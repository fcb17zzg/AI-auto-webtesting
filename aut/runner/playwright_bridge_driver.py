from __future__ import annotations

from importlib.util import find_spec
from typing import Any

from aut.dsl import ResolvedStep

from .assertions import PLAYWRIGHT_PAGE_KEY
from .browser_use_adapter import BROWSER_USE_ADAPTER_KEY, BrowserUsePlan
from .contracts import Driver, ExecutionContext, StepResult
from .playwright_task_mapper import PlaywrightTaskMapper


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
            return StepResult(
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
            )

        if mapped_action is None:
            return StepResult(
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
            )

        browser_use_artifacts: dict[str, Any] = {
            "enabled": False,
            "planned": False,
            "plan": None,
            "executionSource": "task-mapping",
        }
        action_to_execute = mapped_action
        try:
            browser_use_plan = self._plan_with_browser_use(step.task, mapped_action, context)
            if browser_use_plan is not None:
                action_to_execute = self._map_browser_use_plan_to_action(browser_use_plan)
                browser_use_artifacts = {
                    "enabled": True,
                    "planned": True,
                    "plan": browser_use_plan.to_dict(),
                    "executionSource": "browser-use-plan",
                }
        except Exception as exc:
            return StepResult(
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
                    },
                },
            )

        try:
            page = self._ensure_runtime_page(context)
            self._execute_mapped_action(page, action_to_execute)
        except Exception as exc:
            return StepResult(
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
            )

        return StepResult(
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
                    "action": action_to_execute,
                },
                "execution": {
                    "source": browser_use_artifacts["executionSource"],
                    "action": action_to_execute,
                },
                "browserUse": browser_use_artifacts,
            },
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

    def _map_browser_use_plan_to_action(self, plan: BrowserUsePlan) -> dict[str, Any]:
        action = (plan.action or "").strip().lower()
        if action not in {"goto", "click", "fill"}:
            raise ValueError(f"unsupported browser-use plan action: {plan.action}")

        mapped_action: dict[str, Any] = {
            "action": action,
            "target": plan.target,
            "value": plan.value,
        }
        options = plan.metadata.get("options")
        if isinstance(options, dict) and options:
            mapped_action["options"] = options
        return mapped_action

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
