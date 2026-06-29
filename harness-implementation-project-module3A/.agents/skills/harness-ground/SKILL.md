---
name: harness-ground
description: Ground any spec, plan, review, or implementation turn in current truth — repository code/tests, Work Unit progress, and GitHub integration state — before acting. Use before asking factual questions, trusting summaries, or starting any role turn (before harness-clarify).
---

# Harness Ground

Every role — conductor, reviewer, worker — grounds on current truth **before** each work turn. Do not start discussing, writing a spec/plan, reviewing, or implementing until you have synced the sources below. Grounding reads what *is*, not what was planned or what a prior summary claimed.

## Sync before acting

These two sources are easy to skip and are the most common cause of working from stale assumptions:

1. **Progress** — run `harnessctl brief --id <WU-ID>` (or read `.harness/work-units/active/<WU-ID>/state.json`): current status, current role, base/head commit, next safe action, latest evidence receipts, the last review verdict, and the review-track generation. Know where the Work Unit stands and what the prior role actually produced before adding to it.
2. **GitHub / integration truth** — run `harnessctl github-sync --id <WU-ID>` and read the linked PR/issue thread, CI check results, review comments, and recent integration commits. In team collaboration repository truth lives partly on GitHub; surface a teammate's PR, a failing check, or a review comment the same way you surface a local code change. See `harness-github` for the binding and delivery-gate mechanism.

## Read in this order (repository truth)

1. `docs/spec/<WU-ID>.md` for approved desired behavior.
2. Nearby project instructions and local rules.
3. Current implementation and public interfaces.
4. Tests that define or contradict current behavior.
5. Runtime/config/CI surfaces needed for the claim.
6. Only the ADRs/docs explicitly relevant to touched areas.

Record concise pointers, not copied content. Surface code/docs/test/integration conflicts. Do not promote a proposed design into current project truth before it is implemented and verified.
