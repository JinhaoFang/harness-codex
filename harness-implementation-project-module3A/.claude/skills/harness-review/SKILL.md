---
name: harness-review
description: Perform Plan and Close Review on the same persistent logical platform session, directly inspecting repository truth, diff, tests, and controller evidence rather than builder narrative.
---

# Harness Review

Reviewer is read-only. Findings return to the Worker; Reviewer never silently patches the implementation and then approves its own new diff.

## Plan Review

Inspect the tracked Spec, local plan, current code/tests/runtime, scope, and risk. Reject ungrounded architecture, incomplete claim coverage, weak failure oracles, hidden scope expansion, or tests that merely certify the proposed implementation.

The platform adapter captures the real Reviewer session ID. Manual review uses:

```bash
harnessctl request-review --id <WU-ID> --mode plan \
  --reviewer-id <REVIEWER-ID> --reviewer-session <REVIEW-SESSION> \
  --planner-id <PLANNER-ID> --planner-session <PLANNER-SESSION>
```

## Close Review

Resume the **same logical Reviewer session** and re-ground from the current repository, complete diff, tests, and fresh receipts. Earlier Plan Review context preserves identified risks but does not make the plan true.

```bash
harnessctl request-review --id <WU-ID> --mode close \
  --reviewer-id <REVIEWER-ID> --reviewer-session <SAME-REVIEW-SESSION>
harnessctl check --id <WU-ID> --gate review --strict
```

Silent replacement is forbidden. Use explicit `reviewer-takeover` when a session is unrecoverable; takeover resets generation and requires Plan Review again. For high/critical risk, add a fresh specialist review or human gate while retaining the continuous primary Reviewer.

For Codex native reviewer orchestration, including binding and same-session Close Review, follow `docs/harness/codex-native-subagents.md`.
