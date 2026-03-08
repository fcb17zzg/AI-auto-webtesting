from __future__ import annotations

from dataclasses import dataclass, field
from importlib.util import find_spec
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


def detect_browser_use_dependency() -> tuple[bool, str]:
    """Detect whether browser-use package is importable in current environment."""
    spec = find_spec("browser_use")
    if spec is None:
        return False, "dependency-missing"
    return True, "available"


def create_browser_use_adapter(
    enabled: bool,
) -> tuple[BrowserUseAdapter | None, dict[str, Any]]:
    """Create browser-use adapter with explicit dependency detection and fallback status."""
    if not enabled:
        return None, {
            "enabled": False,
            "available": False,
            "mode": "disabled",
            "fallback": "task-mapping",
        }

    available, reason = detect_browser_use_dependency()
    if not available:
        return None, {
            "enabled": True,
            "available": False,
            "mode": "degraded",
            "reason": reason,
            "fallback": "task-mapping",
        }

    return BrowserUseModelStubAdapter(), {
        "enabled": True,
        "available": True,
        "mode": "model-stub",
        "reason": reason,
        "fallback": "none",
        "planner": "stub-rule-v1",
    }
