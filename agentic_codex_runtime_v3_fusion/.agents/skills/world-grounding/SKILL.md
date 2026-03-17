---
name: world-grounding
description: use when codex needs to ground a task or a proposed plan in the current codebase, tests, configuration, and reusable mechanisms before freezing goal truth or approving changes.
---

# world-grounding

Ground the task in the current world before anyone freezes a plan or judges a large change.

## Read first
- the current task request or user ask
- `.agentdocs/tasks/<task-id>/workflow.md` if it exists
- `.agentdocs/tasks/<task-id>/plan.md` if it already exists
- the minimum code, tests, config, and runtime artifacts needed to answer these questions

## Questions to answer
- What is the promised deliverable and observable effect in concrete repo terms?
- What is the real entry path?
- Which files, symbols, routes, jobs, services, or commands actually control this behavior?
- Which existing tests or checks already cover part of the task?
- Which existing docs, legacy materials, or source artifacts must be reviewed before any migration, deletion, or reclassification decision?
- Which existing mechanisms can be reused or lightly extended?
- Which constraints in the real codebase will shape the plan?
- Which stage order, approval points, or review-before-action constraints are implied by the task and current world?
- Which unresolved questions or requirement ambiguities still block freezing goal truth?

## Operating rules
- Prefer targeted file reads, search, and existing tests over broad scans.
- Cite concrete paths and symbols, not vague summaries.
- Keep findings concise and directly useful for planning or review.
- Treat code, tests, configuration, and runtime outputs as world truth.
- Treat existing docs / legacy materials as world truth only when they already exist in the repo today.
- Do not use current-task `plan.md`, `workflow.md`, `reviews/*.json`, `evidence/*.json`, `subtask-packs/*.md`, or proposed future outputs as world-grounded anchors.
- Do not silently turn a stale summary into truth.

## Output
Return a short grounded summary with:
- deliverable / observable effect in repo terms
- key entry points
- key symbols or interfaces
- existing tests and checks
- existing docs / source materials that must be preserved, migrated, or reviewed before deletion
- reusable mechanisms
- constraints that must appear in the plan
- unresolved questions that still require DISCUSS

## Do not
- do not write a thick recap
- do not freeze goals on your own
- do not edit business code
- do not replace `plan.md` with a grounding memo
