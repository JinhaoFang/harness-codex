---
name: close-review
description: use when implementation evidence exists and codex needs an independent, fresh-context judgment about delivery readiness, drift from the approved plan, and evidence traceability before archive.
---

# close-review

Review delivery readiness with fresh context.

## Role assumptions
Use this skill from the `close_reviewer` role or in an equivalent read-only review context.

## Preconditions
`python .codex/tools/agentctl.py check-gate --task-id <task-id> --action close-review` passes.

## Read first
- active subtask pack
- approved `plan.md`
- current `workflow.md`
- relevant evidence JSON files
- source materials when the task migrated, deleted, reorganized, or reclassified existing materials
- a minimal sample of changed code or runtime artifacts

## Review questions
- Does the delivered work drift from the approved plan?
- Are tests and behavior checks traceable from evidence to code paths?
- For migration / deletion / reclassification tasks, can the result still be traced back to source materials and approved deletion / migration guardrails?
- Is there an unnecessary new path where reuse should have been used?
- Is anything missing that would block a safe close?

## Structured writeback

```bash
python .codex/tools/agentctl.py write-review   --task-id <task-id>   --subtask <subtask-id>   --review-type close   --decision PASS|CHANGES_REQUIRED|REJECT   --plan-ref .agentdocs/tasks/<task-id>/plan.md   --task-requirement <workflow-or-user-constraint-ref>   --code-path <path>   --test <path>   --evidence-ref <evidence-json>   --material-accessed <path-or-symbol>   --coverage-goal-truth FULL   --coverage-world-truth FULL|SAMPLED   --sampling-scope "<when sampled>"   --sampling-basis "<when sampled>"   --residual-risk "<when sampled>"   --finding type:severity:summary
```

If the review passes, the main agent may move workflow state toward archive and then archive the task.

## Do not
- do not fix code yourself
- do not archive directly
- do not expand scope while reviewing
