from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from aut.dsl import ResolvedCase
from aut.runner import ExecutionContext, StepResult

SCHEMA_VERSION = "1.0"


@dataclass(slots=True)
class ReplayStepRecord:
    index: int
    task: str
    success: bool
    message: str = ""
    artifacts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "task": self.task,
            "success": self.success,
            "message": self.message,
            "artifacts": self.artifacts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReplayStepRecord:
        return cls(
            index=int(data["index"]),
            task=str(data["task"]),
            success=bool(data["success"]),
            message=str(data.get("message", "")),
            artifacts=dict(data.get("artifacts", {})),
        )


@dataclass(slots=True)
class ReplayRecord:
    schema_version: str
    run_id: str
    case_name: str
    case_path: str
    driver: str
    created_at: str
    variables: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    steps: list[ReplayStepRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "runId": self.run_id,
            "caseName": self.case_name,
            "casePath": self.case_path,
            "driver": self.driver,
            "createdAt": self.created_at,
            "variables": self.variables,
            "metadata": self.metadata,
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReplayRecord:
        return cls(
            schema_version=str(data["schemaVersion"]),
            run_id=str(data["runId"]),
            case_name=str(data["caseName"]),
            case_path=str(data["casePath"]),
            driver=str(data["driver"]),
            created_at=str(data["createdAt"]),
            variables=dict(data.get("variables", {})),
            metadata=dict(data.get("metadata", {})),
            steps=[
                ReplayStepRecord.from_dict(item)
                for item in data.get("steps", [])
            ],
        )


def build_replay_record(
    case: ResolvedCase,
    context: ExecutionContext,
    results: list[StepResult],
    driver: str,
) -> ReplayRecord:
    step_records = [
        ReplayStepRecord(
            index=index,
            task=item.task,
            success=item.success,
            message=item.message,
            artifacts=item.artifacts,
        )
        for index, item in enumerate(results, start=1)
    ]
    return ReplayRecord(
        schema_version=SCHEMA_VERSION,
        run_id=context.run_id,
        case_name=case.name,
        case_path=str(case.path),
        driver=driver,
        created_at=datetime.now(UTC).isoformat(),
        variables=context.variables,
        metadata=case.metadata,
        steps=step_records,
    )
