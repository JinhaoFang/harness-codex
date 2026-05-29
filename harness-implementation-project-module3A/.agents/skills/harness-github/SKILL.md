---
name: harness-github
description: Use GitHub issues, branches, commits, and pull requests as the collaboration surface for Work Units. Use when work should be reviewable outside the chat, mapped to an issue, split across PRs, or integrated with CI and human review.
---

# Harness GitHub

GitHub is collaboration and audit surface, not completion authority. Work Unit Contract, repo state, evidence receipts, review verdicts, and waivers remain the sources of truth.

Do not use one GitHub pattern for every task. Choose the repo/GitHub footprint by task type, risk, collaboration need, and artifact retention need.

## When to use

Use this skill only when GitHub materially helps collaboration:

- a Work Unit should be mirrored to an issue;
- a PR needs a body that connects diff, evidence, and review;
- a commit should preserve traceability to a Work Unit or issue;
- CI or human reviewers need concise external context.

Do not require GitHub for every local task.


## Task-type operating model

| Task class | Work Unit in repo | GitHub issue | PR / CI evidence | Artifact retention |
|---|---|---|---|---|
| trivial docs/comment | no | no | optional | final note |
| low local bugfix | optional | optional | PR evidence note | short-lived logs |
| medium multi-file or user-visible behavior | yes | recommended | PR links receipts and CI artifacts | retain receipts/review summaries |
| high auth/billing/security/migration | yes, locked | yes | protected PR with human/reviewer gate | retain receipts, waivers, rollback notes |
| critical production/data/compliance | yes, audit-grade | yes | protected PR and explicit approval | retain audit artifacts outside noisy repo paths when large |

Commit stable harness implementation, not transient runtime noise. Keep large command logs, screenshots, traces, and raw transcripts in CI artifacts or temporary storage unless audit policy requires committing them.

## Branch / worktree

Name branches with the Work Unit or issue ID:

```text
wu/<WU-ID>-short-topic
issue-<number>-short-topic
```

Create GitHub-facing artifacts only after the local task shape is grounded:

- create or update the Work Unit first;
- lock the contract and pass the required plan review for medium+ work;
- then create the issue/branch/PR surface that mirrors that reviewed plan.

Do not open GitHub issue or branch state as a substitute for clarification, spec, or plan review. For trivial or low-risk local work, GitHub remains optional.

## Issue body

The issue body should contain or link the Work Unit Contract. Keep it stable and reviewable; do not turn comments into a second task ledger.

```markdown
## Background
- What problem or change triggered this Work Unit.

## Goal
- The grounded deliverable.
- The observable effect.

## Scope
### In scope
- Allowed or likely changed areas.

### Out of scope
- Non-goals and forbidden paths or behaviors.

## Acceptance criteria
- [ ] Concrete, externally checkable result.
- [ ] Concrete, externally checkable result.

## Required evidence
- EV-*: `<command or artifact expected>`

## Risk / approval notes
- Risk level:
- Human approval required before:

## Runtime refs
- Work Unit Contract: `.harness/work-units/active/<WU-ID>/contract.md`
- Evidence: `.harness/work-units/active/<WU-ID>/evidence/receipts.jsonl`
```

For slice issues derived from a larger PRD, add:

```markdown
## Parent PRD
#<prd-issue-number>

## Blocked by
- None - can start immediately
```

## Commit body

Prefer one verified slice per commit. The commit subject should be short and conventional when the project uses that style:

```text
feat: add bounded Work Unit scope gate
fix: reject stale evidence receipts
test: cover committed out-of-bounds diff
```

Use the body for traceability and verification, not a long narrative:

```text
Work Unit: WU-123
Refs: #123
Evidence: EV-SCOPE-COMMITTED via `python3 -m unittest ...`
Risk: low
```

Use `Closes #123` only when this commit or PR actually completes the issue. Otherwise use `Refs: #123`.

## PR body

```markdown
## Summary
- What changed, in 2-4 bullets.

## Work Unit
- Contract: `.harness/work-units/active/<WU-ID>/contract.md`
- Issue: Refs #123

## Scope check
- In boundary: `<paths>`
- Out of bounds touched: `none` or explain amendment/waiver

## Evidence
- EV-*: `<receipt-id>` — `<command>` — pass/fail/skipped

## Skipped checks / waivers
- None
- Or: `<waiver-id>` for `<EV-ID>`, approved by `human:<owner>`

## Risk notes
- Risk level:
- Rollback/reopen path:

## Review
- Requested reviewer(s):
- Close review verdict: `<review-id>` or pending
```

## Progress comment

When updating an issue or PR, mirror only current runtime facts:

```markdown
## Progress
- Completed: ...
- Verified by: `<receipt-id>` / `<real command>`
- Blocked by: ...
- Next safe action: ...
```

## Do not

- Do not merge based only on agent summary, issue state, or green-looking local output.
- Do not let GitHub issue text override the current repository, Work Unit Contract, or evidence receipts.
- Do not close issues from an agent claim without fresh evidence or an explicit waiver.
- Do not create a second lifecycle ledger in comments.
