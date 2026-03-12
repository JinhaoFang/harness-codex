---
name: dev-review-router
description: |
  review gate 路由器，用于让 main agent 在当前状态下选择正确的 reviewer 角色、specialist skill 与 review mode。
  Use when a task is about to enter PLAN_REVIEW or CLOSE_REVIEW, or when Codex must reroute after review findings,
  while keeping the main agent out of the full reviewer checklists.
---

# Dev Review Router

用 review gate 的最小事实集合决定 reviewer、specialist skill、review mode 与下一合法动作。

## Procedure
- 读取当前 task pack、workflow state 与上一轮 findings。
- 判断应派发 `plan_reviewer` 还是 `close_reviewer`。
- 判断应使用 `FULL_REVIEW`、`DELTA_REVIEW` 还是 `FORMAT_ONLY`。
- 在需要固定 handoff 时，通过 controller 生成 delegation brief。

## Boundary
- 只做路由，不执行 review 本体，不修改实现，不直接归档。
- 让 main agent 停留在 route / state / delegation 层。

## Escalate
- 在 pack 缺失、pack 过期、gate 不满足或 review 与当前状态冲突时，停止并回退。
- 不要在缺少前置条件时盲目委派 reviewer。
