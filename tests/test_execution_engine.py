from pathlib import Path

from aut.dsl.models import ResolvedCase, ResolvedStep
from aut.runner import DryRunDriver, ExecutionContext, ExecutionEngine
from aut.runner.contracts import Driver, StepResult


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