from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from aut.dsl import CaseParser
from aut.reporting import (
    map_replay_files_to_allure_batch,
    map_replay_record_to_allure,
    write_replay_files_to_allure_results,
    write_allure_entities,
)
from aut.replay import ReplayStore, build_replay_record
from aut.runner import (
    BROWSER_USE_ADAPTER_KEY,
    BROWSER_USE_PLAN_FALLBACK_KEY,
    BROWSER_USE_PLAN_RETRY_KEY,
    BROWSER_USE_STATUS_KEY,
    DryRunDriver,
    ExecutionContext,
    ExecutionEngine,
    PlaywrightAssertionExecutor,
    PlaywrightBridgeDriver,
    create_browser_use_adapter,
    discover_case_files,
    run_cases_with_pytest,
)


def _non_negative_int(raw_value: str) -> int:
    value = int(raw_value)
    if value < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return value


def _positive_int(raw_value: str) -> int:
    value = int(raw_value)
    if value <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return value


def _collect_new_replay_files(replay_dir: Path, existing: set[Path]) -> list[Path]:
    if not replay_dir.exists():
        return []
    current = {path.resolve() for path in replay_dir.glob("*.json") if path.is_file()}
    return sorted(current - existing)


def _collect_planner_failure_categories(stdout: str, stderr: str) -> list[str]:
    combined = f"{stdout}\n{stderr}".lower()
    categories: list[str] = []

    if "browser-use plan failed" in combined:
        categories.append("planner-exception")
    if "unsupported browser-use plan action" in combined:
        categories.append("unsupported-action")
    if "browser-use adapter must return browseruseplan" in combined:
        categories.append("adapter-contract")
    if "playwright action execution failed" in combined:
        categories.append("plan-runtime")
    if "browser-use-plan-failed" in combined and not categories:
        categories.append("planner-failed-unknown")

    # A generic fallback for planner-related failures that do not match known patterns.
    if not categories and re.search(r"browser[\-_ ]use", combined) and "failed" in combined:
        categories.append("planner-failed-unknown")

    return categories


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render AUT case execution plan")
    parser.add_argument("--case", help="Relative path under cases/ or absolute path")
    parser.add_argument(
        "--case-root",
        default=str(Path.cwd() / "cases"),
        help="Case root directory, defaults to ./cases",
    )
    parser.add_argument(
        "--var",
        action="append",
        default=[],
        help="Template variable in KEY=VALUE format, repeatable",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute steps by dry-run driver and persist replay record",
    )
    parser.add_argument(
        "--driver",
        choices=["dry-run", "playwright"],
        default="dry-run",
        help="Driver backend for --run mode, defaults to dry-run",
    )
    parser.add_argument(
        "--capture-step-screenshot",
        choices=["never", "on-failure", "always"],
        default="never",
        help="Optional step screenshot capture policy for --run mode",
    )
    parser.add_argument(
        "--capture-step-log",
        action="store_true",
        help="Enable step-level log capture metadata for --run mode",
    )
    parser.add_argument(
        "--enable-browser-use",
        action="store_true",
        help="Enable browser-use adapter planning in --run mode (playwright only)",
    )
    parser.add_argument(
        "--browser-use-planner",
        choices=["model-stub", "real-model"],
        default="model-stub",
        help="Planner backend for browser-use adapter, defaults to model-stub",
    )
    parser.add_argument(
        "--browser-use-model",
        default="stub-rule-v1",
        help="Planner model name for browser-use adapter",
    )
    parser.add_argument(
        "--browser-use-planner-endpoint",
        default="",
        help="HTTP endpoint for real-model planner backend",
    )
    parser.add_argument(
        "--browser-use-planner-api-key",
        default="",
        help="Optional API key for real-model planner endpoint",
    )
    parser.add_argument(
        "--browser-use-plan-retry",
        type=_non_negative_int,
        default=0,
        help="Retry count when browser-use planning fails, defaults to 0",
    )
    parser.add_argument(
        "--browser-use-plan-fallback",
        choices=["fail-fast", "task-mapping"],
        default="fail-fast",
        help="Fallback strategy when browser-use planning still fails after retries",
    )
    parser.add_argument(
        "--replay-dir",
        default=str(Path.cwd() / ".aut" / "replays"),
        help="Replay output directory, defaults to ./.aut/replays",
    )
    parser.add_argument(
        "--allure-results-dir",
        default="",
        help="Optional allure-results output directory for --run and --run-pytest modes",
    )
    parser.add_argument(
        "--run-pytest",
        action="store_true",
        help="Run selected YAML cases through pytest scheduler entry",
    )
    parser.add_argument(
        "--run-stability",
        action="store_true",
        help="Run selected YAML cases repeatedly through pytest and evaluate stability gate",
    )
    parser.add_argument(
        "--stability-runs",
        type=_positive_int,
        default=10,
        help="Total repeated runs for --run-stability, defaults to 10",
    )
    parser.add_argument(
        "--stability-min-consecutive-pass",
        type=_positive_int,
        default=10,
        help="Consecutive pass threshold for --run-stability gate, defaults to 10",
    )
    parser.add_argument(
        "--case-glob",
        default="**/*.yaml",
        help="Glob pattern for selecting cases in case-root, defaults to **/*.yaml",
    )
    parser.add_argument(
        "--case-filter",
        default="",
        help="Case name/path contains filter for batch selection",
    )
    parser.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        help="Extra argument passed to pytest when using --run-pytest",
    )
    return parser


def parse_vars(raw_vars: list[str]) -> dict[str, str]:
    variables: dict[str, str] = {}
    for raw_var in raw_vars:
        if "=" not in raw_var:
            raise ValueError(f"Invalid variable format: {raw_var}")
        key, value = raw_var.split("=", 1)
        variables[key] = value
    return variables


def build_driver(name: str):
    if name == "dry-run":
        return DryRunDriver()
    if name == "playwright":
        return PlaywrightBridgeDriver()
    raise ValueError(f"Unsupported driver: {name}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    selected_modes = [args.run, args.run_pytest, args.run_stability]
    if sum(1 for mode in selected_modes if mode) > 1:
        parser.error("--run, --run-pytest and --run-stability are mutually exclusive")

    if args.enable_browser_use and (not args.run or args.driver != "playwright"):
        parser.error("--enable-browser-use requires --run --driver playwright")

    if (
        (args.browser_use_plan_retry > 0 or args.browser_use_plan_fallback != "fail-fast")
        and not args.enable_browser_use
    ):
        parser.error(
            "--browser-use-plan-retry/--browser-use-plan-fallback require --enable-browser-use"
        )

    if (
        (
            args.browser_use_planner != "model-stub"
            or args.browser_use_model != "stub-rule-v1"
            or args.browser_use_planner_endpoint
            or args.browser_use_planner_api_key
        )
        and not args.enable_browser_use
    ):
        parser.error(
            "--browser-use-planner/--browser-use-model/--browser-use-planner-endpoint/"
            "--browser-use-planner-api-key require --enable-browser-use"
        )

    if args.run_stability and args.stability_min_consecutive_pass > args.stability_runs:
        parser.error("--stability-min-consecutive-pass cannot be greater than --stability-runs")

    if not args.run_pytest and not args.run_stability and not args.case:
        parser.error("--case is required unless --run-pytest is used")

    variables = parse_vars(args.var)
    if args.run:
        variables["aut.capture.stepScreenshot"] = args.capture_step_screenshot
        variables["aut.capture.stepLog"] = args.capture_step_log
        adapter, adapter_status = create_browser_use_adapter(
            args.enable_browser_use,
            planner=args.browser_use_planner,
            model=args.browser_use_model,
            planner_endpoint=args.browser_use_planner_endpoint,
            planner_api_key=args.browser_use_planner_api_key,
        )
        variables[BROWSER_USE_STATUS_KEY] = adapter_status
        variables[BROWSER_USE_PLAN_RETRY_KEY] = args.browser_use_plan_retry
        variables[BROWSER_USE_PLAN_FALLBACK_KEY] = args.browser_use_plan_fallback
        if adapter is not None:
            variables[BROWSER_USE_ADAPTER_KEY] = adapter

    if args.run_pytest:
        replay_dir = Path(args.replay_dir).resolve()
        existing_replays = set()
        if replay_dir.exists():
            existing_replays = {
                path.resolve() for path in replay_dir.glob("*.json") if path.is_file()
            }

        selected_cases = discover_case_files(
            case_root=args.case_root,
            case_glob=args.case_glob,
            case_filter=args.case_filter,
        )
        if not selected_cases:
            raise ValueError("No cases matched current selection")

        completed = run_cases_with_pytest(
            case_root=args.case_root,
            replay_dir=args.replay_dir,
            case_glob=args.case_glob,
            case_filter=args.case_filter,
            pytest_args=args.pytest_arg,
        )
        payload = {
            "scheduler": "pytest",
            "case_root": str(Path(args.case_root).resolve()),
            "selected_cases": [
                str(path.relative_to(Path(args.case_root).resolve())) for path in selected_cases
            ],
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

        new_replay_files = _collect_new_replay_files(replay_dir, existing_replays)
        if new_replay_files:
            payload["report"] = {
                "allureBatch": map_replay_files_to_allure_batch(new_replay_files),
            }
            if args.allure_results_dir:
                payload["report"]["allureResultsBatch"] = write_replay_files_to_allure_results(
                    new_replay_files,
                    args.allure_results_dir,
                )

        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return completed.returncode

    if args.run_stability:
        case_root = Path(args.case_root).resolve()
        selected_cases = discover_case_files(
            case_root=args.case_root,
            case_glob=args.case_glob,
            case_filter=args.case_filter,
        )
        if not selected_cases:
            raise ValueError("No cases matched current selection")

        run_results: list[dict[str, object]] = []
        pass_count = 0
        fail_count = 0
        consecutive_pass = 0
        max_consecutive_pass = 0
        planner_failure_counts: dict[str, int] = {}
        planner_failure_by_case: dict[str, dict[str, object]] = {}
        planner_failure_trend: list[dict[str, object]] = []

        for run_index in range(1, args.stability_runs + 1):
            run_case_results: list[dict[str, object]] = []
            run_failed = False
            run_planner_categories: list[str] = []

            for case_path in selected_cases:
                case_relative = case_path.relative_to(case_root).as_posix()
                completed = run_cases_with_pytest(
                    case_root=args.case_root,
                    replay_dir=args.replay_dir,
                    case_glob=args.case_glob,
                    case_filter=args.case_filter,
                    case_paths=[case_path],
                    pytest_args=args.pytest_arg,
                )
                passed = completed.returncode == 0
                if not passed:
                    run_failed = True

                planner_failure_categories = _collect_planner_failure_categories(
                    completed.stdout,
                    completed.stderr,
                )
                if planner_failure_categories:
                    run_planner_categories.extend(planner_failure_categories)
                    case_stats = planner_failure_by_case.setdefault(
                        case_relative,
                        {
                            "total": 0,
                            "byCategory": {},
                        },
                    )
                    case_stats["total"] = int(case_stats["total"]) + len(planner_failure_categories)
                    category_counts = case_stats["byCategory"]
                    if isinstance(category_counts, dict):
                        for category in planner_failure_categories:
                            planner_failure_counts[category] = (
                                planner_failure_counts.get(category, 0) + 1
                            )
                            category_counts[category] = int(category_counts.get(category, 0)) + 1
                    planner_failure_trend.append(
                        {
                            "index": run_index,
                            "case": case_relative,
                            "exit_code": completed.returncode,
                            "categories": planner_failure_categories,
                        }
                    )

                run_case_results.append(
                    {
                        "case": case_relative,
                        "exit_code": completed.returncode,
                        "passed": passed,
                        "plannerFailureCategories": planner_failure_categories,
                        "stdout": completed.stdout,
                        "stderr": completed.stderr,
                    }
                )

            passed = not run_failed
            if passed:
                pass_count += 1
                consecutive_pass += 1
                max_consecutive_pass = max(max_consecutive_pass, consecutive_pass)
            else:
                fail_count += 1
                consecutive_pass = 0

            run_results.append(
                {
                    "index": run_index,
                    "exit_code": 0 if passed else 1,
                    "passed": passed,
                    "plannerFailureCategories": _ordered_unique(run_planner_categories),
                    "caseResults": run_case_results,
                }
            )

        pass_rate = pass_count / args.stability_runs
        gate_passed = max_consecutive_pass >= args.stability_min_consecutive_pass
        payload = {
            "scheduler": "pytest-stability",
            "case_root": str(Path(args.case_root).resolve()),
            "selected_cases": [
                path.relative_to(case_root).as_posix() for path in selected_cases
            ],
            "runs": args.stability_runs,
            "results": run_results,
            "summary": {
                "passCount": pass_count,
                "failCount": fail_count,
                "passRate": pass_rate,
                "maxConsecutivePass": max_consecutive_pass,
                "plannerFailureStats": {
                    "total": sum(planner_failure_counts.values()),
                    "byCategory": planner_failure_counts,
                    "byCase": planner_failure_by_case,
                },
            },
            "plannerFailureTrend": planner_failure_trend,
            "gate": {
                "type": "min-consecutive-pass",
                "minConsecutivePass": args.stability_min_consecutive_pass,
                "passed": gate_passed,
            },
        }

        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if gate_passed else 1

    case_parser = CaseParser(args.case_root)
    resolved_case = case_parser.parse(args.case, variables)
    payload = {
        "name": resolved_case.name,
        "description": resolved_case.description,
        "metadata": resolved_case.metadata,
        "steps": [
            {
                "task": step.task,
                "source": str(step.source),
                "expected": step.expected,
            }
            for step in resolved_case.steps
        ],
    }

    if args.run:
        run_id = datetime.now(UTC).strftime("run-%Y%m%d%H%M%S")
        context = ExecutionContext(
            case_name=resolved_case.name,
            run_id=run_id,
            variables=variables,
        )
        driver = build_driver(args.driver)
        assertion_executor = PlaywrightAssertionExecutor() if args.driver == "playwright" else None
        engine = ExecutionEngine(driver, assertion_executor=assertion_executor)
        results = engine.run_case(resolved_case, context)
        replay_record = build_replay_record(
            case=resolved_case,
            context=context,
            results=results,
            driver=args.driver,
        )
        replay_file = ReplayStore(args.replay_dir).save(replay_record)
        allure_preview = map_replay_record_to_allure(replay_record)
        payload["execution"] = {
            "run_id": run_id,
            "driver": args.driver,
            "step_count": len(results),
            "success_count": sum(1 for item in results if item.success),
            "failed": any(not item.success for item in results),
            "replay_file": str(replay_file),
        }
        payload["report"] = {
            "allure": allure_preview,
        }
        if args.allure_results_dir:
            outputs = write_allure_entities(replay_record, args.allure_results_dir)
            payload["report"]["allureFiles"] = {
                "result": str(outputs["resultFile"]),
                "container": str(outputs["containerFile"]),
                "attachments": [str(path) for path in outputs["attachmentFiles"]],
            }

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())