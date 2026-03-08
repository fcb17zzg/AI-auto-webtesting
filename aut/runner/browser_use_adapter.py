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


class BrowserUsePassthroughAdapter:
    """Minimal browser-use adapter that normalizes mapped action into BrowserUsePlan."""

    def plan(
        self,
        *,
        task: str,
        mapped_action: dict[str, Any],
        context: ExecutionContext,
    ) -> BrowserUsePlan:
        _ = context
        metadata: dict[str, Any] = {
            "task": task,
            "source": "browser-use-passthrough",
        }
        options = mapped_action.get("options")
        if isinstance(options, dict) and options:
            metadata["options"] = options
        return BrowserUsePlan(
            action=str(mapped_action.get("action", "")).strip().lower(),
            target=str(mapped_action.get("target", "")),
            value=str(mapped_action.get("value", "")),
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

    return BrowserUsePassthroughAdapter(), {
        "enabled": True,
        "available": True,
        "mode": "passthrough",
        "reason": reason,
        "fallback": "none",
    }
