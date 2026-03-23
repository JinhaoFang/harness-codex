---
name: close-review
description: use when implementation evidence exists and codex needs an independent, fresh-context judgment about delivery readiness, drift from the approved plan, and evidence traceability before archive.
---

# close-review

Review delivery readiness with fresh context.

## Role assumptions
Use this skill from the `close_reviewer` role or in an equivalent read-only review context.
Start with `$subagent-bootstrap`.
The parent prompt may add extra focus, but it must not shrink mandatory review scope.

## Preconditions
`python .codex/tools/agentctl.py check-gate --task-id <task-id> --action close-review` passes.

## Read first
- active subtask pack
- approved `plan.md`
- current `workflow.md`
- relevant evidence JSON files
- the latest close review only after you have rebuilt the current-state judgment, when a rereview must confirm prior findings are closed
- source materials when the task migrated, deleted, reorganized, or reclassified existing materials
- a minimal sample of changed code or runtime artifacts

## Review questions
- Does the delivered work drift from the approved plan?
- Are tests and behavior checks traceable from evidence to code paths?
- For code-bearing development subtasks, is there traceable evidence that the required TDD loop happened through real failing and passing behavior checks?
- For migration / deletion / reclassification tasks, can the result still be traced back to source materials and approved deletion / migration guardrails?
- Is there an unnecessary new path where reuse should have been used?
- Is anything missing that would block a safe close?

## Structured writeback

The main agent should request the review before handing work to the reviewer:

```bash
python .codex/tools/agentctl.py request-review --task-id <task-id> --review-type close --subtask <subtask-id>
```

```bash
python .codex/tools/agentctl.py submit-review   --task-id <task-id>   --subtask <subtask-id>   --review-type close   --request-id <request-id>   --reviewer-role close_reviewer   --decision PASS|CHANGES_REQUIRED|REJECT   --plan-ref .agentdocs/tasks/<task-id>/plan.md   --task-requirement <workflow-or-user-constraint-ref>   --code-path <path>   --test <path>   --evidence-ref <evidence-json>   --material-accessed <path-or-symbol>   --coverage-goal-truth FULL   --coverage-world-truth FULL|SAMPLED   --sampling-scope "<when sampled>"   --sampling-basis "<when sampled>"   --residual-risk "<when sampled>"   --finding type:severity:summary
```

If the review passes, the workflow will record the latest reviewed subtask and recompute task-level `Task close-ready`.
Only when `Task close-ready = YES` may the main agent move workflow state toward archive and archive the task.

## Review style
- Use fresh context.
- On rereview, rebuild the full judgment from the current pack, approved plan, workflow, evidence, and sampled code first; only then use prior findings as a regression checklist.
- Lead with concrete findings and the smallest blocking delta.

## Do not
- do not fix code yourself
- do not archive directly
- do not let the main agent submit the reviewer verdict on your behalf
- do not expand scope while reviewing
- do not accept "only verify the last fix" as sufficient close-review scope
