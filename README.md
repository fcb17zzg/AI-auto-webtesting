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

## 运行测试

```bash
pytest
```

## 批量调度 YAML 用例（pytest 入口）

```bash
python -m aut.runner.cli --run-pytest --case-root cases --case-filter vpc --replay-dir .aut/replays
```

可选参数：

- `--case-glob`：按 glob 匹配 YAML（默认 `**/*.yaml`）
- `--case-filter`：按用例路径/文件名包含匹配
- `--pytest-arg`：透传 pytest 参数（可重复）

## 当前说明

当前 CLI 不会真正操作浏览器，而是输出解析后的执行计划。这一步用于先稳定 DSL、变量系统和前置步骤展开逻辑，后续再接入 driver、LLM 和 replay。
