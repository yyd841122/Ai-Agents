# Route B Minimal Loop Acceptance

本文档对路线 B 第一阶段（B-01 到 B-06）已实现能力做最小真实开发闭环验收。

---

## 1. Scope

B-07 验收范围：

- PROJECT_ID
- PROJECT_ROOT
- 工作区识别
- 真实任务协议
- Coder 输出 HTML
- 受控写入 PROJECT_ROOT/app.html
- 变更记录
- 项目隔离输出
- project_state.json
- 恢复入口状态

最小闭环链路：

Task → PROJECT_ID / PROJECT_ROOT → 工作区识别 → 真实任务协议 → Coder 输出 → 受控写入 app.html → 变更记录 → 项目隔离输出 → project_state 保存

---

## 2. Acceptance Checklist

| Capability | Status | Evidence |
|-----------|--------|----------|
| Workspace Detection | Accepted | summary.md / run_log.md / final_report.md 中已记录 |
| Real Task Protocol | Accepted | summary.md / run_log.md / final_report.md 中已记录 |
| Controlled app.html Write | Accepted | outputs/projects/{PROJECT_ID}/app.html / final_report.md 中已记录 |
| Change Record | Accepted | summary.md / final_report.md 中已记录 |
| Project Registry | Accepted | projects/registry.json 已建立 |
| Project Session Isolation | Accepted | outputs/projects/{PROJECT_ID}/runs / latest 已建立 |
| Project State Save | Accepted | outputs/projects/{PROJECT_ID}/project_state.json 已建立 |
| Resume Entry | Accepted | summary.md / final_report.md 中已记录 |
| Global Latest | Accepted | outputs/latest 已建立 |
| Project Latest | Accepted | outputs/projects/{PROJECT_ID}/latest 已建立 |

---

## 3. Non-Goals

明确 B-07 不做：

- 不做 Reviewer 真实 diff 审查
- 不做 Tester 命令执行
- 不做 Git 操作
- 不做自动恢复
- 不做自动 revise
- 不做多文件修改
- 不做通用 patch

这些留给后续路线 B 阶段（B-08 及以后）。

---

## 4. Conclusion

B-07 完成后，路线 B 第一阶段最小真实开发闭环已成立。

平台已具备：

- 识别真实项目工作区
- 建立真实任务协议
- 受控写入单个 app.html
- 记录变更与简化 diff
- 多项目注册与会话隔离
- 项目状态保存与恢复入口

下一步进入：

**B-08：Reviewer 读取真实 diff 审查**

---

## 5. 验收版本信息

- 文档版本：v1
- 验收范围：B-01 到 B-06 已实现能力
- 下一个里程碑：B-08 Reviewer 读取真实 diff 审查
- 最小闭环判定条件：
  - workspace 已识别
  - 真实任务协议已建立
  - app.html 修改（已修改）或明确跳过（不存在但已记录原因）
  - 变更记录已生成
  - 项目会话已启用
  - project_state.json 已写入
