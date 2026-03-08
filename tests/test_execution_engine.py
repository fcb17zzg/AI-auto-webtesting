from pathlib import Path

from aut.dsl.models import ResolvedCase, ResolvedStep
from aut.runner import DryRunDriver, ExecutionContext, ExecutionEngine
from aut.runner.browser_use_adapter import BROWSER_USE_ADAPTER_KEY, BrowserUsePlan
from aut.runner.contracts import AssertionResult, AssertionExecutor, Driver, StepResult
from aut.runner.playwright_bridge_driver import PlaywrightBridgeDriver


def test_execution_engine_runs_all_steps_with_dry_run_driver() -> None:
    case = ResolvedCase(
        name="demo",
        path=Path("demo.yaml"),
        description="",
        steps=[
            ResolvedStep(task="step-1", source=Path("demo.yaml")),
            ResolvedStep(task="step-2", source=Path("demo.yaml")),
        ],
    )
    context = ExecutionContext(case_name="demo", run_id="run-001")
    engine = ExecutionEngine(DryRunDriver())

    results = engine.run_case(case, context)

    assert len(results) == 2
    assert all(item.success for item in results)
    assert results[0].artifacts["run_id"] == "run-001"


def test_execution_engine_records_assertion_artifacts_when_passed() -> None:
    case = ResolvedCase(
        name="demo",
        path=Path("demo.yaml"),
        description="",
        steps=[
            ResolvedStep(
                task="step-1",
                source=Path("demo.yaml"),
                expected=[
                    {
                        "type": "playwright",
                        "locator": "get_by_text('ok')",
                        "method": "to_be_visible()",
                    }
                ],
            )
        ],
    )
    context = ExecutionContext(case_name="demo", run_id="run-001")
    engine = ExecutionEngine(DryRunDriver())

    results = engine.run_case(case, context)

    assert len(results) == 1
    assert results[0].success is True
    assert "assertions" in results[0].artifacts
    assert results[0].artifacts["assertions"][0]["passed"] is True


def test_execution_engine_adds_observability_fields_by_default() -> None:
    case = ResolvedCase(
        name="demo",
        path=Path("demo.yaml"),
        description="",
        steps=[ResolvedStep(task="step-1", source=Path("demo.yaml"))],
    )
    context = ExecutionContext(case_name="demo", run_id="run-ob-001")
    engine = ExecutionEngine(DryRunDriver())

    results = engine.run_case(case, context)

    observability = results[0].artifacts["observability"]
    assert observability["stepIndex"] == 1
    assert "startedAt" in observability
    assert "finishedAt" in observability
    assert observability["durationMs"] >= 0
    assert observability["capture"]["stepScreenshotPolicy"] == "never"
    assert observability["capture"]["stepLogEnabled"] is False


def test_execution_engine_records_step_logs_when_enabled() -> None:
    case = ResolvedCase(
        name="demo",
        path=Path("demo.yaml"),
        description="",
        steps=[ResolvedStep(task="step-1", source=Path("demo.yaml"))],
    )
    context = ExecutionContext(
        case_name="demo",
        run_id="run-ob-002",
        variables={"aut.capture.stepLog": True},
    )
    engine = ExecutionEngine(DryRunDriver())

    results = engine.run_case(case, context)

    logs = results[0].artifacts["observability"]["logs"]
    assert len(logs) == 1
    assert logs[0]["level"] == "info"
    assert "step[1]" in logs[0]["message"]


class FailOnSecondStepDriver(Driver):
    def execute_step(self, step: ResolvedStep, context: ExecutionContext) -> StepResult:
        if step.task == "step-2":
            return StepResult(task=step.task, success=False, message="forced failure")
        return StepResult(task=step.task, success=True)


class _CloseAwareDriver(Driver):
    def __init__(self, raise_on_close: bool = False):
        self.closed = False
        self.raise_on_close = raise_on_close

    def execute_step(self, step: ResolvedStep, context: ExecutionContext) -> StepResult:
        _ = context
        return StepResult(task=step.task, success=True)

    def close(self, context: ExecutionContext) -> None:
        _ = context
        self.closed = True
        if self.raise_on_close:
            raise RuntimeError("cleanup boom")


def test_execution_engine_stops_when_step_failed() -> None:
    case = ResolvedCase(
        name="demo",
        path=Path("demo.yaml"),
        description="",
        steps=[
            ResolvedStep(task="step-1", source=Path("demo.yaml")),
            ResolvedStep(task="step-2", source=Path("demo.yaml")),
            ResolvedStep(task="step-3", source=Path("demo.yaml")),
        ],
    )
    context = ExecutionContext(case_name="demo", run_id="run-002")
    engine = ExecutionEngine(FailOnSecondStepDriver())

    results = engine.run_case(case, context)

    assert len(results) == 2
    assert results[-1].success is False
    assert results[-1].message == "forced failure"


def test_execution_engine_calls_driver_close_after_run() -> None:
    case = ResolvedCase(
        name="demo",
        path=Path("demo.yaml"),
        description="",
        steps=[ResolvedStep(task="step-1", source=Path("demo.yaml"))],
    )
    context = ExecutionContext(case_name="demo", run_id="run-close-001")
    driver = _CloseAwareDriver()
    engine = ExecutionEngine(driver)

    results = engine.run_case(case, context)

    assert len(results) == 1
    assert results[0].success is True
    assert driver.closed is True


def test_execution_engine_appends_cleanup_failure_result_when_driver_close_raises() -> None:
    case = ResolvedCase(
        name="demo",
        path=Path("demo.yaml"),
        description="",
        steps=[ResolvedStep(task="step-1", source=Path("demo.yaml"))],
    )
    context = ExecutionContext(case_name="demo", run_id="run-close-002")
    driver = _CloseAwareDriver(raise_on_close=True)
    engine = ExecutionEngine(driver)

    results = engine.run_case(case, context)

    assert len(results) == 2
    assert results[0].success is True
    assert results[-1].task == "__driver_cleanup__"
    assert results[-1].success is False
    assert "cleanup boom" in results[-1].message


def test_execution_engine_stops_when_assertion_failed() -> None:
    case = ResolvedCase(
        name="demo",
        path=Path("demo.yaml"),
        description="",
        steps=[
            ResolvedStep(task="step-1", source=Path("demo.yaml")),
            ResolvedStep(
                task="step-2",
                source=Path("demo.yaml"),
                expected=[
                    {
                        "type": "playwright",
                        "locator": "get_by_text('boom')",
                        "method": "force_fail()",
                    }
                ],
            ),
            ResolvedStep(task="step-3", source=Path("demo.yaml")),
        ],
    )
    context = ExecutionContext(case_name="demo", run_id="run-003")
    engine = ExecutionEngine(DryRunDriver())

    results = engine.run_case(case, context)

    assert len(results) == 2
    assert results[-1].success is False
    assert "assertion failed" in results[-1].message
    assert results[-1].artifacts["assertions"][0]["reason"] == "forced assertion failure"


class _AttachmentAssertionExecutor(AssertionExecutor):
    def evaluate(self, expected, context):
        _ = expected, context
        return [
            AssertionResult(
                type="playwright",
                locator='get_by_text("boom")',
                method="to_be_visible()",
                passed=False,
                reason="playwright assertion failed",
                artifacts={
                    "attachments": [
                        {
                            "name": "assertion-failure-screenshot",
                            "contentType": "image/png",
                            "encoding": "base64",
                            "content": "ZmFrZQ==",
                        }
                    ]
                },
            )
        ]


def test_execution_engine_collects_assertion_attachments_to_step_artifacts() -> None:
    case = ResolvedCase(
        name="demo",
        path=Path("demo.yaml"),
        description="",
        steps=[
            ResolvedStep(
                task="step-1",
                source=Path("demo.yaml"),
                expected=[
                    {
                        "type": "playwright",
                        "locator": 'get_by_text("boom")',
                        "method": "to_be_visible()",
                    }
                ],
            )
        ],
    )
    context = ExecutionContext(case_name="demo", run_id="run-004")
    engine = ExecutionEngine(DryRunDriver(), assertion_executor=_AttachmentAssertionExecutor())

    results = engine.run_case(case, context)

    assert len(results) == 1
    assert results[0].success is False
    assert "attachments" in results[0].artifacts
    assert results[0].artifacts["attachments"][0]["name"] == "assertion-failure-screenshot"


def test_playwright_bridge_driver_marks_dependency_missing_when_unavailable(
    monkeypatch,
) -> None:
    step = ResolvedStep(task='打开 "http://example.com"', source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-004")
    driver = PlaywrightBridgeDriver()
    monkeypatch.setattr(driver, "_is_playwright_available", lambda: False)

    result = driver.execute_step(step, context)

    assert result.success is False
    assert "not installed" in result.message
    assert result.artifacts["integration"] == "dependency-missing"
    assert result.artifacts["mapping"]["supported"] is True
    assert result.artifacts["mapping"]["action"]["action"] == "goto"


def test_playwright_bridge_driver_reports_entrypoint_ready_when_dependency_present(
    monkeypatch,
) -> None:
    class _FakeLocator:
        def __init__(self):
            self.clicked = False

        def click(self):
            self.clicked = True

    class _FakePage:
        def __init__(self):
            self.last_role = None
            self.last_name = None
            self.last_options = {}
            self.locator = _FakeLocator()

        def get_by_role(self, role, name, **kwargs):
            self.last_role = role
            self.last_name = name
            self.last_options = kwargs
            return self.locator

    step = ResolvedStep(task="点击“登录”按钮", source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-005")
    driver = PlaywrightBridgeDriver()
    fake_page = _FakePage()

    monkeypatch.setattr(driver, "_is_playwright_available", lambda: True)
    monkeypatch.setattr(driver, "_create_runtime_page", lambda _: fake_page)

    result = driver.execute_step(step, context)

    assert result.success is True
    assert "executed" in result.message
    assert result.artifacts["integration"] == "runtime-executed"
    assert result.artifacts["mapping"]["supported"] is True
    assert result.artifacts["mapping"]["action"]["action"] == "click"
    assert context.variables["playwright.page"] is fake_page
    assert fake_page.last_role == "button"
    assert fake_page.last_name == "登录"
    assert fake_page.last_options["exact"] is True
    assert fake_page.locator.clicked is True


def test_playwright_bridge_driver_returns_mapping_unsupported_for_unknown_task(
    monkeypatch,
) -> None:
    step = ResolvedStep(task="上传 文件", source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-006")
    driver = PlaywrightBridgeDriver()
    monkeypatch.setattr(driver, "_is_playwright_available", lambda: True)

    result = driver.execute_step(step, context)

    assert result.success is False
    assert "cannot map" in result.message
    assert result.artifacts["integration"] == "entrypoint-ready"
    assert result.artifacts["mapping"]["supported"] is False
    assert result.artifacts["mapping"]["action"] is None


def test_playwright_bridge_driver_executes_select_option_action(
    monkeypatch,
) -> None:
    class _FakeLocator:
        def __init__(self):
            self.selected = ""

        def select_option(self, value):
            self.selected = value

    class _FakePage:
        def __init__(self):
            self.label = ""
            self.locator = _FakeLocator()

        def get_by_label(self, label, exact=True):
            _ = exact
            self.label = label
            return self.locator

    step = ResolvedStep(task="在“地域”下拉框选择“华东1（杭州）”", source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-006-select")
    driver = PlaywrightBridgeDriver()
    fake_page = _FakePage()

    monkeypatch.setattr(driver, "_is_playwright_available", lambda: True)
    monkeypatch.setattr(driver, "_create_runtime_page", lambda _: fake_page)

    result = driver.execute_step(step, context)

    assert result.success is True
    assert result.artifacts["integration"] == "runtime-executed"
    assert result.artifacts["mapping"]["action"]["action"] == "select_option"
    assert fake_page.label == "地域"
    assert fake_page.locator.selected == "华东1（杭州）"


def test_playwright_bridge_driver_executes_wait_action(
    monkeypatch,
) -> None:
    class _FakePage:
        pass

    recorded_seconds: list[float] = []

    step = ResolvedStep(task="等待 1.5 秒", source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-006-wait")
    driver = PlaywrightBridgeDriver()

    monkeypatch.setattr(driver, "_is_playwright_available", lambda: True)
    monkeypatch.setattr(driver, "_create_runtime_page", lambda _: _FakePage())
    monkeypatch.setattr("aut.runner.playwright_bridge_driver.time.sleep", lambda s: recorded_seconds.append(s))

    result = driver.execute_step(step, context)

    assert result.success is True
    assert result.artifacts["integration"] == "runtime-executed"
    assert result.artifacts["mapping"]["action"]["action"] == "wait"
    assert recorded_seconds == [1.5]


def test_playwright_bridge_driver_executes_assert_text_visible_action(
    monkeypatch,
) -> None:
    class _FakeLocator:
        def __init__(self, visible: bool):
            self.visible = visible

        def is_visible(self):
            return self.visible

    class _FakePage:
        def __init__(self, visible: bool):
            self.visible = visible
            self.last_text = ""

        def get_by_text(self, text, exact=True):
            _ = exact
            self.last_text = text
            return _FakeLocator(self.visible)

    step = ResolvedStep(task="断言“登录成功”文本可见", source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-006-assert")
    driver = PlaywrightBridgeDriver()
    fake_page = _FakePage(visible=True)

    monkeypatch.setattr(driver, "_is_playwright_available", lambda: True)
    monkeypatch.setattr(driver, "_create_runtime_page", lambda _: fake_page)

    result = driver.execute_step(step, context)

    assert result.success is True
    assert result.artifacts["mapping"]["action"]["action"] == "assert_text_visible"
    assert fake_page.last_text == "登录成功"


def test_playwright_bridge_driver_returns_failed_when_assert_text_not_visible(
    monkeypatch,
) -> None:
    class _FakeLocator:
        def is_visible(self):
            return False

    class _FakePage:
        def get_by_text(self, text, exact=True):
            _ = text, exact
            return _FakeLocator()

    step = ResolvedStep(task="断言“登录成功”文本可见", source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-006-assert-failed")
    driver = PlaywrightBridgeDriver()

    monkeypatch.setattr(driver, "_is_playwright_available", lambda: True)
    monkeypatch.setattr(driver, "_create_runtime_page", lambda _: _FakePage())

    result = driver.execute_step(step, context)

    assert result.success is False
    assert result.artifacts["integration"] == "runtime-execution-failed"
    assert "text not visible" in result.message


def test_playwright_bridge_driver_returns_failed_when_action_execution_throws(
    monkeypatch,
) -> None:
    class _FakePage:
        def goto(self, url):
            _ = url
            raise RuntimeError("goto boom")

    step = ResolvedStep(task='打开 "http://example.com"', source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-007")
    driver = PlaywrightBridgeDriver()
    context.variables["playwright.page"] = _FakePage()

    monkeypatch.setattr(driver, "_is_playwright_available", lambda: True)

    result = driver.execute_step(step, context)

    assert result.success is False
    assert "execution failed" in result.message
    assert result.artifacts["integration"] == "runtime-execution-failed"
    assert result.artifacts["mapping"]["supported"] is True
    assert result.artifacts["mapping"]["action"]["action"] == "goto"


def test_playwright_bridge_driver_includes_browser_use_plan_when_adapter_present(
    monkeypatch,
) -> None:
    class _FakeLocator:
        def click(self):
            return None

    class _FakePage:
        def __init__(self):
            self.last_url = ""

        def get_by_role(self, role, name, **kwargs):
            _ = role, name, kwargs
            return _FakeLocator()

        def goto(self, url):
            self.last_url = url

    class _Adapter:
        def plan(self, *, task, mapped_action, context):
            _ = context
            return BrowserUsePlan(
                action="goto",
                target="http://browser-use-plan.example",
                value="",
                metadata={"task": task},
            )

    step = ResolvedStep(task="点击“登录”按钮", source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-008")
    context.variables[BROWSER_USE_ADAPTER_KEY] = _Adapter()

    driver = PlaywrightBridgeDriver()
    fake_page = _FakePage()
    monkeypatch.setattr(driver, "_is_playwright_available", lambda: True)
    monkeypatch.setattr(driver, "_create_runtime_page", lambda _: fake_page)

    result = driver.execute_step(step, context)

    assert result.success is True
    assert fake_page.last_url == "http://browser-use-plan.example"
    assert result.artifacts["execution"]["source"] == "browser-use-plan"
    assert result.artifacts["execution"]["action"]["action"] == "goto"
    assert result.artifacts["browserUse"]["enabled"] is True
    assert result.artifacts["browserUse"]["planned"] is True
    assert result.artifacts["browserUse"]["plan"]["action"] == "goto"
    assert result.artifacts["browserUse"]["plan"]["metadata"]["task"] == "点击“登录”按钮"
    assert sorted(result.artifacts["browserUse"]["whitelist"]) == ["click", "fill", "goto"]
    assert result.artifacts["browserUse"]["requestedAction"] == "goto"
    assert result.artifacts["browserUse"]["whitelistDecision"] == "allowed"
    assert result.artifacts["browserUse"]["plannedActionCount"] == 1
    assert len(result.artifacts["execution"]["actions"]) == 1


def test_playwright_bridge_driver_executes_browser_use_multi_action_plan(
    monkeypatch,
) -> None:
    class _FakeLabelLocator:
        def __init__(self, calls: list[str], label: str):
            self.calls = calls
            self.label = label

        def fill(self, value: str):
            self.calls.append(f"fill:{self.label}:{value}")

    class _FakeRoleLocator:
        def __init__(self, calls: list[str], name: str):
            self.calls = calls
            self.name = name

        def click(self):
            self.calls.append(f"click:{self.name}")

    class _FakePage:
        def __init__(self):
            self.calls: list[str] = []

        def get_by_label(self, label, exact=True):
            _ = exact
            return _FakeLabelLocator(self.calls, label)

        def get_by_role(self, role, name, **kwargs):
            _ = role, kwargs
            return _FakeRoleLocator(self.calls, name)

    class _Adapter:
        def plan(self, *, task, mapped_action, context):
            _ = task, mapped_action, context
            return BrowserUsePlan(
                action="fill",
                target="用户名",
                value="tester",
                metadata={
                    "actions": [
                        {"action": "fill", "target": "用户名", "value": "tester"},
                        {
                            "action": "click",
                            "target": "role=button",
                            "value": "登录",
                            "options": {"exact": True},
                        },
                    ]
                },
            )

    step = ResolvedStep(task="点击“登录”按钮", source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-008-multi")
    context.variables[BROWSER_USE_ADAPTER_KEY] = _Adapter()

    driver = PlaywrightBridgeDriver()
    fake_page = _FakePage()
    monkeypatch.setattr(driver, "_is_playwright_available", lambda: True)
    monkeypatch.setattr(driver, "_create_runtime_page", lambda _: fake_page)

    result = driver.execute_step(step, context)

    assert result.success is True
    assert fake_page.calls == ["fill:用户名:tester", "click:登录"]
    assert result.artifacts["execution"]["source"] == "browser-use-plan"
    assert len(result.artifacts["execution"]["actions"]) == 2
    assert result.artifacts["execution"]["action"]["action"] == "click"
    assert result.artifacts["browserUse"]["plannedActionCount"] == 2


def test_playwright_bridge_driver_fails_when_browser_use_multi_action_contains_unsupported_action(
    monkeypatch,
) -> None:
    class _Adapter:
        def plan(self, *, task, mapped_action, context):
            _ = task, mapped_action, context
            return BrowserUsePlan(
                action="fill",
                target="用户名",
                value="tester",
                metadata={
                    "actions": [
                        {"action": "fill", "target": "用户名", "value": "tester"},
                        {"action": "hover", "target": "#submit", "value": ""},
                    ]
                },
            )

    step = ResolvedStep(task="点击“登录”按钮", source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-008-unsupported")
    context.variables[BROWSER_USE_ADAPTER_KEY] = _Adapter()

    driver = PlaywrightBridgeDriver()
    monkeypatch.setattr(driver, "_is_playwright_available", lambda: True)

    result = driver.execute_step(step, context)

    assert result.success is False
    assert "unsupported browser-use plan action" in result.message
    assert result.artifacts["integration"] == "browser-use-plan-failed"
    assert result.artifacts["browserUse"]["whitelistDecision"] == "rejected"


def test_playwright_bridge_driver_captures_step_screenshot_when_policy_always(
    monkeypatch,
) -> None:
    class _FakePage:
        def goto(self, url):
            _ = url

        def screenshot(self, full_page=True):
            _ = full_page
            return b"fake-step-png"

    step = ResolvedStep(task='打开 "http://example.com"', source=Path("demo.yaml"))
    context = ExecutionContext(
        case_name="demo",
        run_id="run-010-screenshot",
        variables={"aut.capture.stepScreenshot": "always"},
    )

    driver = PlaywrightBridgeDriver()
    monkeypatch.setattr(driver, "_is_playwright_available", lambda: True)
    monkeypatch.setattr(driver, "_create_runtime_page", lambda _: _FakePage())

    result = driver.execute_step(step, context)

    assert result.success is True
    attachments = result.artifacts["attachments"]
    assert len(attachments) == 1
    assert attachments[0]["contentType"] == "image/png"
    assert attachments[0]["metadata"]["policy"] == "always"
    assert result.artifacts["observability"]["screenshot"]["captured"] is True


def test_playwright_bridge_driver_returns_failed_when_browser_use_plan_throws(
    monkeypatch,
) -> None:
    class _Adapter:
        def plan(self, *, task, mapped_action, context):
            _ = task, mapped_action, context
            raise RuntimeError("planner boom")

    step = ResolvedStep(task='打开 "http://example.com"', source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-009")
    context.variables[BROWSER_USE_ADAPTER_KEY] = _Adapter()

    driver = PlaywrightBridgeDriver()
    monkeypatch.setattr(driver, "_is_playwright_available", lambda: True)

    result = driver.execute_step(step, context)

    assert result.success is False
    assert "browser-use plan failed" in result.message
    assert result.artifacts["integration"] == "browser-use-plan-failed"
    assert result.artifacts["browserUse"]["enabled"] is True
    assert result.artifacts["browserUse"]["planned"] is False
    assert sorted(result.artifacts["browserUse"]["whitelist"]) == ["click", "fill", "goto"]
    assert result.artifacts["browserUse"]["whitelistDecision"] == "rejected"


def test_playwright_bridge_driver_returns_failed_when_browser_use_plan_action_unsupported(
    monkeypatch,
) -> None:
    class _Adapter:
        def plan(self, *, task, mapped_action, context):
            _ = task, mapped_action, context
            return BrowserUsePlan(action="hover", target="#submit")

    step = ResolvedStep(task="点击“登录”按钮", source=Path("demo.yaml"))
    context = ExecutionContext(case_name="demo", run_id="run-010")
    context.variables[BROWSER_USE_ADAPTER_KEY] = _Adapter()

    driver = PlaywrightBridgeDriver()
    monkeypatch.setattr(driver, "_is_playwright_available", lambda: True)

    result = driver.execute_step(step, context)

    assert result.success is False
    assert "unsupported browser-use plan action" in result.message
    assert result.artifacts["integration"] == "browser-use-plan-failed"
    assert sorted(result.artifacts["browserUse"]["whitelist"]) == ["click", "fill", "goto"]
    assert result.artifacts["browserUse"]["whitelistDecision"] == "rejected"


def test_playwright_bridge_driver_close_releases_runtime_resources() -> None:
    closed: list[str] = []

    class _FakeClosable:
        def __init__(self, name: str, close_method: str):
            self.name = name
            self.close_method = close_method

        def close(self):
            if self.close_method == "close":
                closed.append(self.name)

        def stop(self):
            if self.close_method == "stop":
                closed.append(self.name)

    context = ExecutionContext(case_name="demo", run_id="run-close-003")
    context.variables["playwright.page"] = _FakeClosable("page", "close")
    context.variables["playwright.browser_context"] = _FakeClosable("browser_context", "close")
    context.variables["playwright.browser"] = _FakeClosable("browser", "close")
    context.variables["playwright.runtime"] = _FakeClosable("runtime", "stop")

    driver = PlaywrightBridgeDriver()
    driver.close(context)

    assert closed == ["page", "browser_context", "browser", "runtime"]
    assert "playwright.page" not in context.variables
    assert "playwright.browser_context" not in context.variables
    assert "playwright.browser" not in context.variables
    assert "playwright.runtime" not in context.variables


def test_playwright_bridge_driver_close_raises_with_resource_errors() -> None:
    class _BrokenResource:
        def close(self):
            raise RuntimeError("close failed")

    context = ExecutionContext(case_name="demo", run_id="run-close-004")
    context.variables["playwright.page"] = _BrokenResource()

    driver = PlaywrightBridgeDriver()

    try:
        driver.close(context)
    except RuntimeError as exc:
        assert "playwright.page" in str(exc)
        assert "close failed" in str(exc)
    else:
        raise AssertionError("expected close to raise RuntimeError")