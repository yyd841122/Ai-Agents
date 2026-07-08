# Route C Final Acceptance

本文档对路线 C（产品与架构文档能力 + 上下文传递 + 文档交付 + 基础设施观测）进行最终验收，为 C-52 基线冻结做准备。

---

## 1. Route C Scope

路线 C 当前覆盖范围：

**核心链路：**
- PRD 生成（Product）
- SDD 生成（Architect）
- TDD 生成（TestDesigner）
- TASKS 生成（TaskManager）
- Planner 接收 TASKS
- Coder 接收执行范围
- Reviewer 接收审查上下文
- Tester 接收测试上下文
- Revise Context（修订上下文）
- Delivery Context（交付上下文）
- Documenter（交付文档）

**基础设施层：**
- Agent Call Wrapper
- Model Router v1
- Cost Record v1
- Fallback Policy v1
- Failure Policy Executor v1
- Failure Capture v1
- Failure Injection Switch
- Failure Injection Matrix

---

## 2. Acceptance Checklist

| Capability | Status | Evidence |
|-----------|--------|----------|
| Product PRD | Accepted | summary.md / run_log.md / final_report.md 中已记录 |
| Architect SDD | Accepted | summary.md / run_log.md / final_report.md 中已记录 |
| TestDesigner TDD | Accepted | summary.md / run_log.md / final_report.md 中已记录 |
| TaskManager TASKS | Accepted | summary.md / run_log.md / final_report.md 中已记录 |
| Planner Context | Accepted | summary.md / run_log.md / final_report.md 中已记录 |
| Coder Task Scope | Accepted | summary.md / run_log.md / final_report.md 中已记录 |
| Reviewer Review Context | Accepted | summary.md / run_log.md / final_report.md 中已记录 |
| Tester Test Context | Accepted | summary.md / run_log.md / final_report.md 中已记录 |
| Revise Context | Accepted | summary.md / run_log.md / final_report.md 中已记录 |
| Delivery Context | Accepted | summary.md / run_log.md / final_report.md 中已记录 |
| Documenter Output | Accepted | final_report.md 中已记录 |
| Agent Call Wrapper | Accepted | summary.md / run_log.md / final_report.md 中已启用 |
| Model Router | Accepted | summary.md / run_log.md / final_report.md 中已启用 |
| Cost Record | Accepted | summary.md / run_log.md / final_report.md 中已记录 |
| Fallback Policy | Accepted | summary.md / run_log.md / final_report.md 中已记录 |
| Failure Policy Executor | Accepted | summary.md / run_log.md / final_report.md 中已启用 |
| Failure Capture | Accepted | summary.md / run_log.md / final_report.md 中已启用 |
| Failure Injection Switch | Accepted | summary.md / run_log.md / final_report.md 中已记录 |
| Failure Injection Matrix | Accepted | docs/FAILURE_INJECTION_MATRIX.md 已建立 |

---

## 3. Known Non-Goals

明确路线 C 不继续做，留给后续路线：

- 不做自动批量失败测试脚本
- 不做真实 token 统计
- 不做真实成本计算
- 不做真实多模型切换
- 不做自动 retry
- 不做自动 revise loop
- 不做 Prompt Builder 独立模块
- 不做 Context Manager 独立模块
- 不做真实文件修改能力

这些留给后续路线或长期基础设施阶段。

---

## 4. Route C Final Conclusion

路线 C 已完成「产品与架构文档能力 + 上下文传递 + 文档交付 + 基础设施观测」的阶段目标：

1. **核心链路完整**：Product → Architect → TestDesigner → TaskManager → Planner → Coder → Reviewer → Tester → Documenter 形成端到端闭环。
2. **上下文传递完整**：Agent 间输入上下文与 Revise / Delivery Context 体系已建立。
3. **基础设施可观测**：Model Router、Cost Record、Fallback Policy、Failure Executor、Failure Capture、Fallback Policy、Failure Injection、Failure Injection Matrix 等 6 层基础设施均已记录并写入报告。
4. **测试矩阵可回归**：9 个 Agent 失败注入已建立 matrix，可人工抽样回归。

**可以进入 C-52：路线 B 进入前基线冻结。**

---

## 5. 验收版本信息

- 文档版本：v1
- 验收范围：路线 C 全部已交付能力
- 下一个里程碑：C-52 路线 B 进入前基线冻结
- 矩阵版本：v1（C-50 FAILURE_INJECTION_MATRIX.md）
- 链路核心 commit 历史：
  - C-41 Documenter：feat: add Documenter delivery agent
  - C-42 Agent Call Wrapper：refactor: centralize agent model calls
  - C-43 Model Router v1：feat: add model router v1
  - C-44 Cost Record v1：feat: enhance model router cost reporting
  - C-45 Fallback Policy v1：feat: record fallback policy v1
  - C-46 Failure Policy Executor v1：feat: add failure policy executor v1
  - C-47 Failure Capture v1：feat: add agent failure capture reporting
  - C-48 Error Path Report Completeness：fix: complete infrastructure reporting on failures
  - C-49 Failure Injection Switch：feat: add controllable failure injection switch
  - C-50 Failure Injection Matrix：docs: add failure injection regression matrix
