---
name: world-grounding
description: use when codex needs to ground a task or a proposed plan in the current codebase, tests, configuration, and reusable mechanisms before freezing goal truth or approving changes.
---

# world-grounding

Ground the task in the current world before anyone freezes a plan or judges a large change.

This skill answers: **what is true in the repo right now?**  
It does **not** answer: **what did the user ultimately mean?**

## Read first

Read the minimum needed:

- the current task request or user ask
- `.agentdocs/tasks/<task-id>/workflow.md` if it exists
- `.agentdocs/tasks/<task-id>/plan.md` if it already exists
- the minimum code, tests, config, docs, and runtime artifacts needed to establish real anchors

If user intent is still ambiguous after a small amount of repo reading, do **not** silently infer the missing intent from the codebase.  
Return the ambiguity to `discuss-clarification`.

## Questions to answer

- What is the promised deliverable and observable effect in concrete repo terms?
- What is the real entry path?
- Which files, symbols, routes, jobs, services, or commands actually control this behavior?
- Which existing tests or checks already cover part of the task?
- Which existing docs, legacy materials, or source artifacts must be reviewed before any migration, deletion, or reclassification decision?
- Which existing mechanisms can be reused or lightly extended?
- Which constraints in the real codebase will shape the plan?
- Which stage order, approval points, or review-before-action constraints are implied by the current world?
- Which unresolved questions still require user clarification before Goal truth can be frozen?

## Operating rules

- Prefer targeted file reads, search, and existing tests over broad scans.
- Cite concrete paths and symbols, not vague summaries.
- Keep findings concise and directly useful for planning or review.
- Treat code, tests, configuration, and runtime outputs as world truth.
- Treat existing docs / legacy materials as world truth only when they already exist in the repo today.
- Do not use current-task `plan.md`, `workflow.md`, `reviews/*.json`, `evidence/*.json`, `subtask-packs/*.md`, or proposed future outputs as world-grounded anchors.
- Do not silently turn a stale summary into truth.
- Do not let strong repo grounding masquerade as user-intent readiness.

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

If repo reality is good but user intent is not, explicitly say so.

## Handoff rule

- If repo truth is the missing piece, hand off toward `freeze-plan`.
- If user-intent ambiguity is still the missing piece, hand back to `discuss-clarification`.
- If both are still weak, say both are weak; do not pretend one substitutes for the other.

## Do not

- do not write a thick recap
- do not freeze goals on your own
- do not edit business code
- do not replace `plan.md` with a grounding memo
- do not treat “the repo seems to imply X” as permission to override unclear user intent
