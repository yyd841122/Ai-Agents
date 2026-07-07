# AI Agents

这是一个从零手动搭建的多 Agent 协作原型项目。

当前目标不是一次性做复杂系统，而是从最简单、最稳定的固定流程开始，逐步演进成可用于真实开发任务的 Agent 协作系统。

## 当前流程

固定流程：

1. Planner
2. Coder
3. Reviewer
4. Tester

当前不使用复杂 Router，不做动态调度。

## Agent 分工

### Planner

负责理解用户任务，并拆成可执行计划。

### Coder

负责根据 Planner 的计划生成代码。

当前阶段主要生成 HTML 代码块，并由程序提取为 `app.html`。

### Reviewer

负责审查 Coder 输出。

如果 Reviewer 输出“不通过”，Tester 会被跳过。

### Tester

负责设计最小测试方案，并给出测试结论。

当前 Tester 不执行真实浏览器测试，只做测试分析。

## 配置

项目使用 `.env` 保存 MiniMax API 配置。

示例：

```env
MINIMAX_API_KEY=你的 MiniMax API Key
MINIMAX_MODEL=MiniMax-M3
MINIMAX_BASE_URL=https://api.minimax.chat/v1/chat/completions
```

注意：

- `.env` 不要提交到 GitHub
- 不要把 API Key 写进代码
- 如果更换模型，优先修改 `.env`

## 输入任务

任务文件：

```text
tasks/task.txt
```

示例：

```text
请实现一个按钮，点击后输出 hello world。
```

## 运行

在项目根目录运行：

```bash
py run_agents.py
```

如果终端不在项目目录，先进入：

```text
E:/AI_Projects/AI_agents/Agents
```

## 输出目录

每次运行都会生成一个新的运行目录：

```text
outputs/runs/run_001
outputs/runs/run_002
...
```

同时会更新：

```text
outputs/latest
```

`latest` 永远指向最近一次运行结果。

## 输出文件

正常运行时主要文件：

```text
outputs/latest/summary.md
outputs/latest/reports/run_log.md
outputs/latest/reports/final_report.md
outputs/latest/reports/planner_result.md
outputs/latest/reports/coder_result.md
outputs/latest/reports/reviewer_result.md
outputs/latest/reports/tester_result.md
outputs/latest/artifacts/app.html
```

失败运行时主要文件：

```text
outputs/latest/summary.md
outputs/latest/reports/run_log.md
outputs/latest/reports/error_report.md
```

## 快速查看结果

优先查看：

```text
outputs/latest/summary.md
```

它会显示：

```text
Run ID
Workflow Result
app.html 是否生成
Tester 状态
Error
```

## 工作流结果规则

工作流通过条件：

1. Reviewer 通过
2. Tester 完成
3. `app.html` 已生成

否则工作流为未通过。

## 当前可靠性能力

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
- latest 生成 summary.md 快速摘要

## 当前限制

当前仍是固定流程：

```text
Planner → Coder → Reviewer → Tester
```

当前 Coder 主要输出 HTML，不会直接修改真实项目文件。

当前 Tester 只做测试分析，不执行浏览器自动化测试。

后续路线：

- 路线 A：继续增强系统可靠性
- 路线 B：让 Coder 真正写入项目文件，进入真实开发能力