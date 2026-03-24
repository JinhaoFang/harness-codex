---
name: plan-eng-review
description: use when a grounded plan needs an owner-side engineering challenge on scope, architecture, code quality, tests, performance, and failure modes before formal independent plan review.
---

# plan-eng-review

Challenge the plan like a strong engineering manager before formal reviewer verdicts begin.

This skill is not the formal `plan-review` verdict.
It is an owner-side challenge pass that should sharpen the plan before requesting the independent reviewer.

## Runtime boundary

- This skill does not redefine Goal truth, Process truth, or completion truth.
- It does not replace `request-review -> submit-review`.
- It must not create a second long-term task ledger.
- If the repo already has a `TODOS.md`, design doc registry, or similar artifact, you may reuse it.
- If those artifacts do not exist, keep deferred work in `plan.md`, `workflow.md`, and explicit user decisions rather than inventing a new ledger.

## Use when

- the task has meaningful architecture or implementation tradeoffs
- the user asks for engineering review, architecture review, or code-quality review before coding
- the expected change is large enough that scope, tests, and failure modes should be challenged before formal reviewer handoff
- the plan touches multiple subsystems, important data flow, prompt/agent behavior, or risky production paths

## Read first

1. the latest design doc, if one exists
2. the active subtask pack, if one exists
3. the current `plan.md`
4. the current `workflow.md`
5. the minimum world anchors, source materials, and existing tests needed for grounded criticism
6. recent branch history if there are signs of prior review-driven rework or revert churn
7. `TODOS.md` only if the repo already uses it

## Engineering preferences

- DRY matters; flag repetition aggressively.
- Test depth is non-negotiable; prefer complete coverage over thin happy-path coverage.
- Aim for "engineered enough": not hacky, not prematurely abstract.
- Handle edge cases thoughtfully.
- Prefer explicit over clever.
- Prefer the minimum diff that fully solves the real problem.

## Cognitive patterns

Apply these as instincts, not a second checklist:

- diagnose state before proposing process
- reason about blast radius first
- prefer boring technology by default
- prefer incremental change over rewrites
- prefer systems that work for tired humans
- optimize for reversibility
- treat failures as information
- watch for accidental complexity
- improve developer experience when it directly improves delivery quality
- make the structural change easy before making the behavioral change
- remember production ownership when reviewing risky plans

## Documentation and diagrams

- Use ASCII diagrams for non-trivial data flow, state transitions, pipelines, or decision trees.
- If the implementation will touch complex models, controllers, services, or non-obvious tests, call out where inline ASCII diagrams should live in code comments.
- Diagram maintenance is part of the change. If touched code already has nearby diagrams, review and update them as part of the same change.

## Step 0: Scope challenge

Before detailed review, answer:

1. What existing code or flows already solve part of the problem?
2. What is the minimum change set that achieves the real goal?
3. Complexity smell: if the plan touches more than 8 files or introduces more than 2 new classes/services, challenge whether the same goal can be reached with fewer moving parts.
4. If `TODOS.md` already exists, are any deferred items blocking this plan or worth bundling without expanding scope?
5. Is the plan taking an unnecessary shortcut where a more complete version costs little extra?

If the complexity smell triggers, recommend scope reduction before proceeding with the rest of the review.

## Review sections

Work through these sections in order:

1. Architecture
2. Code quality
3. Test review
4. Performance

For every real issue:

- ask the user one issue at a time
- do not batch unrelated issues into one question
- describe the problem concretely with file references when possible
- give 2-3 options, including "do nothing" when that is reasonable
- state a recommendation
- explain effort, risk, and maintenance tradeoffs

If a section has no real issues, say so and move on.
If a fix is obvious and low-risk, say what should happen and move on without manufacturing a decision point.

## 1. Architecture review

Evaluate:

- component boundaries and coupling
- data flow and dependency direction
- scaling and single points of failure
- security boundaries and risky trust assumptions
- reuse opportunities versus parallel construction
- whether key flows deserve ASCII diagrams
- one realistic production failure mode for each new path

## 2. Code quality review

Evaluate:

- module organization
- DRY violations
- error handling and missing edge cases
- under-engineering or over-engineering
- stale or missing inline diagrams near touched code
- whether the plan introduces abstractions earlier than necessary

## 3. Test review

Produce a simple ASCII diagram covering:

- new UX or user-visible behavior
- new data flow
- new code paths
- new branches or outcomes

For each new path, ask:

- what test proves it
- which edge case should also be covered
- whether prompt / agent-instruction changes need explicit eval scope and baseline comparison

## 4. Performance review

Evaluate:

- N+1 or repeated expensive calls
- memory growth or retention risks
- caching opportunities
- slow paths and unnecessary complexity on hot paths

## Required outputs

Every completed plan engineering review should produce:

- `NOT in scope`: explicitly deferred work with one-line rationale
- `What already exists`: current code or flows that already solve part of the problem
- `Failure modes`: for each new path, one realistic production failure and whether it has a test, error handling, and clear user-visible failure
- `Completion summary`: counts by section, critical gaps, and whether the recommendation chose the complete version or a shortcut
- `Unresolved decisions`: anything the user did not answer or explicitly deferred

If a repo-local `TODOS.md` already exists, propose TODO additions one at a time.
If no such file exists, do not create one just for this review.

## Critical gaps

Treat this as a critical gap:

- a new path has no test
- no meaningful error handling
- and would fail silently in production

## Suggested placement in the flow

Recommended order when this skill is used:

```text
Discuss
-> Ground in World
-> Freeze Goal Truth
-> refresh-pack
-> optional plan-eng-review
-> formal plan-review
```

If this review changes the plan materially, refresh the pack again before requesting formal plan review.

## Do not

- do not submit formal review verdicts from this skill
- do not create external review dashboards or sidecar ledgers
- do not force `TODOS.md` into repos that do not already use it
- do not treat this skill as permission to start implementation early
