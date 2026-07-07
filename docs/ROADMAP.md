# Roadmap

本项目目标是从一个最小多 Agent Demo，逐步演进成可用于真实开发任务的 Agent 协作系统。

当前坚持一个原则：

先稳定，再扩展。

## 当前固定流程

当前已实现的最小流程：

```text
Planner → Coder → Reviewer → Tester
```

当前不使用复杂 Router，不做动态调度。

## 路线 A：系统可靠性

目标：

让多 Agent 工作流稳定、可追踪、失败可诊断。

已完成：

- Reviewer 不通过时跳过 Tester
- `run_log.md` 记录 Tester 完成 / 跳过
- `final_report.md` 记录 Workflow Result
- `app.html` 未生成时标记未通过
- MiniMax API 调用失败时保存 `error_report.md`
- API 失败时也生成 `run_log.md`
- 失败时记录失败阶段
- 失败 run_log 显示各 Agent 状态
- run_log 显示 Workflow Result
- latest 生成 `summary.md` 快速摘要
- README.md 最小使用说明
- `.gitignore` 排除 `.env`、缓存和 outputs

后续可继续增强：

- 失败时支持重试策略
- 失败时区分网络错误、认证错误、模型输出错误
- 增加更严格的输出格式校验
- 增加运行成本与耗时统计
- 增加任务历史索引
- 增加 Agent 质量评分记录

## 路线 C：产品与架构文档能力

目标：

在进入真实开发前，先让系统具备产品、架构、测试设计能力。

原因：

真实项目不能直接让 Coder 改代码。复杂项目需要先明确：

- PRD：产品需求
- SDD：系统设计
- TDD：测试设计
- 技术栈
- 前端 / 后端 / App 边界
- Android / iOS / Web 范围
- MVP 范围
- 不做什么

计划新增 Agent：

```text
Product Agent
Architect Agent
TestDesigner Agent
```

未来流程可能演进为：

```text
Product → Architect → TestDesigner → Planner → Coder → Reviewer → Tester
```

各 Agent 目标：

| Agent | 作用 | 输出 |
|---|---|---|
| Product | 梳理需求、边界、MVP、用户场景 | PRD.md |
| Architect | 设计技术方案、模块边界、目录结构、数据流 | SDD.md |
| TestDesigner | 设计验收标准、测试策略、边界用例 | TDD.md |

路线 C 的重点不是生成漂亮文档，而是让后续开发不跑偏。

## 路线 B：真实开发能力

目标：

让 Coder 不再只输出 `app.html`，而是能真正参与项目开发。

未来能力：

- 读取项目文件
- 理解项目结构
- 修改真实代码文件
- 生成 patch 或直接写入文件
- 运行测试命令
- 保存变更报告
- Reviewer 审查真实 diff
- Tester 基于真实项目输出测试结论

未来输出可能包括：

```text
artifacts/patch.diff
reports/change_report.md
reports/test_result.md
```

路线 B 必须建立在路线 A 的可靠性和路线 C 的文档边界之上。

## 推荐执行顺序

当前推荐顺序：

```text
A：系统可靠性
C：产品与架构文档能力
B：真实开发能力
```

原因：

1. 没有 A，系统容易悄悄失败。
2. 没有 C，真实开发容易跑偏。
3. B 是最终能力，但不能过早开始。

## 当前阶段

当前正在完成：

```text
路线 A：系统可靠性收口
```

下一阶段建议：

```text
路线 C：产品与架构文档能力最小版
```

优先新增：

```text
Product Agent
```

先让系统能从用户一句话生成最小 PRD，再逐步加入 Architect 和 TestDesigner。

## 暂不做

当前阶段暂不做：

- 复杂 Router
- 动态 Agent 市场
- 自动多轮对话
- 自动连接真实大型项目
- 自动提交 Git
- 自动部署
- 多模型混合调度
- 复杂 UI