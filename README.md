# AUT MVP

AUT 是一个面向内部 Web 管理后台的 AI 前端自动化测试框架原型项目。

当前版本已完成：

- 项目骨架
- YAML DSL 最小解析器
- `preSteps` 递归展开
- Jinja2 变量替换
- CLI 执行计划查看入口
- 示例用例与单元测试

## 目录结构

```text
browse_auto_test/
  aut/
    config/
    dsl/
    runner/
  cases/
    common/
    product/
  tests/
  prd.md
  progress.md
  README.md
```

## 安装依赖

```bash
pip install -e .
```

## 查看执行计划

```bash
python -m aut.runner.cli --case cases/product/create_vpc.yaml --var ASCM_URL=http://example.com --var DEFAULT_ORG_ID=default-org --var VPC_NAME_UNIQUE=vpc-demo
```

当使用 `--run` 执行时，输出中会包含 `report.allure` 字段，用于承载步骤、断言与失败上下文的最小映射。

可选参数：

- `--driver`：执行驱动选择，当前支持 `dry-run`（默认）与 `playwright`（真实动作执行）
- `--capture-step-screenshot`：步骤截图采集策略（`never` / `on-failure` / `always`，默认 `never`）
- `--capture-step-log`：开启步骤级日志观测字段（默认关闭）
- `--enable-browser-use`：开启 browser-use 规划适配（仅 `--run --driver playwright` 生效）
- `--allure-results-dir`：当启用 `--run` 时，额外落盘 Allure 实体文件（`*-result.json`、`*-container.json`、附件）

示例（Playwright 真实动作执行）：

```bash
python -m aut.runner.cli --case cases/product/create_vpc.yaml --run --driver playwright --replay-dir .aut/replays --var ASCM_URL=http://example.com --var USERNAME=tester --var PASSWORD=secret --var DEFAULT_ORG_ID=org-1 --var VPC_NAME_UNIQUE=vpc-demo
```

示例（启用步骤截图与日志观测）：

```bash
python -m aut.runner.cli --case cases/common/playwright_e2e_demo.yaml --run --driver playwright --capture-step-screenshot on-failure --capture-step-log --replay-dir .aut/replays --allure-results-dir .aut/allure-results
```

示例（启用 browser-use 适配；依赖缺失时自动降级到 task mapping）：

```bash
python -m aut.runner.cli --case cases/common/playwright_e2e_demo.yaml --run --driver playwright --enable-browser-use --replay-dir .aut/replays
```

示例（dry-run + Allure 实体落盘）：

```bash
python -m aut.runner.cli --case cases/product/create_vpc.yaml --run --allure-results-dir .aut/allure-results --replay-dir .aut/replays --var ASCM_URL=http://example.com --var USERNAME=tester --var PASSWORD=secret --var DEFAULT_ORG_ID=org-1 --var VPC_NAME_UNIQUE=vpc-demo
```

## 运行测试

```bash
pytest
```

## 批量调度 YAML 用例（pytest 入口）

```bash
python -m aut.runner.cli --run-pytest --case-root cases --case-filter vpc --replay-dir .aut/replays
```

如需同时落盘 Allure 实体文件（`allure-results`）：

```bash
python -m aut.runner.cli --run-pytest --case-root cases --case-filter vpc --replay-dir .aut/replays --allure-results-dir .aut/allure-results
```

可选参数：

- `--case-glob`：按 glob 匹配 YAML（默认 `**/*.yaml`）
- `--case-filter`：按用例路径/文件名包含匹配
- `--pytest-arg`：透传 pytest 参数（可重复）
- `--allure-results-dir`：在调度完成后将新生成 replay 批量转换为 Allure `result/container/attachment` 文件

示例（Playwright 端到端样例 + Allure 附件落盘）：

```bash
python -m aut.runner.cli --case cases/common/playwright_e2e_demo.yaml --run --driver playwright --replay-dir .aut/replays --allure-results-dir .aut/allure-results
```

`cases/common/playwright_e2e_demo.yaml` 支持可选变量（未传入时使用默认值）：

- `LOGIN_URL`（默认 `http://example.com/login`）
- `LOGIN_USERNAME_LABEL`（默认 `用户名`）
- `LOGIN_USERNAME`（默认 `tester`）
- `LOGIN_BUTTON_TEXT`（默认 `登录`）
- `LOGIN_SUCCESS_TEXT`（默认 `登录成功`）

示例（覆盖端到端样例变量）：

```bash
python -m aut.runner.cli --case cases/common/playwright_e2e_demo.yaml --run --driver playwright --replay-dir .aut/replays --allure-results-dir .aut/allure-results --var LOGIN_URL=http://example.com/signin --var LOGIN_USERNAME_LABEL=账号 --var LOGIN_USERNAME=alice --var LOGIN_BUTTON_TEXT=立即登录 --var LOGIN_SUCCESS_TEXT=欢迎回来
```

## 当前说明

当前 `playwright` 驱动已接入真实动作执行链路：可在 runtime page 可用时执行 `goto/click/fill`，并将执行结果写入 replay 与报告链路。执行结束后会自动释放 runtime `page/context/browser` 资源。默认 `dry-run` 仍用于稳定主链路。

browser-use 规划动作白名单（当前版本）：

- `goto`
- `click`
- `fill`
- `select_option`
- `wait`
- `assert_text_visible`

当启用 `--enable-browser-use` 时，CLI 会进行依赖探测：

- 依赖可用：注入最小 `passthrough` adapter，驱动优先尝试 browser-use 规划
- 依赖缺失：写入 `browser_use.status` 降级状态并回退到 task mapping 主链路

当 `ExecutionContext.variables["browser_use.adapter"]` 提供规划器时，驱动会优先尝试执行 browser-use 规划；若规划动作不在白名单内，将返回 `browser-use-plan-failed`，并回传失败上下文用于排障。

browser-use 可观测性字段（`StepResult.artifacts.browserUse`）：

- `enabled`：是否启用 browser-use 规划挂点
- `planned`：是否成功产出可执行规划
- `plan`：规划详情（`action/target/value/metadata`）
- `whitelist`：当前允许执行的动作清单
- `requestedAction`：规划器请求的动作（标准化为小写）
- `whitelistDecision`：白名单判定（`allowed` / `rejected` / `not-planned`）
- `plannedActionCount`：最终被接受并将执行的动作数量

复杂任务拆分协议（browser-use -> 多动作执行）：

- 单动作模式：沿用 `BrowserUsePlan` 顶层 `action/target/value` 字段
- 多动作模式：在 `BrowserUsePlan.metadata.actions` 传入动作数组，每个元素形如 `{action, target, value, options?}`
- 驱动会逐个动作按顺序执行，并在 `StepResult.artifacts.execution.actions` 输出完整执行计划
- `StepResult.artifacts.execution.action` 保留为“最后一个已执行动作”，便于兼容既有消费者

执行来源字段（`StepResult.artifacts.execution.source`）：

- `task-mapping`：由 DSL task mapping 直接执行
- `browser-use-plan`：由 browser-use 规划映射后执行

步骤级可观测性字段（`StepResult.artifacts.observability`）：

- `stepIndex`：步骤序号（从 1 开始）
- `startedAt` / `finishedAt` / `durationMs`：执行时间线
- `capture.stepScreenshotPolicy`：当前截图策略快照
- `capture.stepLogEnabled`：当前日志采集开关
- `logs`：当启用 `--capture-step-log` 时写入的步骤日志数组
- `screenshot`：当触发步骤截图采集时的执行结果（是否成功、策略、失败原因等）

当前 task mapping 首版支持：

- `打开 "URL"` -> `goto`
- `点击“按钮文案”按钮` -> `click`
- `在“输入框文案”输入框输入“值”` -> `fill`
- `在“下拉框文案”下拉框选择“值”` -> `select_option`
- `等待 N 秒` -> `wait`
- `断言“文本”文本可见` -> `assert_text_visible`

对于未覆盖的 task 模式，桥接驱动会在 `artifacts.mapping.supported` 返回 `false`，用于后续补齐映射规则。

断言执行链路已接入 `PlaywrightAssertionExecutor`：

- 当 `ExecutionContext.variables["playwright.page"]` 可用时，会尝试执行真实 `expect(locator).method(...)`
- 当运行态 page 尚不可用时，会回退到结构化断言校验，保持现有 dry-run 与桥接链路稳定

断言失败附件策略：

- 真实 Playwright 断言失败时，会尝试采集整页截图（`page.screenshot(full_page=True)`）
- 截图会以附件元数据写入 replay step artifacts，并在 Allure 落盘时输出为 png 附件
- 失败上下文仍会输出文本附件，便于与截图联合排障
