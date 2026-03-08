from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined

from .models import ResolvedCase, ResolvedStep


class CaseParser:
    def __init__(self, case_root: str | Path):
        self.case_root = Path(case_root).resolve()
        self.jinja_env = Environment(undefined=StrictUndefined, autoescape=False)

    def parse(self, case_path: str | Path, variables: dict[str, Any] | None = None) -> ResolvedCase:
        variables = variables or {}
        resolved_path = self._resolve_case_path(case_path)
        chain: list[Path] = []
        payload = self._load_case_payload(resolved_path)
        steps = self._expand_case_steps(resolved_path, payload, variables, chain)
        metadata = {key: value for key, value in payload.items() if key not in {"preSteps", "testSteps"}}
        return ResolvedCase(
            name=str(metadata.get("testName", resolved_path.stem)),
            path=resolved_path,
            description=str(metadata.get("testDescription", "")),
            steps=steps,
            metadata=metadata,
        )

    def _expand_case_steps(
        self,
        case_path: Path,
        payload: dict[str, Any],
        variables: dict[str, Any],
        chain: list[Path],
    ) -> list[ResolvedStep]:
        if case_path in chain:
            cycle = " -> ".join(str(item.relative_to(self.case_root)) for item in [*chain, case_path])
            raise ValueError(f"Detected circular preSteps reference: {cycle}")

        chain.append(case_path)
        steps: list[ResolvedStep] = []

        for pre_step in payload.get("preSteps", []):
            pre_step_path = self._resolve_case_path(pre_step)
            pre_payload = self._load_case_payload(pre_step_path)
            steps.extend(self._expand_case_steps(pre_step_path, pre_payload, variables, chain))

        for raw_step in payload.get("testSteps", []):
            rendered_step = self._render_mapping(raw_step, variables)
            task = rendered_step.get("task")
            if not task:
                raise ValueError(f"Missing task in step from {case_path}")
            expected = rendered_step.get("expected", [])
            steps.append(ResolvedStep(task=str(task), expected=list(expected), source=case_path))

        chain.pop()
        return steps

    def _load_case_payload(self, case_path: Path) -> dict[str, Any]:
        with case_path.open("r", encoding="utf-8") as file:
            payload = yaml.safe_load(file) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"Case file must be a mapping: {case_path}")
        return payload

    def _render_mapping(self, value: Any, variables: dict[str, Any]) -> Any:
        if isinstance(value, str):
            template = self.jinja_env.from_string(value)
            return template.render(**variables)
        if isinstance(value, list):
            return [self._render_mapping(item, variables) for item in value]
        if isinstance(value, dict):
            return {key: self._render_mapping(item, variables) for key, item in value.items()}
        return value

    def _resolve_case_path(self, case_path: str | Path) -> Path:
        path = Path(case_path)
        if not path.is_absolute():
            candidates = [
                (Path.cwd() / path).resolve(),
                (self.case_root / path).resolve(),
            ]
            for candidate in candidates:
                if candidate.exists():
                    return candidate
            path = self.case_root / path
        resolved = path.resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Case file not found: {resolved}")
        return resolved