from __future__ import annotations

from aut.dsl import ResolvedStep

from .contracts import Driver, ExecutionContext, StepResult


class DryRunDriver(Driver):
    """No-op driver for validating orchestration before browser integration."""

    def execute_step(self, step: ResolvedStep, context: ExecutionContext) -> StepResult:
        message = f"dry-run executed: {step.task}"
        return StepResult(
            task=step.task,
            success=True,
            message=message,
            artifacts={
                "run_id": context.run_id,
                "source": str(step.source),
            },
        )
