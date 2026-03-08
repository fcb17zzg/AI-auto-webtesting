from aut.runner.playwright_task_mapper import PlaywrightTaskMapper


def test_mapper_supports_open_url_task() -> None:
    mapper = PlaywrightTaskMapper()

    action = mapper.map_task('打开 "http://example.com/login"')

    assert action.action == "goto"
    assert action.target == "http://example.com/login"
    assert action.value == ""


def test_mapper_supports_click_button_task() -> None:
    mapper = PlaywrightTaskMapper()

    action = mapper.map_task("点击“登录”按钮")

    assert action.action == "click"
    assert action.target == "role=button"
    assert action.value == "登录"
    assert action.options["exact"] is True


def test_mapper_supports_fill_input_task() -> None:
    mapper = PlaywrightTaskMapper()

    action = mapper.map_task("在“用户名”输入框输入“tester”")

    assert action.action == "fill"
    assert action.target == "用户名"
    assert action.value == "tester"


def test_mapper_supports_select_option_task() -> None:
    mapper = PlaywrightTaskMapper()

    action = mapper.map_task("在“地域”下拉框选择“华东1（杭州）”")

    assert action.action == "select_option"
    assert action.target == "地域"
    assert action.value == "华东1（杭州）"


def test_mapper_supports_wait_task() -> None:
    mapper = PlaywrightTaskMapper()

    action = mapper.map_task("等待 1.5 秒")

    assert action.action == "wait"
    assert action.options["seconds"] == 1.5


def test_mapper_supports_assert_text_visible_task() -> None:
    mapper = PlaywrightTaskMapper()

    action = mapper.map_task("断言“登录成功”文本可见")

    assert action.action == "assert_text_visible"
    assert action.value == "登录成功"
    assert action.options["exact"] is True


def test_mapper_raises_for_unsupported_pattern() -> None:
    mapper = PlaywrightTaskMapper()

    try:
        mapper.map_task("上传 文件")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "Unsupported playwright task pattern" in str(exc)