from __future__ import annotations

import ast
import base64
from importlib.util import find_spec
from typing import Any

from .contracts import AssertionResult, ExecutionContext

SUPPORTED_ASSERTION_TYPES = {"playwright", "validator"}
PLAYWRIGHT_PAGE_KEY = "playwright.page"


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


class PlaywrightAssertionExecutor:
    """Run Playwright assertions when runtime context is available.

    Fallback mode keeps current MVP chain stable by validating assertion structure
    when Playwright page context is not present yet.
    """

    def __init__(self):
        self._fallback = PlaceholderAssertionExecutor()

    def evaluate(
        self,
        expected: list[dict[str, Any]],
        context: ExecutionContext,
    ) -> list[AssertionResult]:
        results: list[AssertionResult] = []
        for raw_item in expected:
            assertion_type = str(raw_item.get("type", "")).strip()
            if assertion_type != "playwright":
                results.append(self._fallback._evaluate_item(raw_item))
                continue

            results.append(self._evaluate_playwright_item(raw_item, context))
        return results

    def _evaluate_playwright_item(
        self,
        raw_item: dict[str, Any],
        context: ExecutionContext,
    ) -> AssertionResult:
        base = self._fallback._evaluate_item(raw_item)
        if not base.passed:
            return base

        locator = str(raw_item.get("locator", "")).strip()
        method = str(raw_item.get("method", "")).strip()

        page = context.variables.get(PLAYWRIGHT_PAGE_KEY)
        if page is None or not self._is_playwright_available():
            return AssertionResult(
                type="playwright",
                locator=locator,
                method=method,
                passed=True,
                reason="",
            )

        locator_call = self._parse_call_expression(locator)
        if locator_call is None:
            return AssertionResult(
                type="playwright",
                locator=locator,
                method=method,
                passed=False,
                reason="invalid playwright locator expression",
            )

        method_call = self._parse_call_expression(method)
        if method_call is None:
            return AssertionResult(
                type="playwright",
                locator=locator,
                method=method,
                passed=False,
                reason="invalid playwright assertion method expression",
            )

        try:
            resolved_locator = getattr(page, locator_call["name"])(
                *locator_call["args"],
                **locator_call["kwargs"],
            )
            expectation = self._resolve_expect(resolved_locator)
            getattr(expectation, method_call["name"])(
                *method_call["args"],
                **method_call["kwargs"],
            )
            return AssertionResult(
                type="playwright",
                locator=locator,
                method=method,
                passed=True,
                reason="",
            )
        except Exception as exc:
            screenshot_attachment = self._capture_failure_screenshot(page)
            artifacts = {}
            if screenshot_attachment is not None:
                artifacts["attachments"] = [screenshot_attachment]
            return AssertionResult(
                type="playwright",
                locator=locator,
                method=method,
                passed=False,
                reason=f"playwright assertion failed: {exc}",
                artifacts=artifacts,
            )

    def _capture_failure_screenshot(self, page: Any) -> dict[str, Any] | None:
        screenshot = getattr(page, "screenshot", None)
        if screenshot is None:
            return None

        try:
            content = screenshot(full_page=True)
        except Exception:
            return None

        if not isinstance(content, (bytes, bytearray)):
            return None

        return {
            "name": "assertion-failure-screenshot",
            "contentType": "image/png",
            "encoding": "base64",
            "content": base64.b64encode(bytes(content)).decode("ascii"),
        }

    def _resolve_expect(self, locator: Any):
        from playwright.sync_api import expect

        return expect(locator)

    def _is_playwright_available(self) -> bool:
        return find_spec("playwright") is not None

    def _parse_call_expression(self, value: str) -> dict[str, Any] | None:
        try:
            node = ast.parse(value, mode="eval")
        except SyntaxError:
            return None

        call = node.body
        if not isinstance(call, ast.Call):
            return None
        if not isinstance(call.func, ast.Name):
            return None

        args: list[Any] = []
        kwargs: dict[str, Any] = {}

        try:
            for arg in call.args:
                args.append(ast.literal_eval(arg))
            for keyword in call.keywords:
                if keyword.arg is None:
                    return None
                kwargs[keyword.arg] = ast.literal_eval(keyword.value)
        except Exception:
            return None

        return {
            "name": call.func.id,
            "args": args,
            "kwargs": kwargs,
        }
