# AUT 项目进度清单

## 当前状态

- 状态：进行中
- 阶段：M2 已完成（断言系统最小接口），M3 已完成首版（pytest/allure 报告链路）
- 更新时间：2026-03-08

## 已完成

- 从文章中抽取架构、流程、模块与实施顺序
- 确认首期边界：内部 B/S、CLI 优先、4 周 MVP
- 建立项目目录骨架
- 创建 `prd.md`
- 创建 `progress.md`
- 初始化项目基础代码与示例
- 完成 DSL 解析、示例用例与测试验证
- 新增执行抽象：`Driver` 协议、`ExecutionContext`、`StepResult`
- 新增 `ExecutionEngine` 与 `DryRunDriver`
- 新增执行引擎单元测试并通过
- 新增回放结构：`ReplayRecord`、`ReplayStepRecord`、`ReplayStore`
- CLI 新增 `--run` 与 `--replay-dir`，可执行 dry-run 并落盘 replay 文件
- 新增回放与 CLI 集成测试并通过（当前总计 7 条测试）
- 新增最小断言链路：`AssertionExecutor` 协议、`PlaceholderAssertionExecutor` 占位实现
- `ExecutionEngine` 串联步骤断言执行，断言失败可中断后续步骤
- 断言结果写入 `StepResult.artifacts.assertions` 并随 replay 落盘
- 新增断言相关单测与 CLI 集成测试并通过（当前总计 10 条测试）
- 新增 pytest 调度入口：`--run-pytest`，支持按 `--case-glob` 与 `--case-filter` 批量执行 case
- 新增调度入口测试与调度器基础单测
- 新增 Allure 报告最小字段映射：步骤、断言、失败上下文（`report.allure`）
- 新增 Allure 映射单测并通过
- 新增报告链路最小集成测试：覆盖失败样例与多 case 聚合
- `--run-pytest` 输出新增 `report.allureBatch` 聚合结果（summary + per-case 结果）
- 新增 CLI 驱动选择参数 `--driver`（`dry-run` / `playwright`）
- 新增 Playwright 桥接驱动接入点评估：可识别依赖缺失与入口就绪状态
- 新增 Playwright 桥接驱动与 CLI 驱动选择测试并通过（当前总计 23 条测试）
- 新增 Allure 实体落盘模块：`result/container/attachment` 文件生成
- CLI `--run` 新增 `--allure-results-dir`，可输出 `allure-results` 文件集
- 新增 Allure 实体落盘与 CLI 输出测试并通过（当前总计 26 条测试）
- 调度链路 `--run-pytest` 接入 `--allure-results-dir`，可按新 replay 批量落盘 Allure 文件
- 新增调度链路 Allure 批量落盘测试并通过（当前总计 27 条测试）

## 进行中

- 规划 Playwright 任务映射策略（DSL task -> 浏览器动作）

## 下一步

1. 规划 Playwright 任务映射策略（DSL task -> 浏览器动作）
2. 接入真实 Playwright 断言执行器（替换占位断言实现）
3. 增加断言失败截图与附件采集策略

## 风险

- 当前断言仍为占位执行器，尚未接入真实 Playwright 断言能力
- 模型与 browser-use 适配还未开始，后续可能影响接口设计

## 决策记录

- 首期不绑定具体模型供应商，保留可插拔接口
- 先做 CLI 和本地可运行主链路，再做服务化与平台集成
- 先实现 DSL 与执行计划，再接 driver/LLM/replay
