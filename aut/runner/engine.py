from __future__ import annotations

from aut.dsl import ResolvedCase

from .assertions import PlaceholderAssertionExecutor
from .contracts import AssertionExecutor, Driver, ExecutionContext, StepResult


class ExecutionEngine:
    def __init__(
        self,
        driver: Driver,
        assertion_executor: AssertionExecutor | None = None,
    ):
        self.driver = driver
        self.assertion_executor = assertion_executor or PlaceholderAssertionExecutor()

    def run_case(self, case: ResolvedCase, context: ExecutionContext) -> list[StepResult]:
        results: list[StepResult] = []
        for step in case.steps:
            result = self.driver.execute_step(step, context)
            if result.success and step.expected:
                assertions = self.assertion_executor.evaluate(step.expected, context)
                result.artifacts["assertions"] = [item.to_dict() for item in assertions]
                attachment_items = [
                    attachment
                    for item in assertions
                    for attachment in item.artifacts.get("attachments", [])
                ]
                if attachment_items:
                    result.artifacts["attachments"] = attachment_items
                first_failed = next((item for item in assertions if not item.passed), None)
                if first_failed is not None:
                    result.success = False
                    result.message = (
                        f"assertion failed: {first_failed.type} "
                        f"{first_failed.locator} {first_failed.method}"
                    )
            results.append(result)
            if not result.success:
                break
        return results
