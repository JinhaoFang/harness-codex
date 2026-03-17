---
name: refresh-subtask-pack
description: use when codex needs a fresh, minimal entry point for a subtask before implementation or review, or after planning, evidence, or workflow state changed in a way that could make the existing pack stale.
---

# refresh-subtask-pack

Regenerate the active subtask digest from source truths.

## When to refresh
- after drafting or materially revising `plan.md`
- before implementation starts
- before an independent review starts
- after a significant evidence update changes what a reviewer should look at
- after reopening work
- after Discuss / workflow constraints materially change in a way that affects phase order, approval points, source materials, or deletion guardrails

## Command

```bash
python .codex/tools/agentctl.py refresh-pack   --task-id <task-id>   --subtask <subtask-id>   --plan-ref .agentdocs/tasks/<task-id>/plan.md   --workflow-ref .agentdocs/tasks/<task-id>/workflow.md
```

Add `--evidence-ref <path>` when a specific evidence item should be surfaced.

## Pack rules
- treat the pack as a derived view
- prefer references over long copied text
- keep only the minimum material needed for the current subtask
- refresh instead of manually editing a stale digest when possible
