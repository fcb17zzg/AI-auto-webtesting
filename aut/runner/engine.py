from __future__ import annotations

from datetime import UTC, datetime

from aut.dsl import ResolvedCase

from .assertions import PlaceholderAssertionExecutor
from .contracts import AssertionExecutor, Driver, ExecutionContext, StepResult


class ExecutionEngine:
    def __init__(
        self,
        driver: Driver,
        assertion_executor: AssertionExecutor | None = None,
    ):
        self.driver = driver
        self.assertion_executor = assertion_executor or PlaceholderAssertionExecutor()

    def run_case(self, case: ResolvedCase, context: ExecutionContext) -> list[StepResult]:
        results: list[StepResult] = []
        try:
            for step_index, step in enumerate(case.steps, start=1):
                started_at = datetime.now(UTC)
                result = self.driver.execute_step(step, context)
                if result.success and step.expected:
                    assertions = self.assertion_executor.evaluate(step.expected, context)
                    result.artifacts["assertions"] = [item.to_dict() for item in assertions]
                    attachment_items = [
                        attachment
                        for item in assertions
                        for attachment in item.artifacts.get("attachments", [])
                    ]
                    if attachment_items:
                        result.artifacts["attachments"] = attachment_items
                    first_failed = next((item for item in assertions if not item.passed), None)
                    if first_failed is not None:
                        result.success = False
                        result.message = (
                            f"assertion failed: {first_failed.type} "
                            f"{first_failed.locator} {first_failed.method}"
                        )
                self._attach_step_observability(
                    result=result,
                    context=context,
                    step_index=step_index,
                    started_at=started_at,
                )
                results.append(result)
                if not result.success:
                    break
        finally:
            cleanup_error = self._cleanup_driver(context)
            if cleanup_error is not None:
                results.append(
                    StepResult(
                        task="__driver_cleanup__",
                        success=False,
                        message=f"driver cleanup failed: {cleanup_error}",
                        artifacts={"phase": "cleanup"},
                    )
                )
        return results

    def _cleanup_driver(self, context: ExecutionContext) -> Exception | None:
        close = getattr(self.driver, "close", None)
        if not callable(close):
            return None
        try:
            close(context)
        except Exception as exc:  # pragma: no cover - error path tested via public API
            return exc
        return None

    def _attach_step_observability(
        self,
        *,
        result: StepResult,
        context: ExecutionContext,
        step_index: int,
        started_at: datetime,
    ) -> None:
        finished_at = datetime.now(UTC)
        duration_ms = max(0, int((finished_at - started_at).total_seconds() * 1000))

        policy = str(context.variables.get("aut.capture.stepScreenshot", "never")).lower().strip()
        if policy not in {"never", "on-failure", "always"}:
            policy = "never"
        log_enabled = self._is_enabled(context.variables.get("aut.capture.stepLog", False))

        observability = result.artifacts.setdefault("observability", {})
        if not isinstance(observability, dict):
            observability = {}
            result.artifacts["observability"] = observability

        observability.setdefault("stepIndex", step_index)
        observability.setdefault("startedAt", started_at.isoformat())
        observability["finishedAt"] = finished_at.isoformat()
        observability["durationMs"] = duration_ms
        observability["capture"] = {
            "stepScreenshotPolicy": policy,
            "stepLogEnabled": log_enabled,
        }

        if log_enabled:
            logs = observability.setdefault("logs", [])
            if not isinstance(logs, list):
                logs = []
                observability["logs"] = logs
            logs.append(
                {
                    "at": finished_at.isoformat(),
                    "level": "info",
                    "message": (
                        f"step[{step_index}] {result.task} "
                        f"-> {'success' if result.success else 'failed'}"
                    ),
                }
            )

    def _is_enabled(self, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)
