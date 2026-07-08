# Route B Entry Baseline

本文档用于冻结路线 C 当前成果，明确进入路线 B 的边界、基线、禁止继续扩展路线 C 的内容，以及路线 B 第一阶段目标。

---

## 1. Baseline Commit

- **Route C acceptance commit:** d846b51
- **Current baseline commit:** d846b51

该 commit 是路线 C 最终验收完成后的基线。路线 B 从此 commit 之上开始构建。

---

## 2. Route C Frozen Capabilities

路线 C 已冻结能力（不再扩展）：

**核心链路：**
- Product PRD
- Architect SDD
- TestDesigner TDD
- TaskManager TASKS
- Planner Context
- Coder Task Scope
- Reviewer Review Context
- Tester Test Context
- Revise Context
- Delivery Context
- Documenter Output

**基础设施层：**
- Agent Call Wrapper
- Model Router
- Cost Record
- Fallback Policy
- Failure Policy Executor
- Failure Capture
- Failure Injection Switch
- Failure Injection Matrix

**验收文档：**
- Route C Final Acceptance

---

## 3. Route C Stop Boundary

明确以下内容不在当前继续做：

- 不继续做自动失败矩阵脚本
- 不做真实 token 统计
- 不做真实成本计算
- 不做真实多模型切换
- 不做自动 retry
- 不做自动 revise loop
- 不拆 Prompt Builder 独立模块
- 不拆 Context Manager 独立模块
- 不继续增加路线 C 报告字段，除非路线 B 必需

---

## 4. Route B Goal

路线 B 目标：

让平台从「生成文档和报告」升级为「具备真实开发能力」。

必须明确路线 B 最终要实现：

- 识别真实项目工作区
- 读取真实项目文件
- 修改真实项目文件
- 输出 changed files
- 输出 diff summary
- Reviewer 基于真实 diff 审查
- Tester 执行真实验证命令
- 记录命令结果
- 失败后生成 revise context
- 最多一次 Coder 修复
- 最终 Documenter 输出真实交付报告

---

## 5. Route B First Milestone

路线 B 第一阶段验收点：

**B-05：真实开发最小闭环**

**B-05 目标：**

Task → 识别项目工作区 → Coder 修改真实文件 → 记录 changed files → 生成报告

**注意：**

B-05 只要求真实修改文件，不要求完整 Reviewer diff 审查和 Tester 命令执行。

完整项目测试目标放在：

**B-10：真实开发完整闭环**

---

## 6. Route B Planned Steps

列出路线 B 初步步骤：

- **B-01**：真实项目工作区识别
- **B-02**：真实任务输入协议
- **B-03**：Coder 真实文件修改能力
- **B-04**：变更记录与 diff 输出
- **B-05**：真实开发最小闭环验收
- **B-06**：Reviewer 读取真实 diff 审查
- **B-07**：Reviewer 审查结果结构化
- **B-08**：Tester 真实命令执行能力
- **B-09**：测试结果记录
- **B-10**：真实审查 + 测试闭环验收
- **B-11**：失败后 Revise 输入生成
- **B-12**：Coder 二次修复能力
- **B-13**：修复后重新审查与测试
- **B-14**：Git 安全边界
- **B-15**：路线 B 最终验收与基线冻结

---

## 7. Route B Entry Conclusion

**路线 C 已冻结。**

下一步可以进入：

**B-01：真实项目工作区识别**

---

## 8. 路线 B 入口禁止清单

为避免路线 C 继续蔓延，路线 B 第一阶段（B-01 ~ B-05）禁止：

- 重构路线 C 已冻结的报告生成函数（除非因 B 必需且有明确 commit reason）
- 删除路线 C 已有基础设施层状态
- 修改路线 C 已固化的 Agent 输入/输出字段
- 重新设计路线 C 的失败注入语义

路线 B 仅在必要时对路线 C 进行增量扩展，并在 commit 中明确标注 reason。