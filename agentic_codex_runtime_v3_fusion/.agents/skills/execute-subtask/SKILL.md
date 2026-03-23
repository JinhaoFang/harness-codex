---
name: execute-subtask
description: use when plan review has passed and codex needs to implement exactly one grounded subtask inside an explicit write boundary, then verify it and hand it back for review.
---

# execute-subtask

Implement one subtask and leave the task in a reviewable state.

## Role assumptions
- When this stage is executed by the `worker` role, start with `$subagent-bootstrap`.
- The parent agent should pass routing data such as task id, subtask id, objective, and required method overlays; the worker must rebuild the actual task context from `.agentdocs/*`.

## Preconditions
- `python .codex/tools/agentctl.py check-gate --task-id <task-id> --action implement` passes
- the active subtask pack is fresh

## Read order
1. active subtask pack
2. relevant `plan.md` section
3. relevant `workflow.md` section
4. the minimum code and tests needed to change behavior safely

## Execution rules
- Change only what is inside the write boundary.
- Prefer the smallest defensible change.
- Reuse existing mechanisms unless the plan explicitly requires a new path.
- Keep scope stable; escalate instead of silently expanding.
- If the parent prompt conflicts with the current pack, plan, workflow, or repo reality, stop and escalate instead of choosing the prompt.
- Do not delete, migrate, or reclassify existing materials outside the approved phase order, approval points, or deletion guardrails.
- Stop if the pack is stale, the plan is insufficient, or user intent changed.

## Method overlays
- This skill describes the implementation stage, not a single engineering method.
- If the subtask changes code-bearing behavior, the independent `$tdd` skill is mandatory for that implementation, while remaining decoupled from the stage definition itself.
- If branch / commit / PR traceability matters, follow repo guardrails and `$github-collaboration` rather than embedding those rules into the stage itself.

## Verification
Run the minimum real repository commands needed to verify the subtask.
Use `$evidence-capture` or call the controller directly after meaningful checks.
Return the changed files, verification commands, and evidence candidates clearly to the parent agent.

## After implementation
- refresh the subtask pack if material facts changed
- update workflow state when handing back for close review:
  `python .codex/tools/agentctl.py update-current --task-id <task-id> --current-gate "Implementation" --allowed-next-action "close-review" --active-subtask <subtask-id> --event "implementation ready for close review"`

## Do not
- do not perform reviewer duties
- do not modify plan intent without reopening planning
- do not claim completion without evidence
