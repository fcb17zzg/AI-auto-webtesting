from __future__ import annotations

from importlib.util import find_spec

from aut.dsl import ResolvedStep

from .contracts import Driver, ExecutionContext, StepResult
from .playwright_task_mapper import PlaywrightTaskMapper


class PlaywrightBridgeDriver(Driver):
    """Bridge driver used to validate Playwright integration entry points.

    This class intentionally does not map AUT DSL tasks into concrete browser actions
    yet. It is introduced to validate dependency wiring and runtime selection paths.
    """

    def __init__(self):
        self.task_mapper = PlaywrightTaskMapper()

    def _is_playwright_available(self) -> bool:
        return find_spec("playwright") is not None

    def execute_step(self, step: ResolvedStep, context: ExecutionContext) -> StepResult:
        _ = context
        mapped_action = None
        try:
            mapped_action = self.task_mapper.map_task(step.task).to_dict()
        except ValueError:
            mapped_action = None

        if not self._is_playwright_available():
            return StepResult(
                task=step.task,
                success=False,
                message="playwright dependency is not installed",
                artifacts={
                    "driver": "playwright",
                    "integration": "dependency-missing",
                    "mapping": {
                        "supported": mapped_action is not None,
                        "action": mapped_action,
                    },
                },
            )

        if mapped_action is None:
            return StepResult(
                task=step.task,
                success=False,
                message="playwright bridge cannot map current task yet",
                artifacts={
                    "driver": "playwright",
                    "integration": "entrypoint-ready",
                    "mapping": {
                        "supported": False,
                        "action": None,
                    },
                },
            )

        return StepResult(
            task=step.task,
            success=False,
            message="playwright bridge mapped task, but browser execution is not implemented yet",
            artifacts={
                "driver": "playwright",
                "integration": "entrypoint-ready",
                "mapping": {
                    "supported": True,
                    "action": mapped_action,
                },
            },
        )
