from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ResolvedStep:
    task: str
    source: Path
    expected: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class ResolvedCase:
    name: str
    path: Path
    description: str
    steps: list[ResolvedStep]
    metadata: dict[str, Any] = field(default_factory=dict)