from __future__ import annotations

import argparse
import json
from pathlib import Path

from aut.dsl import CaseParser


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
    print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()