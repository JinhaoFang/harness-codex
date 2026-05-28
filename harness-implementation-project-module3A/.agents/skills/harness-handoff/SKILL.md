---
name: harness-handoff
description: Generate a recoverable handoff from authoritative artifacts. Use when work crosses a session boundary, becomes blocked, needs reviewer transfer, needs worker/reviewer subagent transfer, or is ready to archive with a no-next-step reason.
---

# Harness Handoff

Handoff is a recovery artifact derived from contract, state, diff, evidence, review, and blockers. It is not a chat summary.

```bash
python3 harness/cli/harnessctl.py handoff --id <WU-ID> --next-safe-action "<one safe action>"
```

Include:

- Work Unit ID;
- current objective and scope;
- state;
- branch, HEAD, diff hash;
- changed files;
- latest evidence;
- known failures and blockers;
- open questions;
- next safe action;
- rollback or reopen path.

Do not archive long-running work without a handoff or explicit no-next-step reason. For a terminal no-next-step archive, use `harnessctl archive --no-next-step-reason "<reason>"` after verification and review gates pass.
