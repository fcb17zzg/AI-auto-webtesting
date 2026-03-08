from __future__ import annotations

from typing import Any

from .contracts import AssertionResult, ExecutionContext

SUPPORTED_ASSERTION_TYPES = {"playwright", "validator"}


class PlaceholderAssertionExecutor:
    """Minimal assertion evaluator used before real browser assertions are integrated."""

    def evaluate(
        self,
        expected: list[dict[str, Any]],
        context: ExecutionContext,
    ) -> list[AssertionResult]:
        _ = context  # Reserved for future context-aware assertions.
        results: list[AssertionResult] = []
        for raw_item in expected:
            results.append(self._evaluate_item(raw_item))
        return results

    def _evaluate_item(self, raw_item: dict[str, Any]) -> AssertionResult:
        assertion_type = str(raw_item.get("type", "")).strip()
        locator = str(raw_item.get("locator", "")).strip()
        method = str(raw_item.get("method", "")).strip()

        if not assertion_type:
            return AssertionResult(
                type="",
                locator=locator,
                method=method,
                passed=False,
                reason="missing assertion type",
            )
        if assertion_type not in SUPPORTED_ASSERTION_TYPES:
            return AssertionResult(
                type=assertion_type,
                locator=locator,
                method=method,
                passed=False,
                reason=f"unsupported assertion type: {assertion_type}",
            )
        if not locator:
            return AssertionResult(
                type=assertion_type,
                locator="",
                method=method,
                passed=False,
                reason="missing locator",
            )
        if not method:
            return AssertionResult(
                type=assertion_type,
                locator=locator,
                method="",
                passed=False,
                reason="missing assertion method",
            )

        should_fail = bool(raw_item.get("forceFail", False)) or method == "force_fail()"
        if should_fail:
            return AssertionResult(
                type=assertion_type,
                locator=locator,
                method=method,
                passed=False,
                reason="forced assertion failure",
            )

        return AssertionResult(
            type=assertion_type,
            locator=locator,
            method=method,
            passed=True,
            reason="",
        )
