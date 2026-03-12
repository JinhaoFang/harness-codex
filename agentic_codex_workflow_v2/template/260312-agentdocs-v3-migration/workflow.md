---
task_id: 260312-agentdocs-v3-migration
slug: agentdocs-v3-migration
title: Agentdocs V3 运行模型迁移
status: archived
entropy: high
issue: N/A
plan_doc: .agentdocs/archive/260312-agentdocs-v3-migration/plan.md
updated_at: 2026-03-12 11:37 +0800
---

# Workflow：Agentdocs V3 运行模型迁移

## 0) 状态头部
- Current State: ARCHIVE
- Allowed Next State: <none>
- Exception Status: NONE
- Last Updated: 2026-03-12 11:37 +0800
- Task ID: 260312-agentdocs-v3-migration
- Entropy: High
- Task Root: .agentdocs/archive/260312-agentdocs-v3-migration/
- Task Pack Dir: .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/
- Review Dir: .agentdocs/archive/260312-agentdocs-v3-migration/reviews/
- Evidence Dir: .agentdocs/archive/260312-agentdocs-v3-migration/evidence/
- Scratch Dir: .agentdocs/archive/260312-agentdocs-v3-migration/scratch/
- Handoff Snapshot:
  - Goal: 把当前 `.agentdocs/` 从 V2 过渡态迁到可运行的 V3 热路径，恢复真实 active task 入口，并迁移旧 index 中仍有价值的长期信息。
  - Current Progress: `.agentdocs/index.md`、`.agentdocs/archive/index.md`、`.agentdocs/insights.md` 的迁移已完成；`CLOSE_REVIEW` 已 PASS，task bundle 已归档到 `.agentdocs/archive/260312-agentdocs-v3-migration/`。
  - Key Decisions:
    - 旧 `index.md` 不能直接覆盖成新模板，必须保留有效信息并迁移到合适目的地。
    - 历史 archive task 维持只读兼容，不做全量 V3 结构化回填。
    - 新 task 从现在开始遵守 V3 合同。
  - Risks / Pitfalls:
    - index 如果只做模板替换，会丢失长期记忆。
    - 如果把历史 archive 全部拉入本轮，会导致范围失控。
    - “全局重要记忆”中部分条目本质是 architecture 事实，迁移时要避免复制出新的双 SoT。
  - Override / Upgrade Notes:
    - 用户已明确同意修复 `index.md`、冻结 compat strategy、执行内容迁移；同时确认历史 archive 的形式合法性不是本轮阻塞。
- Next Step:
  1. 当前无 active 后续步骤
  2. 若未来继续演进 `.agentdocs` 结构，应新建新的 task-scoped 任务
  3. 本归档 bundle 仅作为迁移审计与复盘入口
- Links:
  - GitHub Issue: N/A
  - Plan Doc: .agentdocs/archive/260312-agentdocs-v3-migration/plan.md
  - Task Pack: .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/
  - Index: .agentdocs/index.md
  - AGENTS: AGENTS.md

---

## 1) Discuss / Align Proof
### 1.1 Task Definition
- Problem: 当前 `.agentdocs/index.md` 仍保留 V2 当前任务入口并指向缺失 task，热路径没有真实 active task；同时旧 index 把导航、长期记忆、legacy reference 混写在一起，已经不适合作为 V3 新会话入口。
- Goal: 建立真实 V3 active task，重写 `index.md` 的热路径结构，并把旧 index 的有效长期内容迁移到 `insights.md` / `architecture` 引用 / legacy reference，而不是直接删除。
- In Scope:
  - 当前 task bundle 的 V3 对齐
  - `index.md` 重构
  - `archive/index.md` 补齐
  - `insights.md` 迁移旧 index 的长期记忆
  - compat strategy 冻结
- Out of Scope:
  - 历史 archive 全量 V3 回填
  - 业务代码改动
  - GitHub issue 镜像流程
- Acceptance:
  - `index.md` 指向真实 active task
  - 旧 index 有效信息有明确迁移去向
  - `archive/index.md` 存在
  - 本任务 task pack 可通过当前 `validate-pack`
- Constraints:
  - 不能无目的删除旧 index 信息
  - 历史 archive 的形式合法性不作为本轮阻塞
  - 新热路径要遵守 V3
- Top Risks:
  - 信息丢失
  - 范围膨胀到历史 archive 回填
  - insights / architecture 边界再次混乱

### 1.2 95% Understanding Check
- Goal Clear: YES
- Scope Clear: YES
- Non-Goals Clear: YES
- Truth Anchors Found: YES
- Write Boundary Clear: YES
- Acceptance Clear: YES
- Risks Clear: YES
- Open Questions Controlled: YES

### 1.3 Current Truth Anchors
- Code Paths:
  - `.agentdocs/index.md`
  - `.agentdocs/insights.md`
  - `.codex/workflow/taskctl.py`
  - `.codex/workflow/templates/index.template.md`
  - `.agentdocs/archive/260308-agentdocs-v2-migration/workflow.md`
  - `.agentdocs/archive/260308-backend-architecture-reorg/workflow.md`
- Key Symbols / Entry Points:
  - `taskctl.py::cmd_create_task`
  - `taskctl.py::cmd_sync_index`
  - `taskctl.py::cmd_make_pack`
  - `taskctl.py::cmd_validate_pack`
- Tests / Checks:
  - `test -f .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md`
  - `rg -n "DEFAULT:|## 2\) 当前任务（SSOT\)|260309-taskctl-controller-hardening" .agentdocs/index.md`
  - `python .codex/workflow/taskctl.py validate-pack --pack .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/BUILD-task-pack.md`
  - `find .agentdocs/archive -maxdepth 2 -type f | sort`
- Config / Runtime:
  - `AGENTS.md`
  - `docs/dev/contracts/session-minimum-align.md`
  - `docs/dev/contracts/task-pack-layout.md`
  - `docs/dev/contracts/task-archive-lifecycle.md`
  - `docs/dev/contracts/structured-writeback.md`
- Notes:
  - 当前任务以“controller + contracts + state files 的实际内容”为事实真源。

### 1.4 Context Coverage
- Must Read:
  - `AGENTS.md`
  - `.agentdocs/index.md`
  - `.agentdocs/insights.md`
  - `.codex/workflow/taskctl.py`
  - `docs/dev/contracts/session-minimum-align.md`
  - `docs/dev/contracts/high-entropy-state-machine.md`
  - `docs/dev/contracts/task-pack-layout.md`
  - `docs/dev/contracts/task-archive-lifecycle.md`
  - `docs/dev/contracts/structured-writeback.md`
- Adjacent Scan:
  - `.agentdocs/archive/260308-agentdocs-v2-migration/**`
  - `.agentdocs/archive/260308-backend-architecture-reorg/**`
  - `.agentdocs/architecture/*.md`
  - `.agentdocs/workflow/*.md`
- Unread But Potentially Relevant:
  - `docs/dev/system/module-boundaries.md`
- Coverage Decision: SUFFICIENT
- Coverage Notes:
  - 已足够支撑 BUILD 收尾与下一步 `CLOSE_REVIEW`；剩余工作是 task-scoped bookkeeping 与独立复核。

---

## 2) Workflow State Machine
- Normal Path: DISCUSS -> ALIGN_PROOF -> BOOTSTRAP -> ISSUE_SYNC -> PLAN_DRAFT -> PLAN_REVIEW -> BUILD -> CLOSE_REVIEW -> ARCHIVE
- Current State Owner: controller
- Transition Check: PASS (CLOSE_REVIEW -> ARCHIVE; CLOSE_REVIEW passed and archive-task completed successfully; task bundle now lives under .agentdocs/archive/.)
- Illegal Transition Seen: NO
- If YES, move to: EXCEPTION_RECOVERY

---

## 3) Plan Status
- Plan Doc Path: .agentdocs/archive/260312-agentdocs-v3-migration/plan.md
- Draft Status: BUILD_COMPLETE_PENDING_CLOSE_REVIEW
- Review Status: PASS
- Current Review Round: 3
- Approved At: 2026-03-12 11:09 +0800
- Notes:
  - `plan-review-r1.json` 与 `plan-review-r2.json` 已记录前两轮 `NEEDS_CHANGES`。
  - `plan-review-r3.json` 已记录 round-3 `PASS`；controller 已在 2026-03-12 11:10 +0800 推进到 `BUILD`。

---

## 4) Phase Board（执行 phase SSOT）
| Phase | Spec Ref | Owner | Status | Verification | Evidence Ref | Task Pack | Handoff |
|---|---|---|---|---|---|---|---|
| P2 | Plan §12.P2 | worker | DONE | `.agentdocs/index.md` 与 `.agentdocs/archive/index.md` 已重构，当前任务与 archive 条目可被 controller / regex 检索 | `.agentdocs/archive/260312-agentdocs-v3-migration/evidence/E02.json` | `.agentdocs/archive/260312-agentdocs-v3-migration/task-packs/BUILD-task-pack.md` | BUILD 输出已完成 |
| P3 | Plan §12.P3 | worker | DONE | 旧 index 长期记忆已迁入 `insights.md` 并收口 compat strategy；抽样条目已能落到 `index` / `insights` / `architecture` 引用 | `.agentdocs/archive/260312-agentdocs-v3-migration/evidence/E03.json` | `.agentdocs/archive/260312-agentdocs-v3-migration/task-packs/BUILD-task-pack.md` | BUILD 输出已完成 |

规则：
- 这里只跟踪执行 phase；`PLAN_REVIEW / CLOSE_REVIEW` 结论写在专门的 review 区块
- `Status = DONE` 时，`Verification` 与 `Evidence Ref` 必须同时非空
- `Evidence Ref` 只能指向 `.agentdocs/.../evidence/*.json`
- `Task Pack` 必须指向 `.agentdocs/archive/260312-agentdocs-v3-migration/task-packs/`

---

## 5) Build Log
> 只记录可审计内容：关键决策、关键变更、关键验证、阻塞与恢复。

- 2026-03-12 10:43 +0800 — 使用 `taskctl create-task` 创建 `260312-agentdocs-v3-migration` task-scoped 骨架。
- 2026-03-12 10:43 +0800 — 确认当前 `.agentdocs/index.md` 指向缺失 task，`.agentdocs/tasks/` 无 active task，当前热路径不满足 V3 最小恢复合同。
- 2026-03-12 10:43 +0800 — 用户确认：修复 `index.md` 时不能直接删除旧内容，应分析后迁移；历史 archive 的形式合法性可忽略。
- 2026-03-12 10:49 +0800 — 已生成并校验首版 `PLAN_REVIEW` task pack，进入 `PLAN_REVIEW`。
- 2026-03-12 10:53 +0800 — `plan-review-r1.json` 返回 `NEEDS_CHANGES`：要求冻结闭合 destination matrix、hard routing rule，并修正 phase truth 漂移；当前已按状态机回退到 `PLAN_DRAFT`。
- 2026-03-12 10:58 +0800 — 已冻结 destination matrix 与 hard routing rule，刷新 `PLAN_REVIEW` task pack 并重新进入 `PLAN_REVIEW`（round 2）。
- 2026-03-12 11:03 +0800 — `plan-review-r2.json` 返回 `NEEDS_CHANGES`：destination matrix 与 hard routing rule 已放行，当前只需修正 plan/workflow 的 phase-truth bookkeeping；已按状态机回退到 `PLAN_DRAFT`。
- 2026-03-12 11:05 +0800 — 已修正 plan/workflow 的 phase-truth bookkeeping，刷新 round-3 `PLAN_REVIEW` task pack 并重新进入 `PLAN_REVIEW`。
- 2026-03-12 11:09 +0800 — `plan-review-r3.json` 返回 `PASS`：phase truth 已对齐，BUILD 已获放行；当前等待 controller 正式推进状态。
- 2026-03-12 11:10 +0800 — controller 已执行 `PLAN_REVIEW -> BUILD`，并生成 `BUILD-task-pack.md` 作为当前执行入口。
- 2026-03-12 11:21 +0800 — 已完成 `.agentdocs/index.md`、`.agentdocs/archive/index.md`、`.agentdocs/insights.md` 的 BUILD 改造，并以 `E01` 记录 active task / archive index / insights 迁移的联合校验结果。
- 2026-03-12 11:26 +0800 — 已补齐 BUILD bookkeeping，当前准备生成 `CLOSE_REVIEW` task pack 并进入独立 close review。
- 2026-03-12 11:31 +0800 — 已将 `index.md` 中 task-specific 快速入口改为泛化导航，并去除会随 archive 增长自行陈旧的 archive 明细列表。
- 2026-03-12 11:31 +0800 — controller 已执行 `BUILD -> CLOSE_REVIEW`，当前 active pack 为 `CLOSE_REVIEW-task-pack.md`。
- 2026-03-12 11:37 +0800 — `close-review-r1.json` = PASS，controller 已执行 `archive-task` 并将 task bundle 移入 `.agentdocs/archive/260312-agentdocs-v3-migration/`。
- 2026-03-12 11:37 +0800 — controller 已执行 `CLOSE_REVIEW -> ARCHIVE`；`.agentdocs/index.md` 当前任务段现为 `NONE`，本任务已写入 `.agentdocs/archive/index.md`。

---

## 6) Evidence Ledger
### E01
- Evidence ID: E01
- Phase: BUILD
- Purpose: 验证 V3 热路径迁移后的当前任务入口、archive index 与 BUILD task pack 均可被 controller/regex 检索并且不再残留失效 260309 指针
- Command: python .codex/workflow/taskctl.py sync-index --root . --task-id 260312-agentdocs-v3-migration --title "Agentdocs V3 运行模型迁移" --current-state BUILD --entry-kind DEFAULT; python .codex/workflow/taskctl.py validate-pack --pack .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/BUILD-task-pack.md; python evidence parser checks
- CWD: /root/project/AstraFlow_v0.1
- Ran At: 2026-03-12 11:21 +0800
- Exit Code: 0
- Result: PASS
- Output Path: .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E01-build-validation.txt
- Output Excerpt: issues=[]; current_entries=1 DEFAULT; archive_entries=2; insights_migration_section=True
- Related Artifacts:
  - .agentdocs/index.md
  - .agentdocs/archive/index.md
  - .agentdocs/insights.md
  - .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/BUILD-task-pack.md
- Notes: 修正了 reviewer 越界改动中的 archive index 格式与绝对路径链接问题后重新校验。
- Reviewer Recheck: YES

### E02
- Evidence ID: E02
- Phase: BUILD
- Purpose: 验证热路径入口重构完成：index 仅指向真实 active task，archive index 可稳定列出当前 archive bundle。
- Command: rg -n "DEFAULT:|## 2\\) 当前任务（SSOT\\)|260309-taskctl-controller-hardening" .agentdocs/index.md; python archive/current-task parser checks
- CWD: /root/project/AstraFlow_v0.1
- Ran At: 2026-03-12 11:29 +0800
- Exit Code: 0
- Result: PASS
- Output Path: .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E02-hot-path-entry-check.txt
- Output Excerpt: current_entry=DEFAULT .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md; archive_entry_count=2; stale_260309_pointer_present=False; archive_index_parse_ok=True
- Related Artifacts:
  - .agentdocs/index.md
  - .agentdocs/archive/index.md
- Notes: 已修复 archive index 条目格式到 controller 可解析形态。
- Reviewer Recheck: YES
### E03
- Evidence ID: E03
- Phase: BUILD
- Purpose: 验证旧 index 长期记忆迁移闭合：抽样条目可在 insights、index 与 architecture 引用中找到明确落点。
- Command: rg -n "旧 index 全局记忆迁移（2026-03-12）|legacy `backend/\*\*`|old_global_memory_block_present" .agentdocs/insights.md .agentdocs/index.md .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E03-memory-routing-sample.txt
- CWD: /root/project/AstraFlow_v0.1
- Ran At: 2026-03-12 11:29 +0800
- Exit Code: 0
- Result: PASS
- Output Path: .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E03-memory-routing-sample.txt
- Output Excerpt: insights_migration_section_present=True; sample_product_memory_in_insights=True; sample_architecture_pointer_in_insights=True; sample_legacy_backend_stub_note_in_index=True; old_global_memory_block_present_in_index=False
- Related Artifacts:
  - .agentdocs/index.md
  - .agentdocs/insights.md
- Notes: 按冻结的 routing matrix 只迁移运行时经验，architecture 事实保持引用，不复制 canonical 正文。
- Reviewer Recheck: YES

## 7) Runtime Pointers
- Active Task Pack: `.agentdocs/archive/260312-agentdocs-v3-migration/task-packs/CLOSE_REVIEW-task-pack.md`（final reviewed pack；task 已归档）
- Current Phase Mode: ARCHIVE_COMPLETE
- Spec Source: `.agentdocs/archive/260312-agentdocs-v3-migration/plan.md` §6.3-§6.5, §12.P2-§12.P3
- Review Input: `.agentdocs/archive/260312-agentdocs-v3-migration/reviews/plan-review-r3.json`; `.agentdocs/archive/260312-agentdocs-v3-migration/reviews/close-review-r1.json`
- Latest Evidence Ref: `.agentdocs/archive/260312-agentdocs-v3-migration/evidence/E03.json`
- Latest Plan Review Ref: `.agentdocs/archive/260312-agentdocs-v3-migration/reviews/plan-review-r3.json`
- Latest Close Review Ref: `.agentdocs/archive/260312-agentdocs-v3-migration/reviews/close-review-r1.json`

---

## 8) Memory Routing
### Candidates
- Destination: insights.md
- Rule: 旧 index 中稳定、跨任务可复用、但不直接充当专题架构 SoT 的长期经验，迁入 `insights.md`
- Why: 这类内容不应继续留在 index 热路径，但也不能丢失
- Trigger: 旧 index 的“全局重要记忆”
- Example: 路径稳定性优先于目录美观；跨服务共享配置与身份口径必须由测试锁定
- Destination: architecture/
- Rule: 如果某条旧 index 记忆本质上是长期系统事实，应优先指向已有 `architecture/*.md`
- Why: 避免 insights 与 architecture 形成双 SoT
- Trigger: 媒体存储、后端/agent 结构、runtime 协作边界
- Example: `architecture/media_storage_and_files.md`
- Source Workflow: .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md
- Last Verified: 2026-03-12
- Verification Source:
  - `.agentdocs/index.md`
  - `.agentdocs/insights.md`

---

## 9) Issue Sync
### Summary
- 当前 issue 已收口为三部分：修热路径入口、迁长期信息、冻结闭合 destination matrix；不扩展到历史 archive 全量修复。

### Checklist
- [x] P1 对齐当前失效状态与迁移边界
- [x] P2 重构热路径入口
- [x] P3 迁移旧 index 长期记忆并收口 compat strategy
- [x] P4 修复 reviewer findings、通过 PLAN_REVIEW 并进入 BUILD

---

## 10) Plan Review
- Reviewer Session: .agentdocs/archive/260312-agentdocs-v3-migration/reviews/plan-review-r3.json
- Review Mode Used: FULL_REVIEW
- Decision: PASS
- Summary: Phase truth is aligned across plan, workflow, and the round-3 PLAN_REVIEW pack; BUILD is allowed.
- Required Changes:
- Evidence: Round-3 review confirms the previously approved destination matrix and hard routing rule stayed frozen, and the remaining phase-truth drift called out in r2 has been reconciled.
- Recheck Scope: Proceed to BUILD within the frozen hot-path doc scope: `.agentdocs/index.md`、`.agentdocs/insights.md`、`.agentdocs/archive/index.md` 与 task-scoped artifacts。
- Global Impact: Clears the active review gate so the V3 hot-path migration can start without reopening archive normalization or architecture canonical scope.
- Materials Accessed: AGENTS.md; .agentdocs/archive/260312-agentdocs-v3-migration/plan.md; .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md; .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/PLAN_REVIEW-task-pack.md; .agentdocs/archive/260312-agentdocs-v3-migration/scratch/index-destination-matrix.md; .agentdocs/index.md; .agentdocs/insights.md; docs/dev/contracts/task-pack-layout.md; docs/dev/contracts/session-minimum-align.md
- Open Questions: No blocking open questions.

---

## 11) Final Review / Archive
- Reviewer Session: .agentdocs/archive/260312-agentdocs-v3-migration/reviews/close-review-r1.json
- Review Mode Used: FULL_REVIEW
- Final Status: PASS
- Key Findings: No closure-blocking findings. The migrated index is future-proof enough for task switching, archive index is parseable, sampled old-index memory lands correctly, and workflow/plan/evidence are aligned for task completion.
- Required Follow-ups: 
- Evidence Summary: Reviewer confirmed: index navigation keeps task-specific paths only in the SSOT section; archive index contains 2 valid controller-parseable entries; insights migration block is present and sampled items match the frozen routing rule; BUILD evidence E01/E02/E03 is corroborated by current files.
- Recheck Scope: .agentdocs/index.md; .agentdocs/archive/index.md; .agentdocs/insights.md; .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md; .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E01.json; .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E02.json; .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E03.json
- Global Impact: The .agentdocs hot path is stable enough that future active-task changes or archive moves should not recreate the broken-entry failure mode.
- Materials Accessed: AGENTS.md; .agentdocs/index.md; .agentdocs/archive/index.md; .agentdocs/insights.md; .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md; .agentdocs/archive/260312-agentdocs-v3-migration/plan.md; .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/BUILD-task-pack.md; .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/CLOSE_REVIEW-task-pack.md; .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E01.json; .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E02.json; .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E03.json; .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E01-build-validation.txt; .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E02-hot-path-entry-check.txt; .agentdocs/archive/260312-agentdocs-v3-migration/evidence/E03-memory-routing-sample.txt; .agentdocs/archive/260312-agentdocs-v3-migration/reviews/plan-review-r3.json
- Memory Write-back:
- Archive Actions: Close review passes. The task may be archived; doing so will clear the current-task SSOT entry from index and add this task bundle to archive/index.md.

---

## 12) Exception Recovery
- Status: NONE
- Trigger:
- Impact:
- Recovery Owner:
- Recovery Steps:
- Exit Gate:
- Closed At:
