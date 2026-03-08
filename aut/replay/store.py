from __future__ import annotations

import json
from pathlib import Path

from .schema import ReplayRecord


class ReplayStore:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir)

    def save(self, record: ReplayRecord) -> Path:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        file_path = self.root_dir / f"{record.run_id}.json"
        file_path.write_text(
            json.dumps(record.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return file_path

    def load(self, replay_file: str | Path) -> ReplayRecord:
        file_path = Path(replay_file)
        raw = json.loads(file_path.read_text(encoding="utf-8"))
        return ReplayRecord.from_dict(raw)
