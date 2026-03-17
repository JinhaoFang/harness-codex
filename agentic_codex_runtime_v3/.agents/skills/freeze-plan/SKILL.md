---
name: freeze-plan
description: use when codex has already clarified intent and grounded the task in the current codebase, and now needs to write or materially revise `.agentdocs/tasks/TASK_ID/plan.md` as goal truth before implementation.
---

# freeze-plan

Convert grounded understanding into a plan that can be reviewed independently.

## Preconditions
- the deliverable, observable effect, non-goals, and acceptance are clear enough to draft a plan
- user-side understanding and project-side understanding have both reached the DISCUSS 95% bar
- the terminal completion definition is locked (what counts as done, and what does not)
- must-preserve requirements and the remaining `You decide` space are explicit
- world grounding already identified real code paths, tests, and reusable mechanisms

## Write only goal truth
Write these sections in `plan.md`:
- Goal
- Non-goals
- Acceptance
- Requirement split
- World-grounded anchors
- Decision freeze
- Boundaries
- Verification
- Subtasks
- Rollback / migration

## Plan rules
- Keep `plan.md` focused on what must be delivered, what effect must be visible, and under which constraints.
- Separate user-confirmed requirements, project/world constraints, and implementation latitude; do not blur `must preserve` with `you decide`.
- Do not freeze speculative execution ideas or reviewer-to-be-validated hunches as Goal truth.
- Put only real current paths, symbols, tests, existing docs / source materials, and compatibility constraints in world-grounded anchors.
- Keep write boundaries explicit.
- For staged migration / deletion / reclassification work, freeze phase order, approval points, review-before-action constraints, and deletion / migration guardrails explicitly.
- Make verification and evidence collection specific enough that a reviewer can prove completion.
- Make rollback explicit enough that a close reviewer can judge reversibility.
- Break work into the smallest reviewable subtasks; if a subtask cannot state `Goal / Expected effect / Preconditions / Write boundary / Verify / Review focus`, split it.

## After drafting the plan
- If you are still clarifying intent, you may draft a partial plan to surface questions, but do not treat it as frozen:
  - do not refresh the subtask pack
  - do not request plan review
  - do not move workflow state forward
- refresh the active subtask pack:
  `python .codex/tools/agentctl.py refresh-pack --task-id <task-id> --subtask <subtask-id>`
- move workflow state forward only after a refreshed pack exists:
  `python .codex/tools/agentctl.py update-current --task-id <task-id> --current-gate "Freeze Goal Truth" --allowed-next-action "plan-review" --active-subtask <subtask-id> --event "plan drafted and pack refreshed; ready for plan review"`
- preflight before requesting an independent plan review:
  `python .codex/tools/agentctl.py check-gate --task-id <task-id> --action plan-review`

## Do not
- do not put workflow logs in `plan.md`
- do not put review verdicts in `plan.md`
- do not copy large code excerpts when a path reference is enough
- do not start implementation before independent plan review
