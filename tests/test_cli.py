from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from aut.runner import cli
from aut.replay import ReplayStore
from aut.replay.schema import ReplayRecord


def test_cli_run_outputs_execution_and_replay_file(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    replay_dir = tmp_path / "replays"

    command = [
        sys.executable,
        "-m",
        "aut.runner.cli",
        "--case",
        "product/create_vpc.yaml",
        "--case-root",
        str(project_root / "cases"),
        "--replay-dir",
        str(replay_dir),
        "--run",
        "--var",
        "ASCM_URL=http://example.com",
        "--var",
        "USERNAME=tester",
        "--var",
        "PASSWORD=secret",
        "--var",
        "DEFAULT_ORG_ID=org-1",
        "--var",
        "VPC_NAME_UNIQUE=vpc-001",
    ]

    completed = subprocess.run(
        command,
        cwd=project_root,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["name"] == "create_vpc_unique"
    assert "execution" in payload
    assert "report" in payload
    assert payload["report"]["allure"]["name"] == "create_vpc_unique"
    assert payload["execution"]["driver"] == "dry-run"
    assert payload["execution"]["step_count"] > 0

    replay_file = Path(payload["execution"]["replay_file"])
    assert replay_file.exists()


def test_cli_run_marks_failed_when_assertion_failed(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    replay_dir = tmp_path / "replays"
    case_root = tmp_path / "cases"
    case_root.mkdir(parents=True, exist_ok=True)
    case_path = case_root / "assert_fail.yaml"
    case_path.write_text(
        "\n".join(
            [
                "testName: assertion_fail_demo",
                "testSteps:",
                "  - task: 打开页面",
                "    expected:",
                "      - type: playwright",
                "        locator: get_by_text(\"失败\")",
                "        method: force_fail()",
            ]
        ),
        encoding="utf-8",
    )

    command = [
        sys.executable,
        "-m",
        "aut.runner.cli",
        "--case",
        str(case_path),
        "--case-root",
        str(case_root),
        "--replay-dir",
        str(replay_dir),
        "--run",
    ]

    completed = subprocess.run(
        command,
        cwd=project_root,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["execution"]["failed"] is True

    replay_file = Path(payload["execution"]["replay_file"])
    replay_payload = json.loads(replay_file.read_text(encoding="utf-8"))
    assert replay_payload["steps"][0]["artifacts"]["assertions"][0]["passed"] is False


def test_cli_run_with_playwright_driver_marks_case_failed_when_dependency_missing(
    tmp_path: Path,
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    replay_dir = tmp_path / "replays"

    command = [
        sys.executable,
        "-m",
        "aut.runner.cli",
        "--case",
        "product/create_vpc.yaml",
        "--case-root",
        str(project_root / "cases"),
        "--replay-dir",
        str(replay_dir),
        "--run",
        "--driver",
        "playwright",
        "--var",
        "ASCM_URL=http://example.com",
        "--var",
        "USERNAME=tester",
        "--var",
        "PASSWORD=secret",
        "--var",
        "DEFAULT_ORG_ID=org-1",
        "--var",
        "VPC_NAME_UNIQUE=vpc-001",
    ]

    completed = subprocess.run(
        command,
        cwd=project_root,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["execution"]["driver"] == "playwright"
    assert payload["execution"]["failed"] is True

    replay_file = Path(payload["execution"]["replay_file"])
    replay_payload = json.loads(replay_file.read_text(encoding="utf-8"))
    assert replay_payload["driver"] == "playwright"


def test_cli_requires_case_when_not_run_pytest() -> None:
    with pytest.raises(SystemExit):
        cli.main([])


def test_cli_run_pytest_mode_returns_scheduler_exit_code(monkeypatch, tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    selected_case = project_root / "cases" / "product" / "create_vpc.yaml"

    monkeypatch.setattr(cli, "discover_case_files", lambda **_: [selected_case])

    fake_result = subprocess.CompletedProcess(["pytest"], 0, stdout="2 passed", stderr="")
    monkeypatch.setattr(cli, "run_cases_with_pytest", lambda **_: fake_result)

    exit_code = cli.main(
        [
            "--run-pytest",
            "--case-root",
            str(project_root / "cases"),
            "--replay-dir",
            str(tmp_path / "replays"),
            "--case-filter",
            "vpc",
            "--pytest-arg=-k=create_vpc",
        ]
    )

    assert exit_code == 0


def test_cli_run_pytest_mode_includes_allure_batch_report(monkeypatch, tmp_path: Path, capsys) -> None:
    project_root = Path(__file__).resolve().parents[1]
    selected_case = project_root / "cases" / "product" / "create_vpc.yaml"
    replay_dir = tmp_path / "replays"

    store = ReplayStore(replay_dir)
    record = ReplayRecord(
        schema_version="1.0",
        run_id="run-001",
        case_name="demo_case",
        case_path="cases/product/demo.yaml",
        driver="dry-run",
        created_at="2026-03-08T00:00:00+00:00",
        variables={},
        metadata={},
        steps=[],
    )

    def fake_run_cases_with_pytest(**_: object) -> subprocess.CompletedProcess[str]:
        store.save(record)
        return subprocess.CompletedProcess(["pytest"], 0, stdout="1 passed", stderr="")

    monkeypatch.setattr(cli, "discover_case_files", lambda **_: [selected_case])
    monkeypatch.setattr(cli, "run_cases_with_pytest", fake_run_cases_with_pytest)

    exit_code = cli.main(
        [
            "--run-pytest",
            "--case-root",
            str(project_root / "cases"),
            "--replay-dir",
            str(replay_dir),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["report"]["allureBatch"]["summary"]["total"] == 1
    assert payload["report"]["allureBatch"]["results"][0]["name"] == "demo_case"
