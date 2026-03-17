---
name: session-recovery
description: use when codex resumes interrupted work, hands a task across sessions, or needs a disciplined recovery check before continuing implementation or review. this skill absorbs harness-style recovery primitives without introducing separate state files.
---

# session-recovery

Resume work from runtime truth instead of inventing a second progress ledger.

## Read order
1. `workflow.md`
2. `plan.md`
3. active subtask pack (if present)
4. latest review/evidence refs
5. the minimum changed code/tests needed to confirm reality

## Recovery checklist
- confirm the current gate and allowed next action still match reality
- check whether the active subtask pack is stale
- check whether user intent or source materials changed
- confirm the latest review/evidence refs still exist and still matter
- confirm the repo state is safe before new writes

## Recovery actions
### If truth is still current
- refresh the pack if needed
- append a minimal resume event
- continue from the existing gate

### If truth is stale
- stop implementation
- route back to the smallest correct earlier gate
- use `$reopen-fix` when archived work or failed review must be reopened

## Useful commands
```bash
python .codex/tools/agentctl.py validate-refs --task-id <task-id>
python .codex/tools/agentctl.py check-gate --task-id <task-id> --action implement
python .codex/tools/agentctl.py refresh-pack --task-id <task-id> --subtask <subtask-id>
python .codex/tools/agentctl.py update-current --task-id <task-id> --event "session resumed after recovery check"
```

## Design boundary
- do not create `harness-tasks.json`
- do not create `harness-progress.txt`
- do not persist thick session history
- use minimal events plus existing review/evidence instead
