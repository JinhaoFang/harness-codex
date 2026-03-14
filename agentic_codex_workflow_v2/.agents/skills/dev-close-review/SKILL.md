---
name: dev-close-review
description: |
  面向 `close_reviewer` 的 CLOSE_REVIEW specialist skill。
  Use when a CLOSE_REVIEW task pack already exists and an independent reviewer must verify
  plan alignment, evidence traceability, sampled truth anchors, and archive readiness before closure.
---

# Dev Close Review

先读取当前 CLOSE_REVIEW task pack，再执行独立收尾评审。

## Review Procedure

- 阅读 `references/close-review-checklist.md`，再据此抽样 plan 对齐、evidence traceability、truth anchors 与 archive readiness。
- 按需回到代码、架构、测试、日志与 evidence，判断实现是否按 approved plan 落地且没有语义漂移。
- 返回固定 close-review 输出字段，而不是自由发挥总结。
- 让 main agent 只消费结论，不展开完整 checklist。

## Write Boundary

- 只写 task-scoped review 产物与 controller sidecar。
- 不要修改实现代码、plan 正文、archive 状态或产出替代性完整修复方案。

## Escalate

- 在 evidence 不可追踪、task pack 过期、存在 build-before-review 或修复需要改实现时，返回 `NEEDS_FIX` 或 `BLOCKED`。
- 不要把 close review 退化成主 agent 的手工检查。
- 如果你开始替 main agent 重新路由、重写实现策略或安排后续任务，说明身份已漂移，应立刻收回到 blocking delta。
