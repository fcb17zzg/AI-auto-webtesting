# AUT 项目任务清单

## 1. 项目目标

构建一个面向内部 Web 管理后台的 AI 前端自动化测试框架 MVP，首期以 CLI 形态交付，打通以下主链路：

- YAML 用例编写
- 变量替换与前置步骤解析
- 用例执行入口
- 回放能力预留
- Playwright/browser-use 执行层预留
- Pytest 调度与 Allure 报告接入预留

## 2. 范围定义

### 2.1 首期纳入

- 用例目录结构与元数据规范
- YAML DSL 解析器
- preSteps 递归展开与循环引用检测
- Jinja2 变量替换
- CLI 执行入口
- 示例用例与基础单元测试
- 项目结构文档与进度管理文档

### 2.2 首期暂缓

- 真实 LLM 接入
- browser-use 深度定制
- Playwright 驱动实现
- 执行回放刷新与智能修复
- super-server 服务化
- backend 平台适配

## 3. 模块拆解

| 模块 | 子项 | 输出物 | 优先级 |
| --- | --- | --- | --- |
| DSL | schema、解析器、变量渲染、preSteps 展开 | 可解析的用例对象 | P0 |
| Runner | CLI 入口、执行计划输出 | 本地执行入口 | P0 |
| Case 管理 | common/product 目录、示例 case | 示例用例 | P0 |
| 文档 | README、PRD、Progress | 文档基线 | P0 |
| Driver | Playwright/browser-use 抽象接口 | 执行接口定义 | P1 |
| Replay | JSON schema、缓存目录 | 回放设计稿 | P1 |
| Assertion | Playwright/assert validator | 断言接口设计 | P1 |
| Scheduler | pytest 集成 | 测试调度 | P1 |
| Report | allure 集成 | 报告输出 | P1 |
| Service | super-server/backend | 服务接口设计 | P2 |

## 4. 里程碑

### M1: 项目起步

- 完成项目骨架
- 完成 `prd.md` 与 `progress.md`
- 完成最小 DSL 解析和 CLI 入口
- 完成至少 1 个 YAML 示例用例和 1 组单测

### M2: 执行抽象

- 增加 driver 抽象层
- 定义执行上下文与步骤结果结构
- 为 LLM 执行与回放执行预留统一接口

### M3: 调度与报告

- 接入 pytest
- 接入 allure
- 沉淀失败上下文与日志格式

### M4: AI 执行闭环

- M4-1 可观测报告增强：将 browser-use 多动作执行计划（`execution.actions`）与步骤附件、失败上下文建立可追踪关联
- M4-2 规划稳定性增强：引入 browser-use 规划失败重试与可控回退策略，降低单次规划波动导致的失败
- M4-3 可靠性验收：建立关键样例连续回归基线，并形成可执行门禁口径

## 5. 当前任务清单

- [x] 梳理文章并转化为实施计划
- [x] 创建 PRD 文档
- [x] 创建 Progress 文档
- [x] 建立项目基础目录结构
- [x] 初始化 README 与 Python 项目配置
- [x] 实现 YAML DSL 最小解析器
- [x] 提供 CLI 入口输出执行计划
- [x] 增加示例用例与单元测试
- [x] 定义 driver 接口与执行上下文
- [x] 接入真实浏览器执行能力（Playwright 首版）
- [x] 接入模型适配层（`model-stub/real-model` 首版）
- [x] 增加回放文件生成与加载
- [x] 增加断言系统
- [x] 接入 pytest/allure 执行报告（首版）

## 6. 验收标准

- M1 验收
  - 可以从命令行解析指定 YAML 用例
  - 可以正确展开 `preSteps`
  - 可以正确进行变量替换
  - 解析结果以结构化步骤顺序输出
- M2 验收
  - 执行上下文、步骤结果、回放文件可稳定落盘
  - driver 抽象可支持 dry-run 与真实驱动并存
- M3 验收
  - `--run` 与 `--run-pytest` 均可产出 replay 与 Allure 映射/实体文件
  - 失败上下文（断言、附件、日志）可在报告链路中追踪
- M4 验收
  - 报告聚合可展示多动作执行计划与步骤附件关联
  - browser-use 规划失败支持重试/回退配置，行为可预测且可观测
  - case 波动 TopN 支持尺寸、最小失败率与最小 plannerFailure 总量阈值配置，能过滤低影响样本
  - 关键样例连续回归至少 10 次，通过率 >= 95%，无阻断级资源泄漏

## 7. 风险与依赖

- 真实页面执行依赖 Playwright 与浏览器环境
- AI 执行依赖模型 API 与提示词策略
- browser-use 的二次定制存在版本兼容风险
- 回放能力落地前，执行成本和稳定性仍不可控
