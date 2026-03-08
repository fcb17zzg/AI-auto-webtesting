from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PlaywrightAction:
    action: str
    target: str = ""
    value: str = ""
    options: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "target": self.target,
            "value": self.value,
            "options": self.options,
        }


class PlaywrightTaskMapper:
    """Map Chinese AUT DSL task text to a normalized Playwright action plan."""

    _OPEN_PATTERN = re.compile(r'^打开\s+"(?P<url>.+)"$')
    _CLICK_PATTERN = re.compile(r'^点击“(?P<label>.+)”按钮$')
    _FILL_PATTERN = re.compile(r'^在“(?P<label>.+)”输入框输入“(?P<value>.*)”$')

    def map_task(self, task: str) -> PlaywrightAction:
        task = task.strip()

        open_match = self._OPEN_PATTERN.match(task)
        if open_match:
            return PlaywrightAction(action="goto", target=open_match.group("url"))

        click_match = self._CLICK_PATTERN.match(task)
        if click_match:
            return PlaywrightAction(
                action="click",
                target="role=button",
                value=click_match.group("label"),
                options={"exact": True},
            )

        fill_match = self._FILL_PATTERN.match(task)
        if fill_match:
            return PlaywrightAction(
                action="fill",
                target=fill_match.group("label"),
                value=fill_match.group("value"),
            )

        raise ValueError(f"Unsupported playwright task pattern: {task}")