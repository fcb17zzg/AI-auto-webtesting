from pathlib import Path

from aut.dsl.models import ResolvedCase, ResolvedStep
from aut.runner import DryRunDriver, ExecutionContext, ExecutionEngine
from aut.runner.contracts import AssertionResult, AssertionExecutor, Driver, StepResult
from aut.runner.playwright_bridge_driver import PlaywrightBridgeDriver


def test_execution_engine_runs_all_steps_with_dry_run_driver() -> None:
    case = ResolvedCase(
        name="demo",
        path=Path("demo.yaml"),
        description="",
        steps=[
            ResolvedStep(task="step-1", source=Path("demo.yaml")),
            ResolvedStep(task="step-2", source=Path("demo.yaml")),
        ],
    )
    context = ExecutionContext(case_name="demo", run_id="run-001")
    engine = ExecutionEngine(DryRunDriver())

    results = engine.run_case(case, context)

    assert len(results) == 2
    assert all(item.success for item in results)
    assert results[0].artifacts["run_id"] == "run-001"


def test_execution_engine_records_assertion_artifacts_when_passed() -> None:
    case = ResolvedCase(
        name="demo",
        path=Path("demo.yaml"),
        description="",
        steps=[
            ResolvedStep(
                task="step-1",
                source=Path("demo.yaml"),
                expected=[
                    {
                        "type": "playwright",
                        "locator": "get_by_text('ok')",
                        "method": "to_be_visible()",
                    }
                ],
            )
        ],
    )
    context = ExecutionContext(case_name="demo", run_id="run-001")
    engine = ExecutionEngine(DryRunDriver())

    results = engine.run_case(case, context)

    assert len(results) == 1
    assert results[0].success is True
    assert "assertions" in results[0].artifacts
    assert results[0].artifacts["assertions"][0]["passed"] is True


class FailOnSecondStepDriver(Driver):
    def execute_step(self, step: ResolvedStep, context: ExecutionContext) -> StepResult:
        if step.task == "step-2":
            return StepResult(task=step.task, success=False, message="forced failure")
        return StepResult(task=step.task, success=True)


def test_execution_engine_stops_when_step_failed() -> None:
    case = ResolvedCase(
        name="demo",
        path=Path("demo.yaml"),
        description="",
        steps=[
            ResolvedStep(task="step-1", source=Path("demo.yaml")),
            ResolvedStep(task="step-2", source=Path("demo.yaml")),
            ResolvedStep(task="step-3", source=Path("demo.yaml")),
        ],
    )
    context = ExecutionContext(case_name="demo", run_id="run-002")
    engine = ExecutionEngine(FailOnSecondStepDriver())

    results = engine.run_case(case, context)

    assert len(results) == 2
    assert results[-1].success is False
    assert results[-1].message == "forced failure"


def test_execution_engine_stops_when_assertion_failed() -> None:
    case = ResolvedCase(
        name="demo",
        path=Path("demo.yaml"),
        description="",
        steps=[
            ResolvedStep(task="step-1", source=Path("demo.yaml")),
            ResolvedStep(
                task="step-2",
                source=Path("demo.yaml"),
                expected=[
                    {
                        "type": "playwright",
                        "locator": "get_by_text('boom')",
                        "method": "force_fail()",
                    }
                ],
            ),
            ResolvedStep(task="step-3", source=Path("demo.yaml")),
        ],
    )
    context = ExecutionContext(case_name="demo", run_id="run-003")
    engine = ExecutionEngine(DryRunDriver())

    results = engine.run_case(case, context)

    assert len(results) == 2
    assert results[-1].success is False
    assert "assertion failed" in results[-1].message
    assert results[-1].artifacts["assertions"][0]["reason"] == "forced assertion failure"


class _AttachmentAssertionExecutor(AssertionExecutor):
    def evaluate(self, expected, context):
        _ = expected, context
        return [
            AssertionResult(
                type="playwright",
                locator='get_by_text("boom")',
                method="to_be_visible()",
                passed=False,
                reason="playwright assertion failed",
                artifacts={
                    "attachments": [
                        {
                            "name": "assertion-failure-screenshot",
                            "contentType": "image/png",
                            "encoding": "base64",
                            "content": "ZmFrZQ==",
                        }
                    ]
                },
            )
        ]


def test_execution_engine_collects_assertion_attachments_to_step_artifacts() -> None:
    case = ResolvedCase(
        name="demo",
        path=Path("demo.yaml"),
        description="",
        steps=[
            ResolvedStep(
                task="step-1",
                source=Path("demo.yaml"),
                expected=[
                    {
                        "type": "playwright",
                        "locator": 'get_by_text("boom")',
                        "method": "to_be_visible()",
                    }
                ],
            )
        ],
    )
    context = ExecutionContext(case_name="demo", run_id="run-004")
    engine = ExecutionEngine(DryRunDriver(), assertion_executor=_AttachmentAssertionExecutor())

    results = engine.run_case(case, context)

    assert len(results) == 1
    assert results[0].success is False
    assert "attachments" in results[0].artifacts
    assert results[0].artifacts["attachments"][0]["name"] == "assertion-failure-screenshot"


def test_playwright_bridge_driver_marks_dependency_missing_when_unavailable(
    monkeypatch,
) -> None:
    step = ResolvedStep(task='打开 "http://example.com"', source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-004")
    driver = PlaywrightBridgeDriver()
    monkeypatch.setattr(driver, "_is_playwright_available", lambda: False)

    result = driver.execute_step(step, context)

    assert result.success is False
    assert "not installed" in result.message
    assert result.artifacts["integration"] == "dependency-missing"
    assert result.artifacts["mapping"]["supported"] is True
    assert result.artifacts["mapping"]["action"]["action"] == "goto"


def test_playwright_bridge_driver_reports_entrypoint_ready_when_dependency_present(
    monkeypatch,
) -> None:
    step = ResolvedStep(task="点击“登录”按钮", source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-005")
    driver = PlaywrightBridgeDriver()
    monkeypatch.setattr(driver, "_is_playwright_available", lambda: True)

    result = driver.execute_step(step, context)

    assert result.success is False
    assert "mapped task" in result.message
    assert result.artifacts["integration"] == "entrypoint-ready"
    assert result.artifacts["mapping"]["supported"] is True
    assert result.artifacts["mapping"]["action"]["action"] == "click"


def test_playwright_bridge_driver_returns_mapping_unsupported_for_unknown_task(
    monkeypatch,
) -> None:
    step = ResolvedStep(task="等待 3 秒", source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-006")
    driver = PlaywrightBridgeDriver()
    monkeypatch.setattr(driver, "_is_playwright_available", lambda: True)

    result = driver.execute_step(step, context)

    assert result.success is False
    assert "cannot map" in result.message
    assert result.artifacts["integration"] == "entrypoint-ready"
    assert result.artifacts["mapping"]["supported"] is False
    assert result.artifacts["mapping"]["action"] is None