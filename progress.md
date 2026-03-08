# AUT 项目进度清单

## 当前状态

- 状态：进行中
- 阶段：M2 已完成（断言系统最小接口），进入 M3 准备（pytest/allure 报告链路）
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

## 进行中

- 按“一个功能一个验证”节奏推进下一功能（pytest/allure 报告链路）

## 下一步

1. 设计 pytest 调度入口（按 case 批量执行与用例筛选）
2. 规划 allure 报告字段映射（步骤、断言、失败上下文）
3. 为报告链路补充最小集成测试
4. 评估真实浏览器驱动接入点（与断言执行器对齐）

## 风险

- 当前断言仍为占位执行器，尚未接入真实 Playwright 断言能力
- 模型与 browser-use 适配还未开始，后续可能影响接口设计

## 决策记录

- 首期不绑定具体模型供应商，保留可插拔接口
- 先做 CLI 和本地可运行主链路，再做服务化与平台集成
- 先实现 DSL 与执行计划，再接 driver/LLM/replay
