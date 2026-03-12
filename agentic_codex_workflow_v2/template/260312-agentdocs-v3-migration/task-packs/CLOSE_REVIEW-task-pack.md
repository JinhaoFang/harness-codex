# Task Pack

## Identity
- Task ID: 260312-agentdocs-v3-migration
- Title: Agentdocs V3 运行模型迁移
- Phase: CLOSE_REVIEW
- Current State: CLOSE_REVIEW
- Allowed Next State: BUILD | ARCHIVE | EXCEPTION_RECOVERY
- Owner: close_reviewer

## Understanding Proof
- Goal Restatement: 对 BUILD 结果执行独立 close review：确认 index/archive/insights 的迁移结果、task-scoped bookkeeping 与 evidence 已闭合，并判断是否允许结束本任务。
- Explicit Non-Goals:
  - Do not reopen historical archive normalization.
  - Do not rewrite architecture canonical documents.
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
  - Old index content had to be migrated or explicitly retained; it could not be silently dropped.
  - Historical archive remains read-only compatible and is not normalized in this task.
  - Architecture facts are referenced via existing canonical docs rather than copied into new prose.
- Known Non-Reopen Decisions:
  - Do not reopen the destination matrix or hard routing rule unless the current BUILD output violates them.
- Open Risks / Escalations:
  - If index navigation still bakes in the current task outside the SSOT section, a future archive or task switch will recreate stale links.
  - If sampled old-index items cannot be found in index/insights/architecture references, information loss may have occurred.
- Previous Findings:
  - PLAN_REVIEW r1 required a closed destination matrix and hard routing rule.
  - PLAN_REVIEW r2 accepted routing scope but rejected stale phase markers.
  - PLAN_REVIEW r3 passed and allowed BUILD.

## Read Boundary
- Must Read:
  - AGENTS.md
  - .agentdocs/index.md
  - .agentdocs/archive/index.md
  - .agentdocs/insights.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/plan.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/BUILD-task-pack.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/CLOSE_REVIEW-task-pack.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E01.json
  - .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E02.json
  - .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E03.json
  - .agentdocs/archive/260312-agentdocs-v3-migration/reviews/plan-review-r3.json
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
  - .agentdocs/archive/index.md
  - .agentdocs/insights.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/plan.md
- Key Symbols / Entry Points:
  - taskctl.py::cmd_make_pack
  - taskctl.py::cmd_validate_pack
  - taskctl.py::cmd_sync_index
- Tests / Checks:
  - python .codex/workflow/taskctl.py validate-pack --pack .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/CLOSE_REVIEW-task-pack.md
  - rg -n "DEFAULT:|260309-taskctl-controller-hardening|当前任务（SSOT）|从当前 task root 下的" .agentdocs/index.md
  - python parser checks for current/archive entries
  - cat .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E01-build-validation.txt .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E02-hot-path-entry-check.txt .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E03-memory-routing-sample.txt
- Config / Runtime:
  - .agentdocs/archive/260312-agentdocs-v3-migration/ is the only active V3 task root.
  - Historical archive legality remains intentionally out of scope for this task.

## Action Boundary
- Write Boundary:
  - .agentdocs/archive/260312-agentdocs-v3-migration/reviews
  - .agentdocs/archive/260312-agentdocs-v3-migration/task-packs
- Forbidden Writes:
  - .agentdocs/index.md
  - .agentdocs/archive/index.md
  - .agentdocs/insights.md
  - .agentdocs/archive/**
  - .agentdocs/architecture/**
  - business-code
- Review Mode: FULL_REVIEW
- Escalation Rule: If any sampled migration destination is missing, if index navigation is still task-specific outside the SSOT section, or if workflow/plan/evidence drift remains, return NEEDS_CHANGES and send the task back to BUILD.

## Invariants
  - Every useful old-index section must have an explicit destination or reason to remain.
  - .agentdocs/index.md must keep task-specific paths only in the SSOT section; other navigation must remain generic or canonical.
  - BUILD must not rewrite architecture canonical docs or normalize historical archive bundles.

## Verification
- Must-Haves:
  - Index hot path is valid and future-proof: current task is discoverable through SSOT, while non-SSOT navigation stays generic.
  - Archive index exists and remains controller-parseable.
  - Sampled old-index memory items can be located through insights and existing architecture references without creating dual SoT.
  - Workflow, plan, and evidence reflect BUILD completion without stale r2-era phase truth.
- Verification Obligations:
  - Review whether the migrated index can survive future task switches or archive moves without stale hardcoded task paths outside SSOT.
  - Review whether sampled legacy information has a clear destination and whether compatibility notes remain sufficient.
  - Review whether E01/E02/E03 actually support the claimed BUILD completion.
  - Review whether any remaining bookkeeping drift would make ARCHIVE or task completion unsafe.
- Reviewer Recheck Plan:
  - .agentdocs/index.md
  - .agentdocs/archive/index.md
  - .agentdocs/insights.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/plan.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E01.json
  - .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E02.json
  - .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E03.json
- UAT:
  - A new session can start from .agentdocs/index.md, locate the current task from the SSOT section, and navigate to insights/archive without ambiguity or stale task-specific side paths.
