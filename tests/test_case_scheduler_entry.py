from __future__ import annotations

import os
from json import loads
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aut.dsl import CaseParser
from aut.replay import ReplayStore, build_replay_record
from aut.runner import DryRunDriver, ExecutionContext, ExecutionEngine, discover_case_files

if os.getenv("AUT_ENABLE_CASE_SCHEDULER") != "1":
    pytestmark = pytest.mark.skip(reason="scheduler entry is enabled only by CLI --run-pytest")


def _resolve_case_root() -> Path:
    raw = os.getenv("AUT_CASE_ROOT")
    if raw:
        return Path(raw).resolve()
    return (Path(__file__).resolve().parents[1] / "cases").resolve()


def _resolve_replay_dir() -> Path:
    raw = os.getenv("AUT_REPLAY_DIR")
    if raw:
        return Path(raw).resolve()
    return (Path(__file__).resolve().parents[1] / ".aut" / "replays").resolve()


def _selected_cases() -> list[Path]:
    explicit_cases = os.getenv("AUT_CASE_PATHS", "").strip()
    if explicit_cases:
        decoded = loads(explicit_cases)
        return [Path(item).resolve() for item in decoded]

    root = _resolve_case_root()
    case_glob = os.getenv("AUT_CASE_GLOB", "**/*.yaml")
    case_filter = os.getenv("AUT_CASE_FILTER", "")
    return discover_case_files(root, case_glob=case_glob, case_filter=case_filter)


@pytest.mark.parametrize("case_path", _selected_cases(), ids=lambda p: p.stem)
def test_case_scheduler_executes_resolved_case(case_path: Path) -> None:
    case_root = _resolve_case_root()
    replay_dir = _resolve_replay_dir()
    parser = CaseParser(case_root)

    variables = {
        "ASCM_URL": "http://example.com",
        "USERNAME": "tester",
        "PASSWORD": "secret",
        "DEFAULT_ORG_ID": "org-1",
        "VPC_NAME_UNIQUE": "vpc-from-pytest",
    }
    resolved_case = parser.parse(case_path, variables)

    run_id = datetime.now(UTC).strftime("pytest-%Y%m%d%H%M%S%f")
    context = ExecutionContext(case_name=resolved_case.name, run_id=run_id, variables=variables)
    engine = ExecutionEngine(DryRunDriver())

    results = engine.run_case(resolved_case, context)

    replay_record = build_replay_record(
        case=resolved_case,
        context=context,
        results=results,
        driver="dry-run",
    )
    replay_file = ReplayStore(replay_dir).save(replay_record)
    assert replay_file.exists()
    assert results
    assert all(item.success for item in results)
