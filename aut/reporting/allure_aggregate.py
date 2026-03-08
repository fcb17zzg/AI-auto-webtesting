from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aut.replay.schema import ReplayRecord

from .allure_entities import write_allure_entities
from .allure_mapper import map_replay_record_to_allure


def _load_replay_record(file_path: Path) -> ReplayRecord:
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    return ReplayRecord.from_dict(payload)


def map_replay_files_to_allure_batch(replay_files: list[Path]) -> dict[str, Any]:
    mapped_results = []
    for replay_file in replay_files:
        record = _load_replay_record(replay_file)
        mapped = map_replay_record_to_allure(record)
        mapped["sourceReplayFile"] = str(replay_file)
        mapped_results.append(mapped)

    summary = {
        "total": len(mapped_results),
        "passed": sum(1 for item in mapped_results if item.get("status") == "passed"),
        "failed": sum(1 for item in mapped_results if item.get("status") == "failed"),
    }

    return {
        "summary": summary,
        "results": mapped_results,
    }


def write_replay_files_to_allure_results(
    replay_files: list[Path],
    output_dir: str | Path,
) -> dict[str, Any]:
    outputs: list[dict[str, Any]] = []
    for replay_file in replay_files:
        record = _load_replay_record(replay_file)
        written = write_allure_entities(record, output_dir)
        outputs.append(
            {
                "sourceReplayFile": str(replay_file),
                "result": str(written["resultFile"]),
                "container": str(written["containerFile"]),
                "attachments": [str(path) for path in written["attachmentFiles"]],
            }
        )

    return {
        "outputDir": str(Path(output_dir).resolve()),
        "total": len(outputs),
        "files": outputs,
    }
