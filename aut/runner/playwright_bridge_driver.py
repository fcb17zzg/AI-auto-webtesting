from __future__ import annotations

import base64
from datetime import UTC, datetime
from importlib.util import find_spec
import time
from typing import Any

from aut.dsl import ResolvedStep

from .assertions import PLAYWRIGHT_PAGE_KEY
from .browser_use_adapter import BROWSER_USE_ADAPTER_KEY, BrowserUsePlan
from .contracts import Driver, ExecutionContext, StepResult
from .playwright_task_mapper import PlaywrightTaskMapper

BROWSER_USE_PLAN_ACTION_WHITELIST = frozenset(
    {"goto", "click", "fill", "select_option", "wait", "assert_text_visible"}
)
STEP_SCREENSHOT_POLICY_KEY = "aut.capture.stepScreenshot"


class PlaywrightBridgeDriver(Driver):
    """Bridge driver that executes mapped AUT DSL actions in Playwright runtime."""

    def __init__(self):
        self.task_mapper = PlaywrightTaskMapper()

    def _is_playwright_available(self) -> bool:
        return find_spec("playwright") is not None

    def execute_step(self, step: ResolvedStep, context: ExecutionContext) -> StepResult:
        mapped_action = None
        try:
            mapped_action = self.task_mapper.map_task(step.task).to_dict()
        except ValueError:
            mapped_action = None

        if not self._is_playwright_available():
            return self._finalize_step_result(
                step,
                context,
                StepResult(
                    task=step.task,
                    success=False,
                    message="playwright dependency is not installed",
                    artifacts={
                        "driver": "playwright",
                        "integration": "dependency-missing",
                        "mapping": {
                            "supported": mapped_action is not None,
                            "action": mapped_action,
                        },
                    },
                ),
            )

        if mapped_action is None:
            return self._finalize_step_result(
                step,
                context,
                StepResult(
                    task=step.task,
                    success=False,
                    message="playwright bridge cannot map current task yet",
                    artifacts={
                        "driver": "playwright",
                        "integration": "entrypoint-ready",
                        "mapping": {
                            "supported": False,
                            "action": None,
                        },
                    },
                ),
            )

        browser_use_artifacts: dict[str, Any] = {
            "enabled": False,
            "planned": False,
            "plan": None,
            "executionSource": "task-mapping",
            "whitelist": sorted(BROWSER_USE_PLAN_ACTION_WHITELIST),
            "requestedAction": None,
            "whitelistDecision": "not-planned",
            "plannedActionCount": 1,
        }
        actions_to_execute = [mapped_action]
        try:
            browser_use_plan = self._plan_with_browser_use(step.task, mapped_action, context)
            if browser_use_plan is not None:
                actions_to_execute = self._map_browser_use_plan_to_actions(browser_use_plan)
                browser_use_artifacts = {
                    "enabled": True,
                    "planned": True,
                    "plan": browser_use_plan.to_dict(),
                    "executionSource": "browser-use-plan",
                    "whitelist": sorted(BROWSER_USE_PLAN_ACTION_WHITELIST),
                    "requestedAction": (browser_use_plan.action or "").strip().lower(),
                    "whitelistDecision": "allowed",
                    "plannedActionCount": len(actions_to_execute),
                }
        except Exception as exc:
            return self._finalize_step_result(
                step,
                context,
                StepResult(
                    task=step.task,
                    success=False,
                    message=f"browser-use plan failed: {exc}",
                    artifacts={
                        "driver": "playwright",
                        "integration": "browser-use-plan-failed",
                        "mapping": {
                            "supported": True,
                            "action": mapped_action,
                        },
                        "browserUse": {
                            "enabled": True,
                            "planned": False,
                            "plan": None,
                            "whitelist": sorted(BROWSER_USE_PLAN_ACTION_WHITELIST),
                            "requestedAction": None,
                            "whitelistDecision": "rejected",
                        },
                    },
                ),
            )

        try:
            page = self._ensure_runtime_page(context)
            for action_to_execute in actions_to_execute:
                self._execute_mapped_action(page, action_to_execute)
        except Exception as exc:
            return self._finalize_step_result(
                step,
                context,
                StepResult(
                    task=step.task,
                    success=False,
                    message=f"playwright action execution failed: {exc}",
                    artifacts={
                        "driver": "playwright",
                        "integration": "runtime-execution-failed",
                        "mapping": {
                            "supported": True,
                            "action": mapped_action,
                        },
                        "browserUse": browser_use_artifacts,
                    },
                ),
            )

        return self._finalize_step_result(
            step,
            context,
            StepResult(
                task=step.task,
                success=True,
                message="playwright action executed",
                artifacts={
                    "driver": "playwright",
                    "integration": "runtime-executed",
                    "mapping": {
                        "supported": True,
                        "action": mapped_action,
                    },
                    "execution": {
                        "source": browser_use_artifacts["executionSource"],
                        "action": actions_to_execute[-1],
                        "actions": actions_to_execute,
                    },
                    "browserUse": browser_use_artifacts,
                },
            ),
        )

    def _plan_with_browser_use(
        self,
        task: str,
        mapped_action: dict[str, Any],
        context: ExecutionContext,
    ) -> BrowserUsePlan | None:
        adapter = context.variables.get(BROWSER_USE_ADAPTER_KEY)
        if adapter is None:
            return None

        plan = adapter.plan(task=task, mapped_action=mapped_action, context=context)
        if not isinstance(plan, BrowserUsePlan):
            raise TypeError("browser-use adapter must return BrowserUsePlan")
        return plan

    def _map_browser_use_plan_to_actions(self, plan: BrowserUsePlan) -> list[dict[str, Any]]:
        metadata_actions = plan.metadata.get("actions")
        if isinstance(metadata_actions, list) and metadata_actions:
            mapped_actions: list[dict[str, Any]] = []
            for index, action_payload in enumerate(metadata_actions):
                if not isinstance(action_payload, dict):
                    raise ValueError(
                        f"unsupported browser-use plan action payload at index {index}: {action_payload}"
                    )
                mapped_actions.append(self._normalize_browser_use_action(action_payload))
            return mapped_actions

        return [
            self._normalize_browser_use_action(
                {
                    "action": plan.action,
                    "target": plan.target,
                    "value": plan.value,
                    "options": plan.metadata.get("options"),
                }
            )
        ]

    def _normalize_browser_use_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        action = str(payload.get("action", "")).strip().lower()
        if action not in BROWSER_USE_PLAN_ACTION_WHITELIST:
            raise ValueError(f"unsupported browser-use plan action: {payload.get('action')}")

        normalized_action: dict[str, Any] = {
            "action": action,
            "target": str(payload.get("target", "")),
            "value": str(payload.get("value", "")),
        }
        options = payload.get("options")
        if isinstance(options, dict) and options:
            normalized_action["options"] = options
        return normalized_action

    def _finalize_step_result(
        self,
        step: ResolvedStep,
        context: ExecutionContext,
        result: StepResult,
    ) -> StepResult:
        self._capture_step_screenshot(step, context, result)
        return result

    def _capture_step_screenshot(
        self,
        step: ResolvedStep,
        context: ExecutionContext,
        result: StepResult,
    ) -> None:
        policy = str(context.variables.get(STEP_SCREENSHOT_POLICY_KEY, "never")).strip().lower()
        if policy not in {"never", "on-failure", "always"}:
            policy = "never"

        should_capture = policy == "always" or (policy == "on-failure" and not result.success)
        if not should_capture:
            return

        page = context.variables.get(PLAYWRIGHT_PAGE_KEY)
        screenshot = getattr(page, "screenshot", None) if page is not None else None
        if not callable(screenshot):
            return

        observability = result.artifacts.setdefault("observability", {})
        if not isinstance(observability, dict):
            observability = {}
            result.artifacts["observability"] = observability

        try:
            raw_content = screenshot(full_page=True)
            if isinstance(raw_content, str):
                raw_bytes = raw_content.encode("utf-8")
            elif isinstance(raw_content, bytes):
                raw_bytes = raw_content
            else:
                raw_bytes = bytes(raw_content)
            encoded = base64.b64encode(raw_bytes).decode("ascii")
            attachments = result.artifacts.setdefault("attachments", [])
            if not isinstance(attachments, list):
                attachments = []
                result.artifacts["attachments"] = attachments
            attachments.append(
                {
                    "name": f"step-screenshot-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                    "contentType": "image/png",
                    "encoding": "base64",
                    "content": encoded,
                    "metadata": {
                        "task": step.task,
                        "policy": policy,
                    },
                }
            )
            observability["screenshot"] = {
                "captured": True,
                "policy": policy,
                "reason": "failure" if not result.success else "always",
            }
        except Exception as exc:
            observability["screenshot"] = {
                "captured": False,
                "policy": policy,
                "error": str(exc),
            }

    def _ensure_runtime_page(self, context: ExecutionContext) -> Any:
        page = context.variables.get(PLAYWRIGHT_PAGE_KEY)
        if page is not None:
            return page

        page = self._create_runtime_page(context)
        context.variables[PLAYWRIGHT_PAGE_KEY] = page
        return page

    def _create_runtime_page(self, context: ExecutionContext) -> Any:
        from playwright.sync_api import sync_playwright

        runtime = sync_playwright().start()
        browser = runtime.chromium.launch(headless=True)
        browser_context = browser.new_context()
        page = browser_context.new_page()

        context.variables.setdefault("playwright.runtime", runtime)
        context.variables.setdefault("playwright.browser", browser)
        context.variables.setdefault("playwright.browser_context", browser_context)
        return page

    def _execute_mapped_action(self, page: Any, mapped_action: dict[str, Any]) -> None:
        action = mapped_action.get("action")
        target = str(mapped_action.get("target", ""))
        value = str(mapped_action.get("value", ""))
        options = mapped_action.get("options") or {}

        if action == "goto":
            page.goto(target)
            return
        if action == "click":
            if target == "role=button":
                locator = page.get_by_role("button", name=value, **options)
            else:
                locator = page.locator(target)
            locator.click()
            return
        if action == "fill":
            page.get_by_label(target, exact=True).fill(value)
            return
        if action == "select_option":
            page.get_by_label(target, exact=True).select_option(value=value)
            return
        if action == "wait":
            seconds = float(options.get("seconds", value or 0.0))
            time.sleep(seconds)
            return
        if action == "assert_text_visible":
            locator = page.get_by_text(value, exact=bool(options.get("exact", True)))
            is_visible = getattr(locator, "is_visible", None)
            if not callable(is_visible) or not bool(is_visible()):
                raise RuntimeError(f"text not visible: {value}")
            return

        raise ValueError(f"Unsupported mapped action: {action}")

    def close(self, context: ExecutionContext) -> None:
        lifecycle_items = [
            (PLAYWRIGHT_PAGE_KEY, "close"),
            ("playwright.browser_context", "close"),
            ("playwright.browser", "close"),
            ("playwright.runtime", "stop"),
        ]
        errors: list[str] = []
        for key, method_name in lifecycle_items:
            resource = context.variables.pop(key, None)
            if resource is None:
                continue
            close_method = getattr(resource, method_name, None)
            if not callable(close_method):
                continue
            try:
                close_method()
            except Exception as exc:
                errors.append(f"{key}: {exc}")

        if errors:
            raise RuntimeError("; ".join(errors))
