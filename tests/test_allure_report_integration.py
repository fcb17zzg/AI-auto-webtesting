from __future__ import annotations

from pathlib import Path

from aut.dsl.models import ResolvedCase
from aut.replay import ReplayStore, build_replay_record
from aut.reporting import map_replay_files_to_allure_batch
from aut.runner.contracts import ExecutionContext, StepResult


def _build_case(case_name: str, case_path: str) -> ResolvedCase:
    return ResolvedCase(
        name=case_name,
        path=Path(case_path),
        description="",
        steps=[],
    )


def test_allure_batch_report_supports_multi_case_and_failure_sample(tmp_path: Path) -> None:
    replay_dir = tmp_path / "replays"
    store = ReplayStore(replay_dir)

    pass_case = _build_case("case_pass", "cases/pass.yaml")
    pass_context = ExecutionContext(case_name="case_pass", run_id="run-pass")
    pass_record = build_replay_record(
        case=pass_case,
        context=pass_context,
        results=[StepResult(task="step-1", success=True)],
        driver="dry-run",
    )
    pass_file = store.save(pass_record)

    fail_case = _build_case("case_fail", "cases/fail.yaml")
    fail_context = ExecutionContext(case_name="case_fail", run_id="run-fail")
    fail_record = build_replay_record(
        case=fail_case,
        context=fail_context,
        results=[
            StepResult(
                task="step-fail",
                success=False,
                message="assertion failed",
                artifacts={
                    "execution": {
                        "source": "browser-use-plan",
                        "actions": [
                            {
                                "action": "click",
                                "target": "role=button",
                                "value": "提交",
                            }
                        ],
                    },
                    "assertions": [
                        {
                            "type": "playwright",
                            "locator": "get_by_text('boom')",
                            "method": "force_fail()",
                            "passed": False,
                            "reason": "forced assertion failure",
                        }
                    ],
                    "attachments": [
                        {
                            "name": "step-screenshot-fail",
                            "contentType": "image/png",
                            "encoding": "base64",
                            "content": "ZmFrZS1wbmc=",
                            "metadata": {"policy": "on-failure"},
                        }
                    ],
                },
            )
        ],
        driver="dry-run",
    )
    fail_file = store.save(fail_record)

    batch = map_replay_files_to_allure_batch([pass_file, fail_file])

    assert batch["summary"] == {"total": 2, "passed": 1, "failed": 1}
    statuses = sorted(item["status"] for item in batch["results"])
    assert statuses == ["failed", "passed"]
    failed_result = next(item for item in batch["results"] if item["status"] == "failed")
    assert failed_result["failureContext"]["runId"] == "run-fail"
    assert failed_result["steps"][0]["executionTrace"]["source"] == "browser-use-plan"
    assert failed_result["steps"][0]["executionTrace"]["actions"][0]["action"] == "click"
    assert failed_result["steps"][0]["executionTrace"]["attachments"][0]["name"] == "step-screenshot-fail"
