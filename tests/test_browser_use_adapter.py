from aut.runner.browser_use_adapter import BrowserUsePlan


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
