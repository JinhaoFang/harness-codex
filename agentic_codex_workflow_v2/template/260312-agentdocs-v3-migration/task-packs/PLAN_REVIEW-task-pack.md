# Task Pack

## Identity
- Task ID: 260312-agentdocs-v3-migration
- Title: Agentdocs V3 运行模型迁移
- Phase: PLAN_REVIEW
- Current State: PLAN_REVIEW
- Allowed Next State: PLAN_DRAFT | BUILD | EXCEPTION_RECOVERY
- Owner: plan_reviewer

## Understanding Proof
- Goal Restatement: 执行最终 round-3 PLAN_REVIEW：destination matrix 与 hard routing rule 已放行，本轮只核对 plan/workflow/task-pack 的 phase truth 是否完全一致，并确认可进入 BUILD。
- Explicit Non-Goals:
  - Do not reopen destination routing unless the current files changed it again.
  - Do not require historical archive normalization.
  - Do not allow architecture canonical rewrites inside this task.
- 95% Understanding Check: YES
- Missing Pieces:
  - <none>

## Source Pointers
- Spec Source:
  - .agentdocs/archive/260312-agentdocs-v3-migration/plan.md §6.3-§6.5
  - .agentdocs/archive/260312-agentdocs-v3-migration/plan.md §12.P4
- Review Inputs:
  - .agentdocs/archive/260312-agentdocs-v3-migration/reviews/plan-review-r2.json

## Frozen Context
- Frozen Decisions:
  - The destination matrix and hard routing rule are closed enough for BUILD unless phase truth drifts again.
  - Historical archive legality is not a blocker for this task.
  - This task may point to existing architecture SoT but must not rewrite architecture canonical docs.
  - Items without a clear existing architecture home must land in source-linked temporary insights entries.
- Known Non-Reopen Decisions:
  - Do not expand this task into full historical archive normalization.
- Open Risks / Escalations:
  - If phase truth still drifts, the active review gate loses SSOT integrity.
- Previous Findings:
  - PLAN_REVIEW r1 required a closed destination matrix and hard routing rule.
  - PLAN_REVIEW r2 accepted the routing scope but rejected stale phase markers.

## Read Boundary
- Must Read:
  - AGENTS.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/plan.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/PLAN_REVIEW-task-pack.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/scratch/index-destination-matrix.md
  - .agentdocs/index.md
  - .agentdocs/insights.md
  - docs/dev/contracts/session-minimum-align.md
  - docs/dev/contracts/task-pack-layout.md
  - docs/dev/contracts/task-archive-lifecycle.md
  - docs/dev/contracts/structured-writeback.md
- Verified Adjacent Context:
  - .agentdocs/archive/260308-agentdocs-v2-migration/workflow.md
  - .agentdocs/archive/260308-backend-architecture-reorg/workflow.md
  - .agentdocs/architecture/*.md
- Unread But Potentially Relevant:
  - docs/dev/system/module-boundaries.md
- Coverage Decision: SUFFICIENT

## Current Truth Anchors
- Code Paths:
  - .agentdocs/index.md
  - .agentdocs/insights.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/plan.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/PLAN_REVIEW-task-pack.md
- Key Symbols / Entry Points:
  - taskctl.py::cmd_make_pack
  - taskctl.py::cmd_validate_pack
  - taskctl.py::cmd_advance_state
- Tests / Checks:
  - python .codex/workflow/taskctl.py validate-pack --pack .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/PLAN_REVIEW-task-pack.md => PASS
  - workflow current state == PLAN_REVIEW
  - plan/workflow phase notes no longer mention readiness for PLAN_DRAFT
- Config / Runtime:
  - .agentdocs/archive/260312-agentdocs-v3-migration/ is the only active V3 task root
  - .agentdocs/index.md still points to the deleted 260309 task and is the intended BUILD target, not a hidden phase-truth conflict

## Action Boundary
- Write Boundary:
  - .agentdocs/archive/260312-agentdocs-v3-migration/reviews/
  - .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/
- Forbidden Writes:
  - .agentdocs/index.md
  - .agentdocs/insights.md
  - .agentdocs/archive/index.md
  - .agentdocs/archive/**
  - .agentdocs/architecture/**
  - business code
- Review Mode: FULL_REVIEW
- Escalation Rule: If phase truth still drifts between plan, workflow, and task pack, return NEEDS_CHANGES and send the task back to PLAN_DRAFT; otherwise decide whether BUILD is allowed.

## Invariants
  - Every useful section from the old index must have an explicit destination or reason to remain.
  - The hot path index must point only to real active tasks.
  - BUILD must not rewrite architecture canonical docs.

## Verification
- Must-Haves:
  - Plan, workflow, and task pack must now describe the same PLAN_REVIEW truth.
  - The destination matrix and hard routing rule must remain unchanged from the approved round-2 scope.
  - BUILD must stay bounded to hot-path docs plus task-scoped artifacts.
- Verification Obligations:
  - Review whether phase truth is now aligned across plan, workflow, and task pack.
  - Review whether the routing scope remains bounded and unchanged.
  - Review whether BUILD is now legally reachable without reopening archive or architecture scope.
- Reviewer Recheck Plan:
  - .agentdocs/archive/260312-agentdocs-v3-migration/plan.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/PLAN_REVIEW-task-pack.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/scratch/index-destination-matrix.md
- UAT:
  - Once BUILD starts, a new session should be able to recover from a real active task without ambiguity.
