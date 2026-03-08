from __future__ import annotations

import argparse
import json
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


def _collect_new_replay_files(replay_dir: Path, existing: set[Path]) -> list[Path]:
    if not replay_dir.exists():
        return []
    current = {path.resolve() for path in replay_dir.glob("*.json") if path.is_file()}
    return sorted(current - existing)


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

    if args.run and args.run_pytest:
        parser.error("--run and --run-pytest cannot be used together")

    if args.enable_browser_use and (not args.run or args.driver != "playwright"):
        parser.error("--enable-browser-use requires --run --driver playwright")

    if (
        (args.browser_use_plan_retry > 0 or args.browser_use_plan_fallback != "fail-fast")
        and not args.enable_browser_use
    ):
        parser.error(
            "--browser-use-plan-retry/--browser-use-plan-fallback require --enable-browser-use"
        )

    if not args.run_pytest and not args.case:
        parser.error("--case is required unless --run-pytest is used")

    variables = parse_vars(args.var)
    if args.run:
        variables["aut.capture.stepScreenshot"] = args.capture_step_screenshot
        variables["aut.capture.stepLog"] = args.capture_step_log
        adapter, adapter_status = create_browser_use_adapter(args.enable_browser_use)
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