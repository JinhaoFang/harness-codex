---
name: dev-workflow-router
description: |
  开发任务总入口路由器，用于判断 entropy、状态机位置、review mode、下一合法动作与是否进入 multi-agent。
  Use for new tasks, resumed tasks, reroutes after findings, implementation requests, reviews, refactors, bug fixes,
  documentation work, or issue sync in this workflow system before selecting a specialist skill or worker.
---

# Dev Workflow Router

先决定任务走 low-entropy 还是 high-entropy，再决定当前 state、角色与下一合法动作。

## Use Bundled Resources
- 先阅读 `references/entropy-classification-rules.md` 做 entropy 判断。
- 在 high-entropy 场景下阅读 `references/high-entropy-loop.md`。
- 在 low-entropy 场景下阅读 `references/low-entropy-fast-path.md`。
- 在需要 sub-agent 协议时阅读 `references/new-session-and-subagent-guidelines.md`。
- 在需要 gate / evidence 约束时阅读 `references/verification-gates-and-evidence.md`。

## Boundary
- 只做 route / state / delegation 决定。
- 把实现、review 本体与结构化写回留给 specialist skills 与 controller。

## Escalate
- 在 goal / scope / acceptance / contract 变化时，回退到 `PLAN_DRAFT`。
- 在 low-entropy 假设失效时，升级到 high-entropy。
