from __future__ import annotations

import io
import json
from urllib import error as urllib_error

from aut.runner.browser_use_adapter import (
    BrowserUsePlan,
    BrowserUseModelStubAdapter,
    BrowserUseRealModelAdapter,
    create_browser_use_adapter,
)
from aut.runner.contracts import ExecutionContext


def test_create_browser_use_adapter_returns_disabled_status_when_not_enabled() -> None:
    adapter, status = create_browser_use_adapter(False)

    assert adapter is None
    assert status["enabled"] is False
    assert status["mode"] == "disabled"
    assert status["fallback"] == "task-mapping"


def test_create_browser_use_adapter_returns_degraded_when_dependency_missing(monkeypatch) -> None:
    monkeypatch.setattr("aut.runner.browser_use_adapter.find_spec", lambda _: None)

    adapter, status = create_browser_use_adapter(True)

    assert adapter is None
    assert status["enabled"] is True
    assert status["available"] is False
    assert status["mode"] == "degraded"
    assert status["reason"] == "dependency-missing"
    assert status["fallback"] == "task-mapping"


def test_model_stub_adapter_maps_action_to_browser_use_plan() -> None:
    adapter = BrowserUseModelStubAdapter()
    context = ExecutionContext(case_name="demo", run_id="run-001")

    plan = adapter.plan(
        task="点击“登录”按钮",
        mapped_action={
            "action": "click",
            "target": "role=button",
            "value": "登录",
            "options": {"exact": True},
        },
        context=context,
    )

    assert plan.action == "click"
    assert plan.target == "role=button"
    assert plan.value == "登录"
    assert plan.metadata["source"] == "browser-use-model-stub"
    assert plan.metadata["task"] == "点击“登录”按钮"
    assert plan.metadata["planner"]["name"] == "stub-rule-v1"
    assert plan.metadata["actions"][0]["options"]["exact"] is True


def test_create_browser_use_adapter_returns_model_stub_when_dependency_available(
    monkeypatch,
) -> None:
    monkeypatch.setattr("aut.runner.browser_use_adapter.find_spec", lambda _: object())

    adapter, status = create_browser_use_adapter(True)

    assert isinstance(adapter, BrowserUseModelStubAdapter)
    assert status["enabled"] is True
    assert status["available"] is True
    assert status["mode"] == "model-stub"
    assert status["planner"] == "model-stub"
    assert status["model"] == "stub-rule-v1"


def test_create_browser_use_adapter_returns_degraded_for_real_model_without_endpoint(
    monkeypatch,
) -> None:
    monkeypatch.setattr("aut.runner.browser_use_adapter.find_spec", lambda _: object())

    adapter, status = create_browser_use_adapter(
        True,
        planner="real-model",
        model="gpt-5.3-codex",
        planner_endpoint="",
    )

    assert adapter is None
    assert status["mode"] == "degraded"
    assert status["reason"] == "planner-endpoint-missing"
    assert status["planner"] == "real-model"
    assert status["model"] == "gpt-5.3-codex"


def test_create_browser_use_adapter_returns_real_model_adapter_when_configured(
    monkeypatch,
) -> None:
    monkeypatch.setattr("aut.runner.browser_use_adapter.find_spec", lambda _: object())

    adapter, status = create_browser_use_adapter(
        True,
        planner="real-model",
        model="gpt-5.3-codex",
        planner_endpoint="http://planner.example/plan",
        planner_api_key="secret-token",
    )

    assert isinstance(adapter, BrowserUseRealModelAdapter)
    assert status["mode"] == "real-model"
    assert status["planner"] == "real-model"
    assert status["model"] == "gpt-5.3-codex"
    assert status["endpoint"] == "http://planner.example/plan"


def test_create_browser_use_adapter_passes_real_model_transport_config(
    monkeypatch,
) -> None:
    monkeypatch.setattr("aut.runner.browser_use_adapter.find_spec", lambda _: object())

    adapter, status = create_browser_use_adapter(
        True,
        planner="real-model",
        model="gpt-5.3-codex",
        planner_endpoint="http://planner.example/plan",
        planner_api_key="secret-token",
        planner_timeout_seconds=9.5,
        planner_http_retries=2,
        planner_retry_backoff_ms=350,
    )

    assert isinstance(adapter, BrowserUseRealModelAdapter)
    assert status["timeoutSeconds"] == 9.5
    assert status["httpRetries"] == 2
    assert status["retryBackoffMs"] == 350
    assert adapter._timeout_seconds == 9.5
    assert adapter._max_retries == 2
    assert adapter._retry_backoff_seconds == 0.35


def test_real_model_adapter_plan_maps_http_response(monkeypatch) -> None:
    context = ExecutionContext(case_name="demo", run_id="run-001")
    adapter = BrowserUseRealModelAdapter(
        endpoint="http://planner.example/plan",
        model="gpt-5.3-codex",
        api_key="api-key",
    )

    captured_request: dict[str, object] = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            _ = exc_type, exc, tb
            return None

        def read(self):
            payload = {
                "action": "click",
                "target": "role=button",
                "value": "登录",
                "metadata": {"traceId": "trace-001"},
            }
            return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def _fake_urlopen(request, timeout):
        _ = timeout
        captured_request["url"] = request.full_url
        captured_request["authorization"] = request.headers.get("Authorization")
        body = request.data.decode("utf-8")
        captured_request["body"] = json.loads(body)
        return _FakeResponse()

    monkeypatch.setattr("aut.runner.browser_use_adapter.urllib_request.urlopen", _fake_urlopen)

    plan = adapter.plan(
        task="点击登录",
        mapped_action={"action": "click", "target": "role=button", "value": "登录"},
        context=context,
    )

    assert captured_request["url"] == "http://planner.example/plan"
    assert captured_request["authorization"] == "Bearer api-key"
    assert captured_request["body"]["model"] == "gpt-5.3-codex"
    assert plan.action == "click"
    assert plan.metadata["planner"]["kind"] == "real-model"
    assert plan.metadata["source"] == "browser-use-real-model"


def test_real_model_adapter_retries_on_retryable_http_error(monkeypatch) -> None:
    context = ExecutionContext(case_name="demo", run_id="run-001")
    adapter = BrowserUseRealModelAdapter(
        endpoint="http://planner.example/plan",
        model="gpt-5.3-codex",
        timeout_seconds=3,
        max_retries=2,
        retry_backoff_seconds=0,
    )

    calls = {"count": 0}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            _ = exc_type, exc, tb
            return None

        def read(self):
            return b'{"action":"click","target":"role=button","value":""}'

    def _fake_urlopen(request, timeout):
        _ = request, timeout
        calls["count"] += 1
        if calls["count"] == 1:
            raise urllib_error.HTTPError(
                url="http://planner.example/plan",
                code=503,
                msg="service unavailable",
                hdrs=None,
                fp=io.BytesIO(b"temporary"),
            )
        return _FakeResponse()

    monkeypatch.setattr("aut.runner.browser_use_adapter.urllib_request.urlopen", _fake_urlopen)

    plan = adapter.plan(
        task="点击登录",
        mapped_action={"action": "click", "target": "role=button", "value": "登录"},
        context=context,
    )

    assert calls["count"] == 2
    assert plan.action == "click"


def test_real_model_adapter_does_not_retry_on_non_retryable_http_error(monkeypatch) -> None:
    context = ExecutionContext(case_name="demo", run_id="run-001")
    adapter = BrowserUseRealModelAdapter(
        endpoint="http://planner.example/plan",
        model="gpt-5.3-codex",
        timeout_seconds=3,
        max_retries=3,
        retry_backoff_seconds=0,
    )

    calls = {"count": 0}

    def _fake_urlopen(request, timeout):
        _ = request, timeout
        calls["count"] += 1
        raise urllib_error.HTTPError(
            url="http://planner.example/plan",
            code=400,
            msg="bad request",
            hdrs=None,
            fp=io.BytesIO(b"bad input"),
        )

    monkeypatch.setattr("aut.runner.browser_use_adapter.urllib_request.urlopen", _fake_urlopen)

    try:
        adapter.plan(
            task="点击登录",
            mapped_action={"action": "click", "target": "role=button", "value": "登录"},
            context=context,
        )
        raise AssertionError("expected RuntimeError")
    except RuntimeError as exc:
        assert "status=400" in str(exc)

    assert calls["count"] == 1


def test_browser_use_plan_to_dict_contains_all_fields() -> None:
    plan = BrowserUsePlan(
        action="goto",
        target="http://example.com",
        value="",
        metadata={"source": "task-mapper"},
    )

    payload = plan.to_dict()

    assert payload["action"] == "goto"
    assert payload["target"] == "http://example.com"
    assert payload["value"] == ""
    assert payload["metadata"]["source"] == "task-mapper"
