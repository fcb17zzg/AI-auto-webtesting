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
