from __future__ import annotations

import json
from pathlib import Path

from aut.replay.schema import ReplayRecord, ReplayStepRecord
from aut.reporting import build_allure_entities, write_allure_entities


def _build_failed_record() -> ReplayRecord:
    return ReplayRecord(
        schema_version="1.0",
        run_id="run-entities-001",
        case_name="entity_case",
        case_path="cases/product/entity_case.yaml",
        driver="dry-run",
        created_at="2026-03-08T00:00:00+00:00",
        variables={"USERNAME": "tester"},
        metadata={},
        steps=[
            ReplayStepRecord(index=1, task="step-1", success=True),
            ReplayStepRecord(
                index=2,
                task="step-2",
                success=False,
                message="assertion failed",
                artifacts={
                    "attachments": [
                        {
                            "name": "assertion-failure-screenshot",
                            "contentType": "image/png",
                            "encoding": "base64",
                            "content": "ZmFrZS1wbmctYnl0ZXM=",
                        }
                    ]
                },
            ),
        ],
    )


def test_build_allure_entities_contains_result_container_and_attachment() -> None:
    record = _build_failed_record()

    entities = build_allure_entities(record)

    assert entities["result"]["status"] == "failed"
    assert entities["container"]["children"] == [entities["result"]["uuid"]]
    assert len(entities["attachments"]) == 2
    assert entities["attachments"][0].name == "failure-context"
    assert entities["attachments"][1].name == "assertion-failure-screenshot"


def test_write_allure_entities_persists_expected_files(tmp_path: Path) -> None:
    record = _build_failed_record()

    outputs = write_allure_entities(record, tmp_path)

    result_file = outputs["resultFile"]
    container_file = outputs["containerFile"]
    attachment_files = outputs["attachmentFiles"]

    assert result_file.exists()
    assert container_file.exists()
    assert len(attachment_files) == 2
    assert attachment_files[0].exists()
    assert attachment_files[1].exists()

    result_payload = json.loads(result_file.read_text(encoding="utf-8"))
    container_payload = json.loads(container_file.read_text(encoding="utf-8"))

    assert result_payload["uuid"] in container_payload["children"]
    assert result_payload["attachments"][0]["name"] == "failure-context"
    assert result_payload["attachments"][1]["name"] == "assertion-failure-screenshot"

    screenshot_file = next(path for path in attachment_files if path.suffix == ".png")
    assert screenshot_file.read_bytes() == b"fake-png-bytes"
