from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from aut.dsl import CaseParser
from aut.replay import ReplayStore, build_replay_record
from aut.runner import DryRunDriver, ExecutionContext, ExecutionEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render AUT case execution plan")
    parser.add_argument("--case", required=True, help="Relative path under cases/ or absolute path")
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
        "--replay-dir",
        default=str(Path.cwd() / ".aut" / "replays"),
        help="Replay output directory, defaults to ./.aut/replays",
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


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    variables = parse_vars(args.var)
    case_parser = CaseParser(args.case_root)
    resolved_case = case_parser.parse(args.case, variables)
    plan = {
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
        engine = ExecutionEngine(DryRunDriver())
        results = engine.run_case(resolved_case, context)
        replay_record = build_replay_record(
            case=resolved_case,
            context=context,
            results=results,
            driver="dry-run",
        )
        replay_file = ReplayStore(args.replay_dir).save(replay_record)
        plan["execution"] = {
            "run_id": run_id,
            "driver": "dry-run",
            "step_count": len(results),
            "success_count": sum(1 for item in results if item.success),
            "failed": any(not item.success for item in results),
            "replay_file": str(replay_file),
        }

    print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()