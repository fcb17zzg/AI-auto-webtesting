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

- `--driver`：执行驱动选择，当前支持 `dry-run`（默认）与 `playwright`（桥接接入点评估）
- `--allure-results-dir`：当启用 `--run` 时，额外落盘 Allure 实体文件（`*-result.json`、`*-container.json`、附件）

示例（Playwright 桥接接入点评估）：

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

## 当前说明

当前 `playwright` 驱动为桥接模式：用于验证依赖探测与接入点连通性，尚未把 DSL `task` 映射为真实浏览器动作。默认 `dry-run` 仍用于稳定主链路。
