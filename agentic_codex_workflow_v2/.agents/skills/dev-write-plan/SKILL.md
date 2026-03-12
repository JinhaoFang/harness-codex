---
name: dev-write-plan
description: |
  面向 PLAN_DRAFT 阶段的 plan drafting specialist skill。
  Use after ALIGN_PROOF / BOOTSTRAP / ISSUE_SYNC produced enough frozen context and truth anchors,
  when Codex must draft or revise the canonical plan without bypassing PLAN_REVIEW.
---

# Dev Write Plan

从冻结决策与当前 truth anchors 起草 canonical plan，不把 plan 退化成执行流水账。

## Use Bundled Resources
- 先阅读 `references/plan-quality-standard.md`，校准 plan 质量标准。
- 再使用 `assets/plan-template.md` 作为结构基线。

## Drafting Procedure
- 从冻结决策、当前 truth anchors、must-haves、verification ladder 与 recheck plan 开始。
- 把 issue 和 workflow 保持为 plan 的镜像层，而不是复制第二份规格。
- 明确写出契约、边界、不变量、回滚与治理项。

## Escalate
- 在 acceptance、scope、contract 或 truth anchors 还不够冻结时，停止并回到 `ALIGN_PROOF`。
- 不要在 plan review 之后把 reviewer 结论默默合并成既成事实。
