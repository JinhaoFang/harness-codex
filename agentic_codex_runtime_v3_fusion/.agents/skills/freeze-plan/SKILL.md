---
name: freeze-plan
description: use when codex has already clarified user intent and grounded the task in the current codebase, and now needs to write or materially revise `.agentdocs/tasks/TASK_ID/plan.md` as goal truth before implementation.
---

# freeze-plan

Convert clarified, grounded understanding into a plan that can be reviewed independently.

This skill **does not** perform the DISCUSS loop.  
It freezes Goal truth after DISCUSS and world grounding are already good enough.

## Preconditions

Before using this skill, all of the following should already be true:

- `discuss-clarification` has reduced the task to a controlled set of known decisions
- the deliverable, observable effect, non-goals, and acceptance are clear enough to freeze
- user-side understanding and project-side understanding have both reached the DISCUSS 95% bar
- a short discuss summary has already been confirmed
- the terminal completion definition is locked (what counts as done, and what does not)
- must-preserve requirements and the remaining `You decide` space are explicit
- phase order, approval points, and delete-or-migrate conditions are explicit when relevant
- world grounding already identified real code paths, tests, reusable mechanisms, and constraints

If any of these are still weak, stop freezing and return to DISCUSS and/or `$world-grounding`.

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

Do not add workflow logging, review verdicts, or temporary clarification chatter.

## Plan rules

- Keep `plan.md` focused on what must be delivered, what effect must be visible, and under which constraints.
- Separate user-confirmed requirements, project/world constraints, and implementation latitude; do not blur `must preserve` with `you decide`.
- Freeze only decisions that are stable enough for review and implementation.
- If a point still requires user confirmation, keep it in `Open questions requiring escalation`; do not disguise it as a frozen decision.
- Put only real current paths, symbols, tests, existing docs / source materials, and compatibility constraints in world-grounded anchors.
- Keep write boundaries explicit.
- For staged migration / deletion / reclassification work, freeze phase order, approval points, review-before-action constraints, and deletion / migration guardrails explicitly.
- Make verification and evidence collection specific enough that a reviewer can prove completion.
- Make rollback explicit enough that a close reviewer can judge reversibility.
- Break work into the smallest reviewable subtasks; if a subtask cannot state `Goal / Expected effect / Preconditions / Write boundary / Verify / Review focus`, split it.

## Draft vs frozen

A draft `plan.md` may exist before the task is fully ready.  
That does **not** make it frozen Goal truth.

Before DISCUSS readiness is genuinely satisfied:

- do not treat the plan as final
- do not request `plan-review`
- do not refresh subtask packs for implementation entry
- do not move the workflow toward implementation

Only freeze when the task can survive independent review in fresh context.

## After drafting the plan

### If the plan still exposes unresolved ambiguity

- keep status as draft
- return to `discuss-clarification` and/or `$world-grounding`
- tighten the unclear parts before trying again

### If the plan is truly review-ready

Then and only then:

- save the updated `plan.md`
- refresh the relevant subtask pack(s):
  `python .codex/tools/agentctl.py refresh-pack --task-id <task-id> --subtask <subtask-id>`
- update workflow status:
  `python .codex/tools/agentctl.py update-current --task-id <task-id> --current-gate "Freeze Goal Truth" --allowed-next-action "plan-review" --active-subtask <subtask-id> --event "plan frozen after discuss summary and grounding; ready for plan review"`
- preflight before requesting an independent plan review:
  `python .codex/tools/agentctl.py check-gate --task-id <task-id> --action plan-review`

## Do not

- do not use this skill as a substitute for user clarification
- do not put workflow logs in `plan.md`
- do not put review verdicts in `plan.md`
- do not copy large code excerpts when a path reference is enough
- do not freeze speculative execution ideas or reviewer-to-be-validated hunches as Goal truth
- do not start implementation before independent plan review
