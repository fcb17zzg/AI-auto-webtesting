from __future__ import annotations

from typing import Any

from aut.replay import ReplayRecord, ReplayStepRecord


def _normalize_execution_actions(execution_payload: Any) -> list[dict[str, Any]]:
    if not isinstance(execution_payload, dict):
        return []

    raw_actions = execution_payload.get("actions")
    if isinstance(raw_actions, list) and raw_actions:
        return [item for item in raw_actions if isinstance(item, dict)]

    fallback_action = execution_payload.get("action")
    if isinstance(fallback_action, dict):
        return [fallback_action]

    return []


def _build_execution_trace(step: ReplayStepRecord) -> dict[str, Any] | None:
    execution_payload = step.artifacts.get("execution")
    normalized_actions = _normalize_execution_actions(execution_payload)

    raw_attachments = step.artifacts.get("attachments")
    attachment_items: list[dict[str, Any]] = []
    if isinstance(raw_attachments, list):
        for index, item in enumerate(raw_attachments, start=1):
            if not isinstance(item, dict):
                continue
            attachment_items.append(
                {
                    "index": index,
                    "name": str(item.get("name", f"attachment-{index}")),
                    "contentType": str(item.get("contentType", "text/plain")),
                    "metadata": item.get("metadata", {}),
                }
            )

    if not normalized_actions and not attachment_items:
        return None

    attachment_refs = [item["name"] for item in attachment_items]
    mapped_actions: list[dict[str, Any]] = []
    for index, action in enumerate(normalized_actions, start=1):
        mapped_actions.append(
            {
                "index": index,
                "action": str(action.get("action", "")),
                "target": str(action.get("target", "")),
                "value": str(action.get("value", "")),
                "attachmentRefs": attachment_refs,
            }
        )

    trace: dict[str, Any] = {
        "actions": mapped_actions,
        "attachments": attachment_items,
    }
    if isinstance(execution_payload, dict):
        source = execution_payload.get("source")
        if isinstance(source, str) and source:
            trace["source"] = source

    return trace


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

    execution_trace = _build_execution_trace(step)
    if execution_trace is not None:
        mapped["executionTrace"] = execution_trace

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
