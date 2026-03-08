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
- `--allure-results-dir`：当启用 `--run` 时，额外落盘 Allure 实体文件（`*-result.json`、`*-container.json`、附件）

示例（Playwright 真实动作执行）：

```bash
python -m aut.runner.cli --case cases/product/create_vpc.yaml --run --driver playwright --replay-dir .aut/replays --var ASCM_URL=http://example.com --var USERNAME=tester --var PASSWORD=secret --var DEFAULT_ORG_ID=org-1 --var VPC_NAME_UNIQUE=vpc-demo
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

## 当前说明

当前 `playwright` 驱动已接入真实动作执行链路：可在 runtime page 可用时执行 `goto/click/fill`，并将执行结果写入 replay 与报告链路。执行结束后会自动释放 runtime `page/context/browser` 资源。默认 `dry-run` 仍用于稳定主链路。

当前 task mapping 首版支持：

- `打开 "URL"` -> `goto`
- `点击“按钮文案”按钮` -> `click`
- `在“输入框文案”输入框输入“值”` -> `fill`

对于未覆盖的 task 模式，桥接驱动会在 `artifacts.mapping.supported` 返回 `false`，用于后续补齐映射规则。

断言执行链路已接入 `PlaywrightAssertionExecutor`：

- 当 `ExecutionContext.variables["playwright.page"]` 可用时，会尝试执行真实 `expect(locator).method(...)`
- 当运行态 page 尚不可用时，会回退到结构化断言校验，保持现有 dry-run 与桥接链路稳定

断言失败附件策略：

- 真实 Playwright 断言失败时，会尝试采集整页截图（`page.screenshot(full_page=True)`）
- 截图会以附件元数据写入 replay step artifacts，并在 Allure 落盘时输出为 png 附件
- 失败上下文仍会输出文本附件，便于与截图联合排障
