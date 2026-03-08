from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from .contracts import ExecutionContext

BROWSER_USE_ADAPTER_KEY = "browser_use.adapter"


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
