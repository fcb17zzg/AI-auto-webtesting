from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from aut.dsl import ResolvedStep


@dataclass(slots=True)
class ExecutionContext:
    case_name: str
    run_id: str
    variables: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StepResult:
    task: str
    success: bool
    message: str = ""
    artifacts: dict[str, Any] = field(default_factory=dict)


class Driver(Protocol):
    def execute_step(self, step: ResolvedStep, context: ExecutionContext) -> StepResult:
        """Execute one resolved step and return the structured result."""
