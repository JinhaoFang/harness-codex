# Plan

## 0. Metadata

- Task ID:
- Title:
- Status: DRAFT | FROZEN | SUPERSEDED
- Owner:
- Created At:
- Last Updated At:
- Supersedes:
- Superseded By:

---

## 1. Intent

### 1.1 What I Need

> 用业务/用户语言描述这次要交付的结果，不写实现过程。

### 1.2 My Requirements

> 列出不可违背的要求、边界、约束、兼容性要求、性能/安全/交互要求等。

### 1.3 You Decide

> 明确授权 agent / engineer 自主决定的实现空间。

### 1.4 Non-Goals / Out of Scope

> 明确这次不做什么，避免 scope 漂移。

---

## 2. Current Reality Assumptions

### 2.1 Current Truth Anchors

> 列出当前世界真相的必要锚点，只放“必须承认的现实前提”。

- Code / module refs:
- Existing behavior refs:
- Test / build refs:
- Config / schema refs:
- Known constraints:

### 2.2 Preconditions

> 这份 plan 成立所依赖的前置条件。

- Preconditions:
- Assumptions:
- External dependencies:

---

## 3. Frozen Decisions

### 3.1 Locked Decisions

> 已经拍板、后续不得静默改写的决策。

- Decision:
- Why locked:
- Consequence:

### 3.2 Contracts / Interface Commitments

> 已承诺的接口、输入输出、兼容性、迁移约束。

### 3.3 Invariants

> 实现过程中必须始终成立的系统不变量。

### 3.4 Non-Reopen Without Approval

> 哪些问题如果要改变，必须显式回到 plan 重开。

---

## 4. Success Contract

### 4.1 Must-Haves

> 做成的最低必要条件。必须尽量写成可验证、可 yes/no 判断。

- [ ] Must-have 1
- [ ] Must-have 2
- [ ] Must-have 3

### 4.2 Acceptance Criteria

> 从“用户/调用方/系统外部观察者”的角度描述什么算成立。

- Criterion 1:
- Criterion 2:
- Criterion 3:

### 4.3 Verification Contract

> 每类 must-have 将通过什么证据被证明成立。

- Static / structure checks:
- Tests:
- Behavioral checks:
- UI / screenshot checks:
- Human review / UAT checks:

### 4.4 Reviewer Recheck Contract

> reviewer 必须复核什么；哪些问题一旦出现必须打回。

- Reviewer must recheck:
- Auto-fail conditions:
- Requires explicit sign-off for:

---

## 5. Human Verification (UAT)

### 5.1 UAT Scenarios

> 人类用来最终确认交付是否符合承诺的操作脚本。

- Scenario 1:
  - Steps:
  - Expected result:
- Scenario 2:
  - Steps:
  - Expected result:

### 5.2 Human-Visible Outcomes

> 哪些结果必须能被人直观看到/感知到，而不能只靠内部日志证明。

- Outcome 1:
- Outcome 2:

---

## 6. Risk & Reversibility

### 6.1 Top Risks

- Risk:
- Why it matters:
- Detection signal:

### 6.2 Migration / Rollout Constraints

> 是否涉及数据迁移、兼容性、灰度、切换顺序等。

### 6.3 Rollback Boundary

> 如果失败，回滚的边界是什么；什么可以撤销，什么不能。

### 6.4 Rollback Verification

> 怎么证明已经成功回滚或恢复到安全状态。

---

## 7. Governance

### 7.1 Already Decided

> 已有明确决策，后续不再争论。

### 7.2 Needs User Decision

> 必须回到用户/负责人拍板的问题。

### 7.3 Open Questions

> 尚未影响冻结、但需要后续跟踪的问题。

### 7.4 Change Rule

> 若 Goal / Scope / Acceptance / Contract / Invariant 发生变化：
>
> - 该 plan 必须回到 DRAFT
> - 下游 task 必须重新校验是否失效
> - 原结论不得默认沿用
