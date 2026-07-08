# Failure Injection Matrix

本文档用于人工验证 `FAIL_AGENT` 环境变量对不同 Agent 的失败注入行为。

通过本矩阵，可以确认：

- 每个 Agent 失败时，异常路径报告是否完整
- Failure Capture 是否正确记录失败 Agent
- 基础设施状态是否保持"已启用/已记录"
- 验证完成后系统是否能恢复

---

## 1. PowerShell 命令模板

每次验证前设置环境变量，验证后必须清理：

```powershell
$env:FAIL_AGENT="<AgentName>"
python run_agents.py
Remove-Item Env:FAIL_AGENT
```

或者使用一行命令：

```powershell
$env:FAIL_AGENT="<AgentName>"; python run_agents.py; Remove-Item Env:FAIL_AGENT
```

> 注意：每次测试后必须执行 `Remove-Item Env:FAIL_AGENT` 清理环境变量，避免污染后续运行。

---

## 2. 验收检查清单

每次失败注入验证后，必须逐项确认：

- [ ] `summary.md` 包含 `失败注入：已启用：<Agent>`
- [ ] `summary.md` 包含 `失败捕获：已启用`
- [ ] `summary.md` 包含 6 个基础设施状态（Agent 调用统一入口、Model Router、成本记录、失败降级策略、失败策略执行层、失败捕获）
- [ ] `summary.md` 包含 `失败注入矩阵：已建立`
- [ ] `final_report.md` 包含 `## Failure Injection` 章节
- [ ] `final_report.md` 包含 `## Failure Capture` 章节
- [ ] `final_report.md` 包含 `## Failure Injection Matrix` 章节
- [ ] Failure Capture 表格包含对应 Agent
- [ ] Error Type 为 `RuntimeError`
- [ ] Error Message 为 `Injected failure for agent: <Agent>`
- [ ] 清理 `FAIL_AGENT` 后正常路径恢复，`失败注入：未启用`，`Documenter：完成`

---

## 3. 失败注入矩阵

下表列出 9 个 Agent 失败时的预期表现。

| Agent | Command | Expected Failed Stage | Expected Skipped Stages | Expected Failure Capture | Expected Infrastructure Status |
|-------|---------|----------------------|------------------------|-------------------------|-------------------------------|
| Product | `FAIL_AGENT=Product` | Product 失败 | Architect / TestDesigner / TaskManager / Planner / Coder / Reviewer / Tester / Documenter | Product / RuntimeError / Injected failure for agent: Product | 6 项完整 |
| Architect | `FAIL_AGENT=Architect` | Architect 失败 | TestDesigner / TaskManager / Planner / Coder / Reviewer / Tester / Documenter | Architect / RuntimeError / Injected failure for agent: Architect | 6 项完整 |
| TestDesigner | `FAIL_AGENT=TestDesigner` | TestDesigner 失败 | TaskManager / Planner / Coder / Reviewer / Tester / Documenter | TestDesigner / RuntimeError / Injected failure for agent: TestDesigner | 6 项完整 |
| TaskManager | `FAIL_AGENT=TaskManager` | TaskManager 失败 | Planner / Coder / Reviewer / Tester / Documenter | TaskManager / RuntimeError / Injected failure for agent: TaskManager | 6 项完整 |
| Planner | `FAIL_AGENT=Planner` | Planner 失败 | Coder / Reviewer / Tester / Documenter | Planner / RuntimeError / Injected failure for agent: Planner | 6 项完整 |
| Coder | `FAIL_AGENT=Coder` | Coder 失败 | Reviewer / Tester / Documenter | Coder / RuntimeError / Injected failure for agent: Coder | 6 项完整 |
| Reviewer | `FAIL_AGENT=Reviewer` | Reviewer 失败 | Tester / Documenter | Reviewer / RuntimeError / Injected failure for agent: Reviewer | 6 项完整 |
| Tester | `FAIL_AGENT=Tester` | Tester 失败 | Documenter | Tester / RuntimeError / Injected failure for agent: Tester | 6 项完整 |
| Documenter | `FAIL_AGENT=Documenter` | Documenter 失败 | (无) | Documenter / RuntimeError / Injected failure for agent: Documenter | 6 项完整 |

---

## 4. 各 Agent 失败详细预期

### 4.1 Product 失败

- **已完成**：（无）
- **失败**：Product
- **跳过**：Architect / TestDesigner / TaskManager / Planner / Coder / Reviewer / Tester / Documenter
- **Failure Capture**：Product | RuntimeError | Injected failure for agent: Product
- **基础设施状态**：全部 6 项完整

### 4.2 Architect 失败

- **已完成**：Product
- **失败**：Architect
- **跳过**：TestDesigner / TaskManager / Planner / Coder / Reviewer / Tester / Documenter
- **Failure Capture**：Architect | RuntimeError | Injected failure for agent: Architect

### 4.3 TestDesigner 失败

- **已完成**：Product / Architect
- **失败**：TestDesigner
- **跳过**：TaskManager / Planner / Coder / Reviewer / Tester / Documenter
- **Failure Capture**：TestDesigner | RuntimeError | Injected failure for agent: TestDesigner

### 4.4 TaskManager 失败

- **已完成**：Product / Architect / TestDesigner
- **失败**：TaskManager
- **跳过**：Planner / Coder / Reviewer / Tester / Documenter
- **Failure Capture**：TaskManager | RuntimeError | Injected failure for agent: TaskManager

### 4.5 Planner 失败

- **已完成**：Product / Architect / TestDesigner / TaskManager
- **失败**：Planner
- **跳过**：Coder / Reviewer / Tester / Documenter
- **Failure Capture**：Planner | RuntimeError | Injected failure for agent: Planner

### 4.6 Coder 失败

- **已完成**：Product / Architect / TestDesigner / TaskManager / Planner
- **失败**：Coder
- **跳过**：Reviewer / Tester / Documenter
- **Failure Capture**：Coder | RuntimeError | Injected failure for agent: Coder

### 4.7 Reviewer 失败

- **已完成**：Product / Architect / TestDesigner / TaskManager / Planner / Coder
- **失败**：Reviewer
- **跳过**：Tester / Documenter
- **Failure Capture**：Reviewer | RuntimeError | Injected failure for agent: Reviewer

### 4.8 Tester 失败

- **已完成**：Product / Architect / TestDesigner / TaskManager / Planner / Coder / Reviewer
- **失败**：Tester
- **跳过**：Documenter
- **Failure Capture**：Tester | RuntimeError | Injected failure for agent: Tester

### 4.9 Documenter 失败

- **已完成**：Product / Architect / TestDesigner / TaskManager / Planner / Coder / Reviewer / Tester
- **失败**：Documenter
- **跳过**：（无）
- **Failure Capture**：Documenter | RuntimeError | Injected failure for agent: Documenter

---

## 5. 抽样验证推荐

完整 9 Agent 验证耗时长且消耗 token。日常回归可仅抽样 2 个：

1. **Product**（最早阶段，验证 8 个 Agent 跳过）
2. **Reviewer**（中后阶段，验证部分 Agent 完成后失败）

抽样命令：

```powershell
$env:FAIL_AGENT="Product"; python run_agents.py; Remove-Item Env:FAIL_AGENT
$env:FAIL_AGENT="Reviewer"; python run_agents.py; Remove-Item Env:FAIL_AGENT
```

---

## 6. 变更后回归触发时机

建议在以下场景下执行矩阵验证：

- 修改 `run_agents.py` 中异常处理逻辑
- 修改 `build_final_report()` / `build_run_log()` / `build_summary()` 签名
- 修改 `execute_agent_with_policy()` 中失败捕获逻辑
- 修改任何 `failure_*_status` 写入路径

---

## 7. 默认行为

- 未设置 `FAIL_AGENT` 时，失败注入开关**默认关闭**
- `python run_agents.py` 应与 C-49 正常路径行为一致
- summary.md 中 `失败注入：未启用`
- Documenter：完成
- Failure Capture 章节显示 "无 Agent 调用失败。"

---

## 8. 矩阵版本

- 版本：v1
- 创建：基于 C-49 可控失败注入测试开关
- 维护原则：每次异常路径相关代码修改后必须回归本矩阵
