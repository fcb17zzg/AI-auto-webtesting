from __future__ import annotations

from aut.replay.schema import ReplayRecord, ReplayStepRecord
from aut.reporting import map_replay_record_to_allure


def test_map_replay_record_to_allure_includes_steps_assertions_and_failure_context() -> None:
    record = ReplayRecord(
        schema_version="1.0",
        run_id="run-001",
        case_name="demo_case",
        case_path="cases/product/demo.yaml",
        driver="dry-run",
        created_at="2026-03-08T00:00:00+00:00",
        variables={"USERNAME": "tester"},
        metadata={},
        steps=[
            ReplayStepRecord(
                index=1,
                task="step-1",
                success=True,
                artifacts={
                    "assertions": [
                        {
                            "type": "playwright",
                            "locator": "get_by_text('ok')",
                            "method": "to_be_visible()",
                            "passed": True,
                            "reason": "",
                        }
                    ]
                },
            ),
            ReplayStepRecord(
                index=2,
                task="step-2",
                success=False,
                message="assertion failed",
                artifacts={
                    "assertions": [
                        {
                            "type": "playwright",
                            "locator": "get_by_text('boom')",
                            "method": "force_fail()",
                            "passed": False,
                            "reason": "forced assertion failure",
                        }
                    ]
                },
            ),
        ],
    )

    mapped = map_replay_record_to_allure(record)

    assert mapped["status"] == "failed"
    assert mapped["name"] == "demo_case"
    assert mapped["steps"][0]["status"] == "passed"
    assert mapped["steps"][1]["status"] == "failed"
    assert mapped["steps"][1]["failureContext"]["failedAssertionCount"] == 1
    assert mapped["failureContext"]["runId"] == "run-001"


def test_map_replay_record_to_allure_without_failure() -> None:
    record = ReplayRecord(
        schema_version="1.0",
        run_id="run-002",
        case_name="ok_case",
        case_path="cases/product/ok.yaml",
        driver="dry-run",
        created_at="2026-03-08T00:00:00+00:00",
        variables={},
        metadata={},
        steps=[ReplayStepRecord(index=1, task="step", success=True)],
    )

    mapped = map_replay_record_to_allure(record)

    assert mapped["status"] == "passed"
    assert "failureContext" not in mapped


def test_map_replay_record_to_allure_includes_execution_trace_for_actions_and_attachments() -> None:
    record = ReplayRecord(
        schema_version="1.0",
        run_id="run-003",
        case_name="trace_case",
        case_path="cases/common/trace.yaml",
        driver="playwright",
        created_at="2026-03-08T00:00:00+00:00",
        variables={},
        metadata={},
        steps=[
            ReplayStepRecord(
                index=1,
                task="登录步骤",
                success=True,
                artifacts={
                    "execution": {
                        "source": "browser-use-plan",
                        "actions": [
                            {
                                "action": "fill",
                                "target": "用户名",
                                "value": "tester",
                            },
                            {
                                "action": "click",
                                "target": "role=button",
                                "value": "登录",
                            },
                        ],
                    },
                    "attachments": [
                        {
                            "name": "step-screenshot-1",
                            "contentType": "image/png",
                            "metadata": {"policy": "always"},
                        }
                    ],
                },
            )
        ],
    )

    mapped = map_replay_record_to_allure(record)
    execution_trace = mapped["steps"][0]["executionTrace"]

    assert execution_trace["source"] == "browser-use-plan"
    assert len(execution_trace["actions"]) == 2
    assert execution_trace["actions"][0]["action"] == "fill"
    assert execution_trace["actions"][0]["attachmentRefs"] == ["step-screenshot-1"]
    assert execution_trace["actions"][1]["action"] == "click"
    assert execution_trace["attachments"][0]["name"] == "step-screenshot-1"
    assert execution_trace["attachments"][0]["contentType"] == "image/png"
