from __future__ import annotations

from typing import Any

from aut.replay import ReplayRecord, ReplayStepRecord


def _map_step(step: ReplayStepRecord) -> dict[str, Any]:
    assertions = list(step.artifacts.get("assertions", []))
    failed_assertions = [item for item in assertions if not item.get("passed", False)]
    status = "passed" if step.success else "failed"

    mapped: dict[str, Any] = {
        "name": step.task,
        "status": status,
        "stage": "finished",
        "assertions": assertions,
    }

    if step.message:
        mapped["statusDetails"] = {"message": step.message}

    if failed_assertions:
        mapped["failureContext"] = {
            "failedAssertionCount": len(failed_assertions),
            "firstFailedAssertion": failed_assertions[0],
        }

    return mapped


def map_replay_record_to_allure(record: ReplayRecord) -> dict[str, Any]:
    steps = [_map_step(step) for step in record.steps]
    failed_step = next((item for item in steps if item["status"] == "failed"), None)

    payload: dict[str, Any] = {
        "name": record.case_name,
        "fullName": f"{record.case_name}::{record.run_id}",
        "historyId": record.run_id,
        "status": "failed" if failed_step else "passed",
        "labels": [
            {"name": "suite", "value": record.case_name},
            {"name": "driver", "value": record.driver},
        ],
        "parameters": [
            {"name": key, "value": str(value)}
            for key, value in sorted(record.variables.items(), key=lambda item: item[0])
        ],
        "steps": steps,
    }

    if failed_step is not None:
        payload["failureContext"] = {
            "runId": record.run_id,
            "casePath": record.case_path,
            "failedStep": failed_step,
        }

    return payload
