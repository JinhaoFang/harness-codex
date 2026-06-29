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

Resume the **same logical Reviewer session**. Earlier Plan Review context preserves identified risks but does not make the plan true — re-ground on current truth and review the complete diff yourself.

1. Ground via `harness-ground` first: current repository truth, Work Unit progress, and GitHub integration state. Read what *is*, including any PR, review-comment, or CI change since Plan Review.
2. Enumerate **every** changed file with native Git, not from memory or the plan:

```bash
git diff <base_commit>..HEAD --stat   # the full set of changed files
git diff <base_commit>..HEAD          # the complete diff to review hunk by hunk
```

   `<base_commit>` is the Work Unit base recorded in `state.json`.

3. For **every** changed file and hunk, confirm it maps to an intended plan slice and that no bystander field, relation, or behavior was altered or damaged. Collateral damage to a non-target field (for example an existing DB relation or public symbol edited in the same file as the planned change) is the most common Close Review miss — check each hunk against the plan and do not stop once the planned deviations look correct. Then re-read current tests and fresh receipts and confirm the facts align with the planned direction.

Submit:

```bash
harnessctl request-review --id <WU-ID> --mode close \
  --reviewer-id <REVIEWER-ID> --reviewer-session <SAME-REVIEW-SESSION>
harnessctl check --id <WU-ID> --gate review --strict
```

Silent replacement is forbidden. Use explicit `reviewer-takeover` when a session is unrecoverable; takeover resets generation and requires Plan Review again. For high/critical risk, add a fresh specialist review or human gate while retaining the continuous primary Reviewer.

For Codex native reviewer orchestration, including binding and same-session Close Review, follow `docs/harness/codex-native-subagents.md`.
