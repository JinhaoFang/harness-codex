---
name: dev-review-plan
description: |
  面向 `plan_reviewer` 的 PLAN_REVIEW specialist skill。
  Use when a PLAN_REVIEW task pack already exists and an independent reviewer must decide
  whether the plan is executable, complete, aligned with frozen decisions, and supported by current truth anchors.
---

# Dev Review Plan

先读取当前 PLAN_REVIEW task pack，再执行独立计划评审。

## Use Bundled Resources
- 先阅读 `references/plan-review-checklist.md`，再按需展开 `assets/plan-review-checklist.md`。
- 在多轮 review 无法收敛到单一技术结论时，使用 `assets/human-decision-template.md` 收敛人工拍板项。
- 仅在遗留手工回填兼容场景下使用 `scripts/apply_plan_review_record.py`；默认仍优先 controller。
- 按需读取代码、架构、接口、测试与当前 truth anchors，判断方案在项目现实里是否可执行，而不是只检查文档格式。

## Write Boundary
- 只写 review bundle 与 controller sidecar。
- 不要重写 canonical plan、产出替代性完整方案、修改业务代码或推进状态机。

## Escalate
- 在 truth anchors 不足、task pack 过期或 review mode 不一致时，返回 `NEEDS_CHANGES`。
- 在局部改动已经影响全局约束时，升级到 `FULL_REVIEW`。
- 在你开始像 main agent 那样重新分解任务、重新路由或替作者设计完整替代方案时，停止并改回最小 blocking delta。
