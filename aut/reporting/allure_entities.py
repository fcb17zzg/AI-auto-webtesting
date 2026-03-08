from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from aut.replay import ReplayRecord

from .allure_mapper import map_replay_record_to_allure


@dataclass(slots=True)
class AllureAttachment:
    name: str
    source: str
    content_type: str
    content: str

    def reference(self) -> dict[str, str]:
        return {
            "name": self.name,
            "source": self.source,
            "type": self.content_type,
        }


def build_allure_entities(record: ReplayRecord) -> dict[str, Any]:
    mapped = map_replay_record_to_allure(record)

    result_uuid = str(uuid4())
    container_uuid = str(uuid4())

    failed_step = next((item for item in mapped["steps"] if item["status"] == "failed"), None)
    attachments: list[AllureAttachment] = []
    if failed_step is not None:
        attachment_source = f"{uuid4()}-attachment.txt"
        detail_lines = [
            f"run_id={record.run_id}",
            f"case_path={record.case_path}",
            f"failed_step={failed_step.get('name', '')}",
        ]
        status_details = failed_step.get("statusDetails", {})
        if status_details.get("message"):
            detail_lines.append(f"message={status_details['message']}")
        attachments.append(
            AllureAttachment(
                name="failure-context",
                source=attachment_source,
                content_type="text/plain",
                content="\n".join(detail_lines),
            )
        )

    result_payload: dict[str, Any] = {
        "uuid": result_uuid,
        "name": mapped["name"],
        "fullName": mapped["fullName"],
        "historyId": mapped["historyId"],
        "status": mapped["status"],
        "stage": "finished",
        "labels": mapped.get("labels", []),
        "parameters": mapped.get("parameters", []),
        "steps": mapped.get("steps", []),
        "attachments": [item.reference() for item in attachments],
    }

    if "failureContext" in mapped:
        result_payload["statusDetails"] = {
            "message": "case failed, see failure-context attachment",
        }

    container_payload = {
        "uuid": container_uuid,
        "name": mapped["name"],
        "children": [result_uuid],
        "befores": [],
        "afters": [],
    }

    return {
        "result": result_payload,
        "container": container_payload,
        "attachments": attachments,
    }


def write_allure_entities(record: ReplayRecord, output_dir: str | Path) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    entities = build_allure_entities(record)
    result_payload = entities["result"]
    container_payload = entities["container"]
    attachments: list[AllureAttachment] = entities["attachments"]

    result_file = output_path / f"{result_payload['uuid']}-result.json"
    result_file.write_text(json.dumps(result_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    container_file = output_path / f"{container_payload['uuid']}-container.json"
    container_file.write_text(
        json.dumps(container_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    attachment_files: list[Path] = []
    for attachment in attachments:
        attachment_file = output_path / attachment.source
        attachment_file.write_text(attachment.content, encoding="utf-8")
        attachment_files.append(attachment_file)

    return {
        "resultFile": result_file,
        "containerFile": container_file,
        "attachmentFiles": attachment_files,
    }
