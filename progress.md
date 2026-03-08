# AUT 项目进度清单

## 当前状态

- 状态：进行中
- 阶段：M1 项目起步
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

## 进行中

- 按“一个功能一个验证”节奏推进下一功能（断言系统最小接口）

## 下一步

1. 设计并实现最小断言接口（`playwright`/`validator` 先占位）
2. 在 `ExecutionEngine` 中串联步骤断言执行
3. 补充失败上下文输出与回放关联字段
4. 为断言链路补充单元测试与示例 case

## 风险

- 当前仅完成离线解析与执行计划生成，尚未接入真实浏览器执行
- 模型与 browser-use 适配还未开始，后续可能影响接口设计

## 决策记录

- 首期不绑定具体模型供应商，保留可插拔接口
- 先做 CLI 和本地可运行主链路，再做服务化与平台集成
- 先实现 DSL 与执行计划，再接 driver/LLM/replay
