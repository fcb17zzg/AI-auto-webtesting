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


@dataclass(slots=True)
class AssertionResult:
    type: str
    locator: str
    method: str
    passed: bool
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "locator": self.locator,
            "method": self.method,
            "passed": self.passed,
            "reason": self.reason,
        }


class Driver(Protocol):
    def execute_step(self, step: ResolvedStep, context: ExecutionContext) -> StepResult:
        """Execute one resolved step and return the structured result."""


class AssertionExecutor(Protocol):
    def evaluate(
        self,
        expected: list[dict[str, Any]],
        context: ExecutionContext,
    ) -> list[AssertionResult]:
        """Evaluate expected assertions and return normalized assertion results."""
