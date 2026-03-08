from __future__ import annotations

import os
import subprocess
import sys
from json import dumps
from pathlib import Path


def discover_case_files(
    case_root: str | Path,
    case_glob: str = "**/*.yaml",
    case_filter: str = "",
) -> list[Path]:
    root = Path(case_root).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Case root not found: {root}")

    normalized_filter = case_filter.strip().lower()
    files = sorted(path.resolve() for path in root.glob(case_glob) if path.is_file())
    if not normalized_filter:
        return files

    selected: list[Path] = []
    for path in files:
        rel_path = str(path.relative_to(root)).lower()
        if normalized_filter in rel_path or normalized_filter in path.stem.lower():
            selected.append(path)
    return selected


def run_cases_with_pytest(
    *,
    case_root: str | Path,
    replay_dir: str | Path,
    case_glob: str = "**/*.yaml",
    case_filter: str = "",
    case_paths: list[str | Path] | None = None,
    pytest_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    root = Path(case_root).resolve()
    replay_path = Path(replay_dir).resolve()

    env = os.environ.copy()
    env["AUT_ENABLE_CASE_SCHEDULER"] = "1"
    env["AUT_CASE_ROOT"] = str(root)
    env["AUT_CASE_GLOB"] = case_glob
    env["AUT_CASE_FILTER"] = case_filter
    env["AUT_REPLAY_DIR"] = str(replay_path)
    if case_paths:
        normalized = [str(Path(path).resolve()) for path in case_paths]
        env["AUT_CASE_PATHS"] = dumps(normalized, ensure_ascii=False)

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests/test_case_scheduler_entry.py",
    ]
    if pytest_args:
        command.extend(pytest_args)

    return subprocess.run(command, text=True, capture_output=True, env=env, check=False)
