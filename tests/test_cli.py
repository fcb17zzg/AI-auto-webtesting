from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


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
