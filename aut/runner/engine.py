from __future__ import annotations

from aut.dsl import ResolvedCase

from .contracts import Driver, ExecutionContext, StepResult


class ExecutionEngine:
    def __init__(self, driver: Driver):
        self.driver = driver

    def run_case(self, case: ResolvedCase, context: ExecutionContext) -> list[StepResult]:
        results: list[StepResult] = []
        for step in case.steps:
            result = self.driver.execute_step(step, context)
            results.append(result)
            if not result.success:
                break
        return results
