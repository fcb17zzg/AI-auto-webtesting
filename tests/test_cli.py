from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from aut.runner import cli
from aut.replay import ReplayStore
from aut.replay.schema import ReplayRecord
from aut.runner.contracts import StepResult


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


def test_cli_run_writes_allure_result_container_and_attachment_files(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    replay_dir = tmp_path / "replays"
    allure_dir = tmp_path / "allure-results"
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
        "--allure-results-dir",
        str(allure_dir),
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
    allure_files = payload["report"]["allureFiles"]

    assert Path(allure_files["result"]).exists()
    assert Path(allure_files["container"]).exists()
    assert len(allure_files["attachments"]) == 1
    assert Path(allure_files["attachments"][0]).exists()


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


def test_cli_run_pytest_mode_writes_allure_results_batch(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    selected_case = project_root / "cases" / "product" / "create_vpc.yaml"
    replay_dir = tmp_path / "replays"
    allure_dir = tmp_path / "allure-results"

    store = ReplayStore(replay_dir)
    record = ReplayRecord(
        schema_version="1.0",
        run_id="run-002",
        case_name="demo_case_2",
        case_path="cases/product/demo2.yaml",
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
            "--allure-results-dir",
            str(allure_dir),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    batch = payload["report"]["allureResultsBatch"]
    assert batch["total"] == 1
    assert Path(batch["files"][0]["result"]).exists()
    assert Path(batch["files"][0]["container"]).exists()


def test_cli_run_stability_mode_returns_zero_when_gate_passed(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    selected_case = project_root / "cases" / "product" / "create_vpc.yaml"

    monkeypatch.setattr(cli, "discover_case_files", lambda **_: [selected_case])

    run_states = iter([0, 0, 1, 0, 0])

    def fake_run_cases_with_pytest(**_: object) -> subprocess.CompletedProcess[str]:
        code = next(run_states)
        return subprocess.CompletedProcess(["pytest"], code, stdout=f"run-{code}", stderr="")

    monkeypatch.setattr(cli, "run_cases_with_pytest", fake_run_cases_with_pytest)

    exit_code = cli.main(
        [
            "--run-stability",
            "--case-root",
            str(project_root / "cases"),
            "--replay-dir",
            str(tmp_path / "replays"),
            "--stability-runs",
            "5",
            "--stability-min-consecutive-pass",
            "2",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["scheduler"] == "pytest-stability"
    assert payload["summary"]["passCount"] == 4
    assert payload["summary"]["maxConsecutivePass"] == 2
    assert payload["gate"]["passed"] is True


def test_cli_run_stability_mode_returns_non_zero_when_gate_failed(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    selected_case = project_root / "cases" / "product" / "create_vpc.yaml"

    monkeypatch.setattr(cli, "discover_case_files", lambda **_: [selected_case])

    run_states = iter([0, 1, 0])

    def fake_run_cases_with_pytest(**_: object) -> subprocess.CompletedProcess[str]:
        code = next(run_states)
        return subprocess.CompletedProcess(["pytest"], code, stdout="", stderr="")

    monkeypatch.setattr(cli, "run_cases_with_pytest", fake_run_cases_with_pytest)

    exit_code = cli.main(
        [
            "--run-stability",
            "--case-root",
            str(project_root / "cases"),
            "--replay-dir",
            str(tmp_path / "replays"),
            "--stability-runs",
            "3",
            "--stability-min-consecutive-pass",
            "2",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["summary"]["maxConsecutivePass"] == 1
    assert payload["gate"]["passed"] is False


def test_cli_run_stability_rejects_invalid_threshold() -> None:
    with pytest.raises(SystemExit):
        cli.main(
            [
                "--run-stability",
                "--stability-runs",
                "3",
                "--stability-min-consecutive-pass",
                "4",
            ]
        )


def test_cli_run_with_playwright_driver_uses_playwright_assertion_executor(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    captured_executor_types: list[type] = []

    class _FakeEngine:
        def __init__(self, driver, assertion_executor=None):
            self.driver = driver
            self.assertion_executor = assertion_executor
            captured_executor_types.append(type(assertion_executor))

        def run_case(self, case, context):
            _ = case, context
            return [StepResult(task="demo", success=False, message="bridge")]

    class _FakeExecutor:
        pass

    monkeypatch.setattr(cli, "ExecutionEngine", _FakeEngine)
    monkeypatch.setattr(cli, "PlaywrightAssertionExecutor", _FakeExecutor)

    exit_code = cli.main(
        [
            "--case",
            "product/create_vpc.yaml",
            "--case-root",
            str(project_root / "cases"),
            "--replay-dir",
            str(tmp_path / "replays"),
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
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["execution"]["driver"] == "playwright"
    assert captured_executor_types == [_FakeExecutor]


def test_cli_run_injects_step_capture_switches_into_context(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    captured_variables: dict[str, object] = {}

    class _FakeEngine:
        def __init__(self, driver, assertion_executor=None):
            _ = driver, assertion_executor

        def run_case(self, case, context):
            _ = case
            captured_variables.update(context.variables)
            return [StepResult(task="demo", success=True, message="ok")]

    monkeypatch.setattr(cli, "ExecutionEngine", _FakeEngine)

    exit_code = cli.main(
        [
            "--case",
            "product/create_vpc.yaml",
            "--case-root",
            str(project_root / "cases"),
            "--replay-dir",
            str(tmp_path / "replays"),
            "--run",
            "--capture-step-screenshot",
            "on-failure",
            "--capture-step-log",
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
    )

    _ = capsys.readouterr()
    assert exit_code == 0
    assert captured_variables["aut.capture.stepScreenshot"] == "on-failure"
    assert captured_variables["aut.capture.stepLog"] is True


def test_cli_run_injects_browser_use_adapter_when_enabled(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    captured_variables: dict[str, object] = {}

    class _FakeAdapter:
        pass

    class _FakeEngine:
        def __init__(self, driver, assertion_executor=None):
            _ = driver, assertion_executor

        def run_case(self, case, context):
            _ = case
            captured_variables.update(context.variables)
            return [StepResult(task="demo", success=True, message="ok")]

    monkeypatch.setattr(cli, "ExecutionEngine", _FakeEngine)
    monkeypatch.setattr(
        cli,
        "create_browser_use_adapter",
        lambda enabled: (
            _FakeAdapter() if enabled else None,
            {
                "enabled": bool(enabled),
                "available": bool(enabled),
                "mode": "passthrough" if enabled else "disabled",
                "fallback": "none" if enabled else "task-mapping",
            },
        ),
    )

    exit_code = cli.main(
        [
            "--case",
            "product/create_vpc.yaml",
            "--case-root",
            str(project_root / "cases"),
            "--replay-dir",
            str(tmp_path / "replays"),
            "--run",
            "--driver",
            "playwright",
            "--enable-browser-use",
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
    )

    _ = capsys.readouterr()
    assert exit_code == 0
    assert "browser_use.adapter" in captured_variables
    assert captured_variables["browser_use.status"]["mode"] == "passthrough"
    assert captured_variables["browser_use.planRetry"] == 0
    assert captured_variables["browser_use.planFallback"] == "fail-fast"


def test_cli_run_sets_browser_use_degraded_status_when_dependency_missing(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    captured_variables: dict[str, object] = {}

    class _FakeEngine:
        def __init__(self, driver, assertion_executor=None):
            _ = driver, assertion_executor

        def run_case(self, case, context):
            _ = case
            captured_variables.update(context.variables)
            return [StepResult(task="demo", success=True, message="ok")]

    monkeypatch.setattr(cli, "ExecutionEngine", _FakeEngine)
    monkeypatch.setattr(
        cli,
        "create_browser_use_adapter",
        lambda enabled: (
            None,
            {
                "enabled": bool(enabled),
                "available": False,
                "mode": "degraded",
                "reason": "dependency-missing",
                "fallback": "task-mapping",
            },
        ),
    )

    exit_code = cli.main(
        [
            "--case",
            "product/create_vpc.yaml",
            "--case-root",
            str(project_root / "cases"),
            "--replay-dir",
            str(tmp_path / "replays"),
            "--run",
            "--driver",
            "playwright",
            "--enable-browser-use",
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
    )

    _ = capsys.readouterr()
    assert exit_code == 0
    assert "browser_use.adapter" not in captured_variables
    assert captured_variables["browser_use.status"]["mode"] == "degraded"
    assert captured_variables["browser_use.status"]["fallback"] == "task-mapping"


def test_cli_rejects_enable_browser_use_without_playwright_driver() -> None:
    with pytest.raises(SystemExit):
        cli.main(
            [
                "--case",
                "product/create_vpc.yaml",
                "--run",
                "--driver",
                "dry-run",
                "--enable-browser-use",
            ]
        )


def test_cli_rejects_browser_use_plan_strategy_without_enable_browser_use() -> None:
    with pytest.raises(SystemExit):
        cli.main(
            [
                "--case",
                "product/create_vpc.yaml",
                "--run",
                "--driver",
                "playwright",
                "--browser-use-plan-retry",
                "1",
            ]
        )


def test_cli_run_injects_browser_use_plan_strategy_when_configured(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    project_root = Path(__file__).resolve().parents[1]
    captured_variables: dict[str, object] = {}

    class _FakeAdapter:
        pass

    class _FakeEngine:
        def __init__(self, driver, assertion_executor=None):
            _ = driver, assertion_executor

        def run_case(self, case, context):
            _ = case
            captured_variables.update(context.variables)
            return [StepResult(task="demo", success=True, message="ok")]

    monkeypatch.setattr(cli, "ExecutionEngine", _FakeEngine)
    monkeypatch.setattr(
        cli,
        "create_browser_use_adapter",
        lambda enabled: (
            _FakeAdapter() if enabled else None,
            {
                "enabled": bool(enabled),
                "available": bool(enabled),
                "mode": "passthrough" if enabled else "disabled",
                "fallback": "none" if enabled else "task-mapping",
            },
        ),
    )

    exit_code = cli.main(
        [
            "--case",
            "product/create_vpc.yaml",
            "--case-root",
            str(project_root / "cases"),
            "--replay-dir",
            str(tmp_path / "replays"),
            "--run",
            "--driver",
            "playwright",
            "--enable-browser-use",
            "--browser-use-plan-retry",
            "2",
            "--browser-use-plan-fallback",
            "task-mapping",
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
    )

    _ = capsys.readouterr()
    assert exit_code == 0
    assert captured_variables["browser_use.planRetry"] == 2
    assert captured_variables["browser_use.planFallback"] == "task-mapping"


def test_cli_playwright_e2e_sample_writes_png_attachment_and_allure_outputs(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    class _FakeLocator:
        def __init__(self):
            self.filled_value = None
            self.clicked = False

        def fill(self, value):
            self.filled_value = value

        def click(self):
            self.clicked = True

    class _FakePage:
        def __init__(self):
            self.last_url = ""
            self.role_locator = _FakeLocator()
            self.label_locator = _FakeLocator()

        def goto(self, url):
            self.last_url = url

        def get_by_role(self, role, name, **kwargs):
            _ = role, name, kwargs
            return self.role_locator

        def get_by_label(self, label, exact=True):
            _ = label, exact
            return self.label_locator

        def get_by_text(self, text, **kwargs):
            _ = kwargs
            return {"text": text}

        def screenshot(self, full_page=True):
            _ = full_page
            return b"fake-png"

    class _FakeExpectation:
        def __init__(self, locator):
            self.locator = locator

        def to_be_visible(self):
            raise RuntimeError(f"expected visible but got: {self.locator}")

    fake_page = _FakePage()

    monkeypatch.setattr(
        cli.PlaywrightBridgeDriver,
        "_is_playwright_available",
        lambda self: True,
    )
    monkeypatch.setattr(
        cli.PlaywrightBridgeDriver,
        "_create_runtime_page",
        lambda self, context: fake_page,
    )
    monkeypatch.setattr(
        cli.PlaywrightAssertionExecutor,
        "_is_playwright_available",
        lambda self: True,
    )
    monkeypatch.setattr(
        cli.PlaywrightAssertionExecutor,
        "_resolve_expect",
        lambda self, locator: _FakeExpectation(locator),
    )

    project_root = Path(__file__).resolve().parents[1]
    replay_dir = tmp_path / "replays"
    allure_dir = tmp_path / "allure-results"

    exit_code = cli.main(
        [
            "--case",
            "common/playwright_e2e_demo.yaml",
            "--case-root",
            str(project_root / "cases"),
            "--replay-dir",
            str(replay_dir),
            "--allure-results-dir",
            str(allure_dir),
            "--run",
            "--driver",
            "playwright",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["execution"]["driver"] == "playwright"
    assert payload["execution"]["failed"] is True
    assert payload["execution"]["step_count"] == 3
    assert len(payload["report"]["allureFiles"]["attachments"]) >= 2
    assert any(
        str(item).endswith(".png") for item in payload["report"]["allureFiles"]["attachments"]
    )

    replay_file = Path(payload["execution"]["replay_file"])
    replay_payload = json.loads(replay_file.read_text(encoding="utf-8"))
    failed_step = replay_payload["steps"][-1]
    attachment_items = failed_step["artifacts"]["attachments"]
    assert attachment_items[0]["name"] == "assertion-failure-screenshot"
    assert attachment_items[0]["contentType"] == "image/png"


def test_cli_playwright_e2e_sample_supports_variable_overrides(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    class _FakeLocator:
        def __init__(self):
            self.filled_value = None
            self.clicked = False

        def fill(self, value):
            self.filled_value = value

        def click(self):
            self.clicked = True

    class _FakePage:
        def __init__(self):
            self.last_url = ""
            self.last_role = ""
            self.last_role_name = ""
            self.role_locator = _FakeLocator()
            self.label_locator = _FakeLocator()

        def goto(self, url):
            self.last_url = url

        def get_by_role(self, role, name, **kwargs):
            _ = kwargs
            self.last_role = role
            self.last_role_name = name
            return self.role_locator

        def get_by_label(self, label, exact=True):
            _ = label, exact
            return self.label_locator

        def get_by_text(self, text, **kwargs):
            _ = kwargs
            return {"text": text}

        def screenshot(self, full_page=True):
            _ = full_page
            return b"fake-png"

    class _FakeExpectation:
        def __init__(self, locator):
            self.locator = locator

        def to_be_visible(self):
            raise RuntimeError(f"expected visible but got: {self.locator}")

    fake_page = _FakePage()

    monkeypatch.setattr(
        cli.PlaywrightBridgeDriver,
        "_is_playwright_available",
        lambda self: True,
    )
    monkeypatch.setattr(
        cli.PlaywrightBridgeDriver,
        "_create_runtime_page",
        lambda self, context: fake_page,
    )
    monkeypatch.setattr(
        cli.PlaywrightAssertionExecutor,
        "_is_playwright_available",
        lambda self: True,
    )
    monkeypatch.setattr(
        cli.PlaywrightAssertionExecutor,
        "_resolve_expect",
        lambda self, locator: _FakeExpectation(locator),
    )

    project_root = Path(__file__).resolve().parents[1]
    replay_dir = tmp_path / "replays"

    exit_code = cli.main(
        [
            "--case",
            "common/playwright_e2e_demo.yaml",
            "--case-root",
            str(project_root / "cases"),
            "--replay-dir",
            str(replay_dir),
            "--run",
            "--driver",
            "playwright",
            "--var",
            "LOGIN_URL=http://example.com/signin",
            "--var",
            "LOGIN_USERNAME=alice",
            "--var",
            "LOGIN_BUTTON_TEXT=立即登录",
            "--var",
            "LOGIN_SUCCESS_TEXT=欢迎回来",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["execution"]["driver"] == "playwright"
    assert payload["execution"]["step_count"] == 3
    assert payload["execution"]["failed"] is True
    assert fake_page.last_url == "http://example.com/signin"
    assert fake_page.label_locator.filled_value == "alice"
    assert fake_page.last_role == "button"
    assert fake_page.last_role_name == "立即登录"
