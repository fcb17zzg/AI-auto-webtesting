from __future__ import annotations

import json
from dataclasses import asdict
from dataclasses import dataclass, field
from importlib.util import find_spec
from urllib import error as urllib_error
from urllib import request as urllib_request
from typing import Any, Protocol

from .contracts import ExecutionContext

BROWSER_USE_ADAPTER_KEY = "browser_use.adapter"
BROWSER_USE_STATUS_KEY = "browser_use.status"
BROWSER_USE_PLAN_RETRY_KEY = "browser_use.planRetry"
BROWSER_USE_PLAN_FALLBACK_KEY = "browser_use.planFallback"


@dataclass(slots=True)
class BrowserUsePlan:
    """Normalized plan payload returned by browser-use adapter implementations."""

    action: str
    target: str = ""
    value: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "target": self.target,
            "value": self.value,
            "metadata": self.metadata,
        }


class BrowserUseAdapter(Protocol):
    """Optional planning interface for future browser-use integration."""

    def plan(
        self,
        *,
        task: str,
        mapped_action: dict[str, Any],
        context: ExecutionContext,
    ) -> BrowserUsePlan:
        """Build a browser-use plan from DSL task and mapped action."""


@dataclass(slots=True)
class BrowserUsePlannerRequest:
    """Request payload contract for planner implementations."""

    task: str
    mapped_action: dict[str, Any]
    case_name: str
    run_id: str


@dataclass(slots=True)
class BrowserUsePlannerResponse:
    """Response payload contract for planner implementations."""

    action: str
    target: str = ""
    value: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BrowserUseModelStubAdapter:
    """Model-driven planner stub that emits normalized browser-use plan payloads."""

    def _normalize_action_payload(self, mapped_action: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "action": str(mapped_action.get("action", "")).strip().lower(),
            "target": str(mapped_action.get("target", "")),
            "value": str(mapped_action.get("value", "")),
        }
        options = mapped_action.get("options")
        if isinstance(options, dict) and options:
            payload["options"] = options
        return payload

    def plan(
        self,
        *,
        task: str,
        mapped_action: dict[str, Any],
        context: ExecutionContext,
    ) -> BrowserUsePlan:
        _ = context
        normalized = self._normalize_action_payload(mapped_action)
        metadata: dict[str, Any] = {
            "task": task,
            "source": "browser-use-model-stub",
            "planner": {
                "provider": "local",
                "name": "stub-rule-v1",
                "kind": "model-stub",
            },
            "actions": [normalized],
        }
        return BrowserUsePlan(
            action=str(normalized.get("action", "")),
            target=str(normalized.get("target", "")),
            value=str(normalized.get("value", "")),
            metadata=metadata,
        )


class BrowserUsePassthroughAdapter(BrowserUseModelStubAdapter):
    """Backward-compatible alias for the historical adapter class name."""


class BrowserUseRealModelAdapter:
    """HTTP-based planner adapter for real model integration."""

    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        api_key: str = "",
        timeout_seconds: float = 15.0,
    ) -> None:
        self._endpoint = endpoint
        self._model = model
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    def _normalize_response(self, payload: dict[str, Any]) -> BrowserUsePlannerResponse:
        return BrowserUsePlannerResponse(
            action=str(payload.get("action", "")).strip().lower(),
            target=str(payload.get("target", "")),
            value=str(payload.get("value", "")),
            metadata=payload.get("metadata", {}) if isinstance(payload.get("metadata"), dict) else {},
        )

    def _request_plan(self, request_payload: BrowserUsePlannerRequest) -> BrowserUsePlannerResponse:
        body = {
            "model": self._model,
            "input": asdict(request_payload),
        }
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        http_request = urllib_request.Request(
            url=self._endpoint,
            data=encoded,
            headers=headers,
            method="POST",
        )

        try:
            with urllib_request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                raw_text = response.read().decode("utf-8")
        except urllib_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"planner http error: status={exc.code}, detail={detail}") from exc
        except urllib_error.URLError as exc:
            raise RuntimeError(f"planner network error: {exc.reason}") from exc

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("planner response is not valid JSON") from exc

        if not isinstance(parsed, dict):
            raise RuntimeError("planner response must be JSON object")

        return self._normalize_response(parsed)

    def plan(
        self,
        *,
        task: str,
        mapped_action: dict[str, Any],
        context: ExecutionContext,
    ) -> BrowserUsePlan:
        request_payload = BrowserUsePlannerRequest(
            task=task,
            mapped_action=mapped_action,
            case_name=context.case_name,
            run_id=context.run_id,
        )
        planned = self._request_plan(request_payload)
        metadata = dict(planned.metadata)
        metadata.setdefault("task", task)
        metadata.setdefault("source", "browser-use-real-model")
        metadata.setdefault(
            "planner",
            {
                "provider": "remote-http",
                "name": self._model,
                "kind": "real-model",
                "endpoint": self._endpoint,
            },
        )
        metadata.setdefault(
            "actions",
            [
                {
                    "action": planned.action,
                    "target": planned.target,
                    "value": planned.value,
                }
            ],
        )

        return BrowserUsePlan(
            action=planned.action,
            target=planned.target,
            value=planned.value,
            metadata=metadata,
        )


def detect_browser_use_dependency() -> tuple[bool, str]:
    """Detect whether browser-use package is importable in current environment."""
    spec = find_spec("browser_use")
    if spec is None:
        return False, "dependency-missing"
    return True, "available"


def create_browser_use_adapter(
    enabled: bool,
    *,
    planner: str = "model-stub",
    model: str = "stub-rule-v1",
    planner_endpoint: str = "",
    planner_api_key: str = "",
) -> tuple[BrowserUseAdapter | None, dict[str, Any]]:
    """Create browser-use adapter with explicit dependency detection and fallback status."""
    if not enabled:
        return None, {
            "enabled": False,
            "available": False,
            "mode": "disabled",
            "fallback": "task-mapping",
            "planner": planner,
        }

    available, reason = detect_browser_use_dependency()
    if not available:
        return None, {
            "enabled": True,
            "available": False,
            "mode": "degraded",
            "reason": reason,
            "fallback": "task-mapping",
            "planner": planner,
        }

    if planner == "real-model":
        if not planner_endpoint:
            return None, {
                "enabled": True,
                "available": True,
                "mode": "degraded",
                "reason": "planner-endpoint-missing",
                "fallback": "task-mapping",
                "planner": planner,
                "model": model,
            }

        return BrowserUseRealModelAdapter(
            endpoint=planner_endpoint,
            model=model,
            api_key=planner_api_key,
        ), {
            "enabled": True,
            "available": True,
            "mode": "real-model",
            "reason": reason,
            "fallback": "none",
            "planner": planner,
            "model": model,
            "endpoint": planner_endpoint,
        }

    return BrowserUseModelStubAdapter(), {
        "enabled": True,
        "available": True,
        "mode": "model-stub",
        "reason": reason,
        "fallback": "none",
        "planner": planner,
        "model": "stub-rule-v1",
    }
