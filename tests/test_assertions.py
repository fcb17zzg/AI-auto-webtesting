from __future__ import annotations

from aut.runner.assertions import PLAYWRIGHT_PAGE_KEY, PlaywrightAssertionExecutor
from aut.runner.contracts import ExecutionContext


class _FakeExpectation:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    def to_be_visible(self, *args, **kwargs):
        _ = args, kwargs
        if self.should_fail:
            raise AssertionError("not visible")


class _FakeLocator:
    pass


class _FakePage:
    def get_by_text(self, text: str, exact: bool = False):
        _ = text, exact
        return _FakeLocator()

    def screenshot(self, full_page: bool = True):
        _ = full_page
        return b"fake-png-bytes"


def test_playwright_assertion_executor_keeps_fallback_mode_without_runtime_page() -> None:
    executor = PlaywrightAssertionExecutor()
    context = ExecutionContext(case_name="demo", run_id="run-001")

    results = executor.evaluate(
        [
            {
                "type": "playwright",
                "locator": 'get_by_text("ok")',
                "method": "to_be_visible()",
            }
        ],
        context,
    )

    assert len(results) == 1
    assert results[0].passed is True


def test_playwright_assertion_executor_runs_real_evaluation_when_runtime_ready(monkeypatch) -> None:
    executor = PlaywrightAssertionExecutor()
    context = ExecutionContext(
        case_name="demo",
        run_id="run-002",
        variables={PLAYWRIGHT_PAGE_KEY: _FakePage()},
    )

    monkeypatch.setattr(executor, "_is_playwright_available", lambda: True)
    monkeypatch.setattr(executor, "_resolve_expect", lambda locator: _FakeExpectation())

    results = executor.evaluate(
        [
            {
                "type": "playwright",
                "locator": 'get_by_text("ok", exact=True)',
                "method": "to_be_visible()",
            }
        ],
        context,
    )

    assert len(results) == 1
    assert results[0].passed is True


def test_playwright_assertion_executor_returns_failed_for_invalid_locator_expression() -> None:
    executor = PlaywrightAssertionExecutor()
    executor._is_playwright_available = lambda: True  # type: ignore[method-assign]
    context = ExecutionContext(
        case_name="demo",
        run_id="run-003",
        variables={PLAYWRIGHT_PAGE_KEY: _FakePage()},
    )

    results = executor.evaluate(
        [
            {
                "type": "playwright",
                "locator": "page.get_by_text('ok')",
                "method": "to_be_visible()",
            }
        ],
        context,
    )

    assert len(results) == 1
    assert results[0].passed is False
    assert "invalid playwright locator expression" in results[0].reason


def test_playwright_assertion_executor_returns_failed_when_expectation_throws(monkeypatch) -> None:
    executor = PlaywrightAssertionExecutor()
    context = ExecutionContext(
        case_name="demo",
        run_id="run-004",
        variables={PLAYWRIGHT_PAGE_KEY: _FakePage()},
    )

    monkeypatch.setattr(executor, "_is_playwright_available", lambda: True)
    monkeypatch.setattr(
        executor,
        "_resolve_expect",
        lambda locator: _FakeExpectation(should_fail=True),
    )

    results = executor.evaluate(
        [
            {
                "type": "playwright",
                "locator": 'get_by_text("boom")',
                "method": "to_be_visible()",
            }
        ],
        context,
    )

    assert len(results) == 1
    assert results[0].passed is False
    assert "playwright assertion failed" in results[0].reason
    attachments = results[0].artifacts["attachments"]
    assert len(attachments) == 1
    assert attachments[0]["name"] == "assertion-failure-screenshot"
    assert attachments[0]["contentType"] == "image/png"
    assert attachments[0]["encoding"] == "base64"