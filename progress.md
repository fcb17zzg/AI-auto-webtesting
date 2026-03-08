# AUT 项目进度清单

## 当前状态

- 状态：进行中
- 阶段：M2 已完成（断言系统最小接口），M3 已完成首版（pytest/allure 报告链路）
- M4-1 已完成：Allure 映射新增 `steps[*].executionTrace` 与 `attachmentRefs` 关联输出
- M4-2 已完成：browser-use 规划失败支持重试与可控回退策略（CLI 开关 + 驱动执行策略）
- M4-3 进行中：已落地稳定性回归门禁模式（`--run-stability`，支持连续通过阈值判定）

## 已完成

- 从文章中抽取架构、流程、模块与实施顺序
- 建立项目目录骨架
- 创建 `prd.md`
- 创建 `progress.md`
- 初始化项目基础代码与示例
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
- 新增 Playwright 任务映射策略首版：支持“打开 URL / 点击按钮 / 输入框输入”三类 DSL task 解析
- Playwright 桥接驱动接入 task mapping 元数据输出（supported/action），支持识别未覆盖任务模式
- 新增 Playwright task mapper 与桥接驱动映射单测并通过（当前总计 32 条测试）
- 新增真实 Playwright 断言执行器：支持在 `ExecutionContext.variables["playwright.page"]` 可用时执行 `expect(locator).assertion()`
- Playwright 驱动执行链路接入真实断言执行器；无 runtime page 时回退结构化校验，兼容 dry-run 主链路
- 新增断言执行器单测与 CLI 接入测试并通过（当前总计 37 条测试）
- 新增断言失败截图采集策略：真实 Playwright 断言失败时自动采集 `page.screenshot(full_page=True)` 并注入附件元数据
- 执行引擎新增断言附件聚合：将 assertion artifacts 提升为 step artifacts，随 replay 一并落盘
- Allure 实体落盘链路支持写出失败截图附件（png）与失败上下文（txt）
- 新增断言附件与 Allure 落盘测试并通过（当前总计 38 条测试）
- 将 task mapping 动作计划接入真实 Playwright 浏览器执行链路：支持在驱动内创建/复用 runtime page 并执行 `goto/click/fill`
- Playwright 桥接驱动新增运行态执行结果：`runtime-executed` 与 `runtime-execution-failed`，保留依赖缺失与未支持任务兼容分支
- 新增 Playwright 动作执行成功/失败单测并通过；全量回归通过（`37 passed, 2 skipped`）
- 新增 browser-use 适配层接口草案：`BrowserUseAdapter` 协议、`BrowserUsePlan` 结构与上下文注入键（`browser_use.adapter`）
- Playwright 驱动接入可选 browser-use 规划挂点：支持产出 `browserUse` 规划产物并在规划异常时返回 `browser-use-plan-failed`
- 新增 browser-use 适配层与驱动集成验证测试并通过；全量回归通过（`40 passed, 2 skipped`）
- 新增端到端演示用例 `cases/common/playwright_e2e_demo.yaml`，覆盖 Playwright 动作执行（goto/fill/click）与断言链路
- 新增 CLI 端到端测试：覆盖真实浏览器执行风格、断言失败截图附件、Allure 结果文件落盘闭环
- 修复 replay 序列化问题：`ExecutionContext.variables` 统一转为 JSON-safe，避免 runtime page/browser 对象导致落盘失败
- 新增 replay 序列化回归测试并通过；全量回归通过（`42 passed, 3 skipped`）
- 新增 Playwright runtime 生命周期托管：`ExecutionEngine` 统一在结束阶段触发 driver `close(context)` 清理钩子
- Playwright 驱动补充 runtime 资源释放：按 `page/context/browser/runtime` 顺序释放并聚合清理异常
- 新增生命周期稳定性测试（引擎清理钩子、Playwright 资源释放/异常分支）；全量回归通过（`46 passed, 3 skipped`）
- 新增 browser-use 规划到执行闭环策略：若存在 `BrowserUsePlan` 则优先映射为可执行动作（`goto/click/fill`），否则回退 task mapping
- Playwright 驱动执行结果新增 `execution.source/action` 元数据，区分 `browser-use-plan` 与 `task-mapping`
- 新增 browser-use 规划执行与不支持动作失败分支测试并通过（全量回归通过）
- e2e 样例 `cases/common/playwright_e2e_demo.yaml` 新增可选变量化参数（带默认值），支持按环境覆盖登录 URL/文案/断言文本
- README 增补 e2e 样例变量清单与覆盖示例命令，降低本地演示与联调门槛
- 新增 e2e 变量覆盖回归测试并通过；全量回归通过（`48 passed, 3 skipped`）
- 扩展 Playwright task mapping：新增“下拉框选择 / 等待秒数 / 文本可见断言”三类 DSL 任务模式
- Playwright 驱动新增 `select_option/wait/assert_text_visible` 执行动作，统一纳入 replay 与失败分支
- 新增 task mapper 与驱动动作回归测试并通过（全量回归通过）
- 固化 browser-use 规划动作白名单常量（`goto/click/fill`），并在驱动产物中新增白名单观测字段
- 补充 browser-use 可观测性：`browserUse.whitelist/requestedAction/whitelistDecision` 与 `execution.source` 文档说明
- 新增白名单与可观测性回归断言并通过（相关回归：`27 passed`）
- 新增 browser-use 多动作执行协议：支持通过 `BrowserUsePlan.metadata.actions` 传入动作序列并按顺序执行
- 扩展执行可观测性：新增 `browserUse.plannedActionCount` 与 `execution.actions`，兼容保留 `execution.action` 字段
- 新增多动作协议成功/失败分支测试并通过（相关回归：`30 passed`）
- 新增步骤级可观测性字段：`observability.stepIndex/startedAt/finishedAt/durationMs` 与 `capture` 配置快照
- 新增可选观测开关：CLI `--capture-step-screenshot`（`never/on-failure/always`）与 `--capture-step-log`
- Playwright 驱动新增步骤截图采集策略（按开关写入 replay 附件）；新增 CLI/执行引擎/驱动回归测试并通过（相关回归：`45 passed`）
- 扩展 browser-use 规划动作白名单：支持 `select_option/wait/assert_text_visible`，与现有驱动执行能力对齐
- 新增 browser-use `select_option` 规划动作执行测试，并同步白名单观测字段断言
- 新增真实 browser-use adapter 最小实现：CLI `--enable-browser-use` + 依赖探测（`available/degraded/disabled`）
- 依赖缺失时自动降级到 task mapping，并在上下文注入 `browser_use.status` 诊断信息
- 新增 adapter 单测与 CLI 集成测试（开关注入、降级路径、参数约束）
- 完成 M4 里程碑拆分与验收标准落地：明确 `M4-1 可观测报告`、`M4-2 规划稳定性`、`M4-3 端到端可靠性` 三阶段目标
- 为 M4 增加可量化验收口径：报告字段完整性、失败重试回退行为、稳定性回归基线（通过率与波动阈值）
- 完成 M4-1：Allure 映射新增 `steps[*].executionTrace`，支持聚合展示 `execution.actions` 与步骤附件摘要
- 新增步骤级动作-附件关联输出：`executionTrace.actions[*].attachmentRefs`（按步骤作用域关联）
- 新增报告链路回归测试并通过（`test_allure_mapper/test_allure_report_integration/test_allure_entities/test_cli` 共 21 条）
- 完成 M4-2：新增 CLI 开关 `--browser-use-plan-retry`、`--browser-use-plan-fallback`，支持规划失败重试与回退策略控制
- Playwright 驱动新增规划重试执行与回退到 task mapping 分支，补充可观测字段（`retryConfigured/attempts/fallbackPolicy/fallbackApplied/planErrors`）
- 新增执行引擎与 CLI 回归测试覆盖：重试成功、回退生效、参数注入与参数约束
- M4-3 首项完成：CLI 新增 `--run-stability` 稳定性回归模式，支持 `--stability-runs` 与 `--stability-min-consecutive-pass` 门禁
- 稳定性输出新增汇总口径：`passCount/failCount/passRate/maxConsecutivePass` + `gate.passed`

## 进行中

- 执行 M4-3：端到端可靠性增强与稳定性回归门禁

## 下一步

1. 对接模型驱动规划器的最小桩实现（替换 passthrough 适配层）
2. 增加 planner 失败分类统计与趋势输出（为门禁提供量化指标）
3. 将 `--run-stability` 纳入 CI/夜间任务并固化告警阈值

## 风险

- browser-use 最小 adapter 已接入，但当前为 passthrough 策略，尚未接入模型驱动规划能力
- M4 报告聚合与重试回退策略已落地，但稳定性门禁尚未实现，复杂场景波动风险仍在
- 模型与 browser-use 适配还未开始，后续可能影响接口设计

## 决策记录

- 首期不绑定具体模型供应商，保留可插拔接口
- 先做 CLI 和本地可运行主链路，再做服务化与平台集成
- 先实现 DSL 与执行计划，再接 driver/LLM/replay
