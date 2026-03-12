---
task_id: <task-id>
slug: <task-slug>
title: <task-title>
workflow: .agentdocs/tasks/<task-id>/workflow.md
issue: <issue-url-or-na>
status: draft
updated_at: <updated-at>
---

# Plan：<task-title>

## 0) 元信息
- Task ID: <task-id>
- Workflow: .agentdocs/tasks/<task-id>/workflow.md
- Issue: <issue-url-or-na>
- Status: DRAFT
- Updated At: <updated-at>

---

## 1) Understanding Proof
- Goal Restatement:
- Explicit Non-Goals:
- Why This Task Exists Now:
- 95% Understanding Check: NO
- Missing Pieces:

---

## 2) What I Need / My Requirements / You Decide
### 2.1 What I Need
- User Outcome:
- Deliverable:
- Acceptance Signal:

### 2.2 My Requirements
- Hard Constraints:
- Preferred Constraints:
- Non-Negotiables:

### 2.3 You Decide
- Agent Decision Space:
- Decisions Requiring User Confirmation:
- Escalation Triggers:

---

## 3) 当前事实锚点（Current Truth Anchors）
### 3.1 Code Paths
- Path 1:
- Path 2:

### 3.2 Key Symbols / Entry Points
- Symbol 1:
- Symbol 2:

### 3.3 Tests / Checks
- Existing Tests:
- Missing Tests:

### 3.4 Config / Env / Runtime
- Config Anchors:
- Runtime Evidence:
- Notes:

---

## 4) 背景与目标
- Problem:
- Goal:
- In Scope:
- Out of Scope:
- Success Criteria:

---

## 5) Memory Lookup 与 Context Coverage
### 5.1 Memory Lookup
- architecture Inputs:
- insights Inputs:
- Reused Rules:
- Re-validation Needed:

### 5.2 Context Coverage Contract
- Must Read:
- Adjacent Scan:
- Unread But Potentially Relevant:
- Coverage Decision: SUFFICIENT
- Coverage Notes:

### 5.3 Scratch Promotion Rule
- Scratch Dir: .agentdocs/tasks/<task-id>/scratch/
- Allowed Scratch Content:
- Promotion Required Before Build:
- Scratch Close Condition:

---

## 6) 已拍板事项（Decision Freeze）
### 6.1 技术 / 依赖 / 基础设施
- Selected:
- Version / Constraint:
- Rejected Alternatives + Why:
- Rollback Switch (if any):

### 6.2 数据 / 协议 / 公共口径
- Frozen Contracts:

---

## 7) 契约与边界
### 7.1 Invariants
- Invariant 1:
- Invariant 2:

### 7.2 Interfaces / Data / Errors / Compatibility
- Inputs:
- Outputs:
- Public API / Schema Changes:
- Error Strategy:
- Compatibility Strategy:

### 7.3 Edge Cases
- Boundary Case 1:
- Boundary Case 2:
- Timeout / Retry / Idempotency / Concurrency:

---

## 8) Must-Haves
### 8.1 Truths
- Truth 1:
- Truth 2:

### 8.2 Artifacts
- Artifact 1:
- Artifact 2:

### 8.3 Key Links
- Link 1:
- Link 2:

---

## 9) Verification Ladder
- Static:
- Command:
- Behavioral:
- Human:
- Minimum Required For PASS:

---

## 10) Reviewer Recheck Plan
- Plan Reviewer Recheck:
- Close Reviewer Recheck:
- Escalation To FULL_REVIEW If:

---

## 11) Issue Breakdown（issue 是 plan 的子结构）
### Issue 1 — <title>
- Goal:
- Depends On:
- Write Boundary:
- Verify:
- Rollback Note:

### Issue 2 — <title>
- Goal:
- Depends On:
- Write Boundary:
- Verify:
- Rollback Note:

---

## 12) 分阶段规格（<= 7 phases）
说明：
- `workflow.md` 的 Phase Board 只跟踪执行 phase
- `PLAN_REVIEW / CLOSE_REVIEW` 的结论写在 workflow review sections，不把 `reviews/*.json` 当作 phase evidence

### P1 — <title>
- Goal:
- Output:
- Files / Modules Touched:
- Write Boundary:
- Truth Anchors To Recheck:
- Verify:
- Evidence Bundle:
- Checkpoint Policy:
- Risks / Notes:

### P2 — <title>
- Goal:
- Output:
- Files / Modules Touched:
- Write Boundary:
- Truth Anchors To Recheck:
- Verify:
- Evidence Bundle:
- Checkpoint Policy:
- Risks / Notes:

---

## 13) 风险、迁移与回滚
### 13.1 Top Risks
1. ...
2. ...
3. ...

### 13.2 Migration / Rollback
- Code Rollback:
- Dependency Rollback:
- Data / Config Rollback:
- Rollback Verification:

---

## 14) UAT（非阻塞）
- Persona / Operator:
- Preconditions:
- Steps:
- Expected Result:
- What To Screenshot / Observe:

---

## 15) Governance Check
- Needs User Decision:
- Already Decided:
- Open Questions (<= 3):
