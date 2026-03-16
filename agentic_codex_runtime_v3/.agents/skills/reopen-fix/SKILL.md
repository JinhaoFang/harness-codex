---
name: reopen-fix
description: use when scope changed, a review failed, an archived task must resume, or stale truth means the task needs to be reopened and routed back to the correct gate before more implementation happens.
---

# reopen-fix

Reopen work deliberately instead of silently drifting.

## Typical triggers
- user changed goal, scope, or acceptance
- plan review returned blocking changes
- close review found drift or missing verification
- an archived task needs more work
- fresh grounding shows the current plan or pack is stale

## Commands
If the task is archived:

```bash
python .codex/tools/agentctl.py reopen   --task-id <task-id>   --trigger "scope-change|review-fail|world-drift|other"   --reason "short reason"
```

Then move workflow state explicitly:

```bash
python .codex/tools/agentctl.py update-current   --task-id <task-id>   --current-gate "Ground in World"   --allowed-next-action "Freeze Goal Truth"   --active-subtask <subtask-id>   --recovery-needed YES   --trigger "scope-change|review-fail|world-drift|other"   --exit-condition "refresh plan and pack, then re-run review"   --event "task reopened for fix"
```

## Rules
- route back to the smallest correct earlier gate
- preserve traceability instead of overwriting history
- refresh the pack after the new plan or evidence changes
- do not continue implementation on stale assumptions
