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