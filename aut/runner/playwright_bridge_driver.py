from __future__ import annotations

from importlib.util import find_spec

from aut.dsl import ResolvedStep

from .contracts import Driver, ExecutionContext, StepResult


class PlaywrightBridgeDriver(Driver):
    """Bridge driver used to validate Playwright integration entry points.

    This class intentionally does not map AUT DSL tasks into concrete browser actions
    yet. It is introduced to validate dependency wiring and runtime selection paths.
    """

    def _is_playwright_available(self) -> bool:
        return find_spec("playwright") is not None

    def execute_step(self, step: ResolvedStep, context: ExecutionContext) -> StepResult:
        _ = context
        if not self._is_playwright_available():
            return StepResult(
                task=step.task,
                success=False,
                message="playwright dependency is not installed",
                artifacts={
                    "driver": "playwright",
                    "integration": "dependency-missing",
                },
            )

        return StepResult(
            task=step.task,
            success=False,
            message="playwright bridge is wired, but task mapping is not implemented yet",
            artifacts={
                "driver": "playwright",
                "integration": "entrypoint-ready",
            },
        )
