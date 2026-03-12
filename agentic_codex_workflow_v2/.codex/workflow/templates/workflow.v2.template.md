---
task_id: <task-id>
slug: <task-slug>
title: <task-title>
status: active
entropy: high
issue: <issue-url-or-na>
plan_doc: .agentdocs/tasks/<task-id>/plan.md
updated_at: <updated-at>
---

# Workflow：<task-title>

## 0) 状态头部
- Current State: DISCUSS
- Allowed Next State: ALIGN_PROOF
- Exception Status: NONE
- Last Updated: <updated-at>
- Task ID: <task-id>
- Entropy: High
- Task Root: .agentdocs/tasks/<task-id>/
- Task Pack Dir: .agentdocs/tasks/<task-id>/task-packs/
- Review Dir: .agentdocs/tasks/<task-id>/reviews/
- Evidence Dir: .agentdocs/tasks/<task-id>/evidence/
- Scratch Dir: .agentdocs/tasks/<task-id>/scratch/
- Handoff Snapshot:
  - Goal:
  - Current Progress:
  - Key Decisions:
  - Risks / Pitfalls:
  - Override / Upgrade Notes:
- Next Step:
  1. 完成 DISCUSS 与 ALIGN_PROOF
- Links:
  - GitHub Issue: <issue-url-or-na>
  - Plan Doc: .agentdocs/tasks/<task-id>/plan.md
  - Task Pack: .agentdocs/tasks/<task-id>/task-packs/
  - Index: .agentdocs/index.md
  - AGENTS: AGENTS.md

---

## 1) Discuss / Align Proof
### 1.1 Task Definition
- Problem:
- Goal:
- In Scope:
- Out of Scope:
- Acceptance:
- Constraints:
- Top Risks:

### 1.2 95% Understanding Check
- Goal Clear: NO
- Scope Clear: NO
- Non-Goals Clear: NO
- Truth Anchors Found: NO
- Write Boundary Clear: NO
- Acceptance Clear: NO
- Risks Clear: NO
- Open Questions Controlled: NO

### 1.3 Current Truth Anchors
- Code Paths:
- Key Symbols / Entry Points:
- Tests / Checks:
- Config / Runtime:
- Notes:

### 1.4 Context Coverage
- Must Read:
- Adjacent Scan:
- Unread But Potentially Relevant:
- Coverage Decision: INSUFFICIENT
- Coverage Notes:

---

## 2) Workflow State Machine
- Normal Path: DISCUSS -> ALIGN_PROOF -> BOOTSTRAP -> ISSUE_SYNC -> PLAN_DRAFT -> PLAN_REVIEW -> BUILD -> CLOSE_REVIEW -> ARCHIVE
- Current State Owner:
- Transition Check:
- Illegal Transition Seen: NO
- If YES, move to: EXCEPTION_RECOVERY

---

## 3) Plan Status
- Plan Doc Path: .agentdocs/tasks/<task-id>/plan.md
- Draft Status: NOT_STARTED
- Review Status: NOT_STARTED
- Current Review Round: 0
- Approved At:
- Notes:

---

## 4) Phase Board（执行 phase SSOT）
| Phase | Spec Ref | Owner | Status | Verification | Evidence Ref | Task Pack | Handoff |
|---|---|---|---|---|---|---|---|
| P1 | Plan §12.P1 | worker | TODO |  |  |  |  |
| P2 | Plan §12.P2 | worker | TODO |  |  |  |  |

规则：
- 这里只跟踪执行 phase；`PLAN_REVIEW / CLOSE_REVIEW` 结论写在专门的 review 区块
- `Status = DONE` 时，`Verification` 与 `Evidence Ref` 必须同时非空
- `Evidence Ref` 只能指向 `.agentdocs/.../evidence/*.json`
- `Task Pack` 必须指向 `.agentdocs/tasks/<task-id>/task-packs/`

---

## 5) Build Log
> 只记录可审计内容：关键决策、关键变更、关键验证、阻塞与恢复。

- YYYY-MM-DD HH:MM — ...

---

## 6) Evidence Ledger
### E01
- Evidence ID:
- Phase:
- Purpose:
- Command:
- CWD:
- Ran At:
- Exit Code:
- Result: PASS
- Output Path:
- Output Excerpt:
- Related Artifacts:
- Notes:
- Reviewer Recheck:

---

## 7) Runtime Pointers
- Active Task Pack:
- Current Phase Mode:
- Spec Source:
- Review Input:
- Latest Evidence Ref:
- Latest Plan Review Ref:
- Latest Close Review Ref:

---

## 8) Memory Routing
### Candidates
- Destination: architecture/ | insights.md
- Rule:
- Why:
- Trigger:
- Example:
- Source Workflow: .agentdocs/tasks/<task-id>/workflow.md
- Last Verified: YYYY-MM-DD
- Verification Source:

---

## 9) Issue Sync
### Summary
- ...

### Checklist
- [ ] P1 ...
- [ ] P2 ...

---

## 10) Plan Review
- Reviewer Session:
- Review Mode Used: FULL_REVIEW
- Decision: NOT_STARTED
- Summary:
- Required Changes:
- Evidence:
- Recheck Scope:
- Global Impact:
- Materials Accessed:
- Open Questions:

---

## 11) Final Review / Archive
- Reviewer Session:
- Review Mode Used: FULL_REVIEW
- Final Status: NOT_STARTED
- Key Findings:
- Required Follow-ups:
- Evidence Summary:
- Recheck Scope:
- Global Impact:
- Materials Accessed:
- Memory Write-back:
- Archive Actions:

---

## 12) Exception Recovery
- Status: NONE
- Trigger:
- Impact:
- Recovery Owner:
- Recovery Steps:
- Exit Gate:
- Closed At:
