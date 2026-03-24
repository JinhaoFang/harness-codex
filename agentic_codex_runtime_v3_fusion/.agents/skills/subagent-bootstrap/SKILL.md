---
name: subagent-bootstrap
description: use when a spawned subagent needs to rebuild task context from runtime truth instead of trusting the parent agent's recap, so role behavior stays stable across fresh sessions and rereviews.
---

# subagent-bootstrap

Re-enter the task from runtime truth before doing role-specific work.

## Purpose

This skill keeps subagents role-driven instead of prompt-driven.
The parent agent should route the work.
The subagent should rebuild the context.

## Minimal handoff from the parent agent

The parent agent should pass only the minimum routing data:

- role
- task id
- subtask id when work is subtask-scoped
- review request id when the role must submit a review
- the concrete objective or question for this run
- optional extra focus or required method overlays such as `tdd`

If these identifiers are missing, stop and ask for them instead of guessing.

## Bootstrap order

1. active subtask pack when one exists
2. relevant `plan.md` section
3. relevant `workflow.md` state
4. latest same-type review or evidence refs only when they matter to this role
5. minimum current code, tests, config, and runtime artifacts needed to judge or change reality

```text
parent handoff
    |
    v
task/subtask identifiers
    |
    v
subtask pack -> plan/workflow -> latest refs -> world truth
    |
    v
role-specific work
```

## Truth split

- `.agentdocs/*` synchronizes task scope, stage, approvals, and latest refs.
- Code, tests, config, logs, and runtime behavior remain world truth.
- The parent prompt is a routing hint, not an authority that can replace either truth layer.

## Re-review discipline

For any rereview after fixes:

```text
re-review = full current review + prior findings recheck
re-review != prior findings only
```

- Previous findings become a regression checklist after current truth is re-read.
- Parent-requested focus areas may increase attention, but must not shrink mandatory review coverage.
- If the parent asks for delta-only review, refuse that narrowing and perform the full role review.

## Role overlays

- `explorer`: use `$world-grounding`; `.agentdocs` provides scope and constraints, not world anchors.
- `worker`: use `$execute-subtask`; for code-bearing development subtasks also apply `$tdd`.
- `plan_reviewer`: use `$plan-review`; every review is a fresh full-scope judgment.
- `close_reviewer`: use `$close-review`; every review is a fresh full-scope judgment.

## Output contract

Return only what the parent agent needs next:

- materials accessed
- changed files or findings
- verification run or remaining blockers
- next legal action

## Do not

- do not trust a stale parent recap over current runtime truth
- do not invent missing task ids, request ids, or write boundaries
- do not let previous reviewer findings become the only scope on rereview
