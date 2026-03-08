from __future__ import annotations

from aut.runner.browser_use_adapter import (
    BrowserUsePlan,
    BrowserUsePassthroughAdapter,
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


def test_passthrough_adapter_maps_action_to_browser_use_plan() -> None:
    adapter = BrowserUsePassthroughAdapter()
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
    assert plan.metadata["source"] == "browser-use-passthrough"
    assert plan.metadata["task"] == "点击“登录”按钮"
    assert plan.metadata["options"]["exact"] is True


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
