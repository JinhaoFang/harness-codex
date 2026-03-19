---
name: plan-review
description: use when a grounded plan exists and codex needs an independent, fresh-context review of executability, reuse, boundaries, verification, and rollback before implementation begins.
---

# plan-review

Review a grounded plan like an owner, not like a formatter.

## Role assumptions
Use this skill from the `plan_reviewer` role or in an equivalent read-only review context.

## Read first
- the active subtask pack
- the current `plan.md`
- the relevant `workflow.md` state
- the workflow discuss-readiness constraints and any task-level stage / approval / deletion guard notes
- source materials when the task migrates, deletes, reorganizes, or reclassifies existing materials
- the minimum world anchors needed to judge the plan

## Review questions
- Does the plan define a single terminal completion definition, and explicitly reject "not acceptable completion" definitions?
- Does the plan preserve the confirmed task rhythm, stage order, approval points, and review-before-action constraints?
- Does it keep user-confirmed requirements separate from agent execution latitude and unfrozen assumptions?
- Does the plan match the actual codebase, tests, and interfaces?
- Does it use only current world objects as world-grounded anchors?
- For migration / deletion / reclassification tasks, did it review the source materials and preserve enough disposition evidence?
- Does the phase order prevent "premature cleanup" while successor work still depends on legacy materials?
- Does it miss an obvious reusable mechanism?
- Is the write boundary explicit and safe?
- Can the verification section really prove completion?
- Is rollback concrete enough?
- Are subtasks small and reviewable?

## Review style
- Use fresh context.
- Fully check task requirements, the workflow Discuss readiness constraints, and Goal truth core constraints; they are not sampleable.
- World truth may be sampled only when you record the scope, basis, residual risk, and actual materials accessed.
- Inspect only the minimum anchors needed for a grounded judgment once the mandatory full checks above are satisfied.
- Lead with concrete findings and the smallest blocking delta.
- Prefer path and symbol references over vague concerns.

## Structured writeback
The main agent should request the review before handing work to the reviewer:

```bash
python .codex/tools/agentctl.py request-review --task-id <task-id> --review-type plan --subtask <subtask-id>
```

Then the reviewer submits the final judgment through the controller:

```bash
python .codex/tools/agentctl.py submit-review   --task-id <task-id>   --subtask <subtask-id>   --review-type plan   --request-id <request-id>   --reviewer-role plan_reviewer   --decision PASS|CHANGES_REQUIRED|REJECT   --plan-ref .agentdocs/tasks/<task-id>/plan.md   --task-requirement <workflow-or-user-constraint-ref>   --world-anchor <path-or-symbol>   --material-accessed <path-or-symbol>   --coverage-task-requirements FULL   --coverage-goal-truth FULL   --coverage-world-truth FULL|SAMPLED   --sampling-scope "<when sampled>"   --sampling-basis "<when sampled>"   --residual-risk "<when sampled>"   --finding type:severity:summary
```

## Do not
- do not rewrite the plan for the author
- do not implement code
- do not advance workflow state by hand
- do not let the main agent submit the reviewer verdict on your behalf
- do not share builder long-context assumptions as evidence
