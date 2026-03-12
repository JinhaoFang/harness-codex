# Task Pack

## Identity
- Task ID: 260312-agentdocs-v3-migration
- Title: Agentdocs V3 运行模型迁移
- Phase: BUILD
- Current State: BUILD
- Allowed Next State: CLOSE_REVIEW | PLAN_DRAFT | EXCEPTION_RECOVERY
- Owner: worker

## Understanding Proof
- Goal Restatement: Execute the frozen hot-path migration: rewrite .agentdocs/index.md into a valid V3 SSOT entry, add .agentdocs/archive/index.md, migrate selected old-index long-term memory into .agentdocs/insights.md, and preserve explicit legacy navigation/compatibility boundaries.
- Explicit Non-Goals:
  - Do not normalize historical archive bundles to V3.
  - Do not rewrite architecture/*.md canonical documents.
  - Do not modify business code.
- 95% Understanding Check: YES
- Missing Pieces:
  - <none>

## Source Pointers
- Spec Source:
  - .agentdocs/archive/260312-agentdocs-v3-migration/plan.md §6.3-§6.5
  - .agentdocs/archive/260312-agentdocs-v3-migration/plan.md §12.P2-§12.P3
- Review Inputs:
  - .agentdocs/archive/260312-agentdocs-v3-migration/reviews/plan-review-r3.json

## Frozen Context
- Frozen Decisions:
  - Old index content must be migrated or explicitly retained with a destination; it cannot be silently dropped.
  - Historical archive remains read-only compatible and is not backfilled to strict V3 in this task.
  - Items with an existing architecture SoT are referenced, not copied into new canonical prose.
- Known Non-Reopen Decisions:
  - Do not reopen the destination matrix or hard routing rule during BUILD.
- Open Risks / Escalations:
  - Over-compressing the index could lose long-term memory or legacy navigation.
  - Misclassifying old memory into insights instead of architecture could create dual sources of truth.
- Previous Findings:
  - PLAN_REVIEW r1 required a closed destination matrix and hard routing rule.
  - PLAN_REVIEW r2 accepted routing scope and only rejected stale phase markers.
  - PLAN_REVIEW r3 passed and allowed BUILD.

## Read Boundary
- Must Read:
  - AGENTS.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/plan.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/scratch/index-destination-matrix.md
  - .agentdocs/index.md
  - .agentdocs/insights.md
  - docs/dev/contracts/session-minimum-align.md
  - docs/dev/contracts/task-pack-layout.md
  - docs/dev/contracts/task-archive-lifecycle.md
- Verified Adjacent Context:
  - .agentdocs/archive/260308-agentdocs-v2-migration/workflow.md
  - .agentdocs/archive/260308-backend-architecture-reorg/workflow.md
  - .agentdocs/architecture/backend_system_overview.md
  - .agentdocs/architecture/backend_data_and_sync.md
  - .agentdocs/architecture/agent_runtime_overview.md
  - .agentdocs/architecture/agent_runtime_orchestration.md
  - .agentdocs/architecture/agent_observability_and_eventing.md
  - .agentdocs/architecture/media_storage_and_files.md
- Unread But Potentially Relevant:
  - docs/dev/system/module-boundaries.md
- Coverage Decision: SUFFICIENT

## Current Truth Anchors
- Code Paths:
  - .agentdocs/index.md
  - .agentdocs/insights.md
  - .agentdocs/archive/index.md
  - .codex/workflow/taskctl.py
- Key Symbols / Entry Points:
  - taskctl.py::cmd_make_pack
  - taskctl.py::cmd_validate_pack
  - taskctl.py::cmd_sync_index
- Tests / Checks:
  - test -f .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md
  - rg -n "DEFAULT:|ACTIVE:|## 2\) 当前任务（SSOT\)|260309-taskctl-controller-hardening" .agentdocs/index.md
  - python .codex/workflow/taskctl.py validate-pack --pack .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/BUILD-task-pack.md
  - find .agentdocs/archive -maxdepth 2 -type f | sort
  - git diff -- .agentdocs
- Config / Runtime:
  - .agentdocs/archive/260312-agentdocs-v3-migration/ is the only active V3 task root.
  - Historical archive legality is intentionally out of scope for this BUILD.

## Action Boundary
- Write Boundary:
  - .agentdocs/index.md
  - .agentdocs/insights.md
  - .agentdocs/archive/index.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/BUILD-task-pack.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/evidence
- Forbidden Writes:
  - .agentdocs/archive/260308-agentdocs-v2-migration
  - .agentdocs/archive/260308-backend-architecture-reorg
  - .agentdocs/architecture
  - business-code
- Build Scope: APPROVED_SCOPE
- Escalation Rule: If any old index item now requires architecture canonical rewrites or historical archive normalization to land cleanly, stop BUILD and return to PLAN_DRAFT or PLAN_REVIEW instead of expanding scope ad hoc.

## Invariants
  - Every useful old-index section must have an explicit destination or reason to remain.
  - .agentdocs/index.md must point only to a real active task.
  - BUILD must not rewrite architecture canonical docs or normalize historical archive bundles.

## Verification
- Must-Haves:
  - Rewrite .agentdocs/index.md into a valid V3 hot-path entry without losing useful legacy navigation.
  - Create .agentdocs/archive/index.md.
  - Migrate selected long-term memory from old index into .agentdocs/insights.md with source-linked grouping.
- Verification Obligations:
  - Confirm .agentdocs/index.md points to the real active task and no longer references the deleted 260309 task.
  - Confirm .agentdocs/archive/index.md exists and provides stable archive navigation.
  - Confirm sampled old-index memory items now land in index, insights, or explicit architecture references per the frozen matrix.
  - Run validate-pack for BUILD-task-pack and inspect git diff limited to .agentdocs.
- Reviewer Recheck Plan:
  - .agentdocs/index.md
  - .agentdocs/insights.md
  - .agentdocs/archive/index.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md
- UAT:
  - A new session can start from .agentdocs/index.md, find the current active task, then navigate to insights and archive index without ambiguity.
