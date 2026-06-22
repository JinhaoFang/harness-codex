---
name: harness-handoff
description: Generate a small local recovery view before session transfer or compaction. Use for long-running or blocked work; do not treat handoff as a tracked source of truth.
---

# Harness Handoff

Generate rather than manually maintain the handoff:

```bash
harnessctl handoff --id <WU-ID> --next-safe-action "<one concrete safe action>"
```

The handoff is local and untracked. It points to the tracked spec, local plan, Git snapshot, evidence logs, review track, blockers, and next action. A new session must re-read current code/diff and must not trust the handoff over repository truth.
