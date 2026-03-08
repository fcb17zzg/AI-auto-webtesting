from __future__ import annotations

import json
import subprocess
from pathlib import Path

from aut.runner.pytest_scheduler import discover_case_files, run_cases_with_pytest


def test_discover_case_files_supports_filter(tmp_path: Path) -> None:
    case_root = tmp_path / "cases"
    (case_root / "common").mkdir(parents=True, exist_ok=True)
    (case_root / "product").mkdir(parents=True, exist_ok=True)
    (case_root / "common" / "login.yaml").write_text("testName: login", encoding="utf-8")
    (case_root / "product" / "create_vpc.yaml").write_text(
        "testName: create_vpc", encoding="utf-8"
    )

    all_cases = discover_case_files(case_root)
    assert len(all_cases) == 2

    filtered = discover_case_files(case_root, case_filter="vpc")
    assert len(filtered) == 1
    assert filtered[0].name == "create_vpc.yaml"


def test_run_cases_with_pytest_invokes_subprocess(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, text, capture_output, env, check):
        captured["command"] = command
        captured["text"] = text
        captured["capture_output"] = capture_output
        captured["env"] = env
        captured["check"] = check
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr("aut.runner.pytest_scheduler.subprocess.run", fake_run)

    result = run_cases_with_pytest(
        case_root=tmp_path / "cases",
        replay_dir=tmp_path / "replays",
        case_glob="product/*.yaml",
        case_filter="vpc",
        case_paths=[tmp_path / "cases" / "product" / "create_vpc.yaml"],
        pytest_args=["-k", "create_vpc"],
    )

    assert result.returncode == 0
    command = captured["command"]
    assert command[:3] == [command[0], "-m", "pytest"]
    assert "tests/test_case_scheduler_entry.py" in command
    assert "-k" in command

    env = captured["env"]
    assert env["AUT_ENABLE_CASE_SCHEDULER"] == "1"
    assert env["AUT_CASE_GLOB"] == "product/*.yaml"
    assert env["AUT_CASE_FILTER"] == "vpc"
    assert "AUT_CASE_PATHS" in env
    assert json.loads(env["AUT_CASE_PATHS"])[0].endswith("create_vpc.yaml")
