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

If GitHub collaboration is added after implementation has already passed local review, classify the amendment precisely instead of reopening the whole implementation loop:

```bash
python3 harness/cli/harnessctl.py amend --id <WU-ID> --field required_evidence --impact collaboration_only --reason "Add GitHub collaboration evidence" --summary "Add issue/PR publication evidence; implementation scope unchanged"
python3 harness/cli/harnessctl.py evidence --id <WU-ID> --claim <EV-GITHUB> --type manual --result pass --command "gh issue view <N> --json number,title,state,url,body" --artifact-uri <ISSUE-OR-PR-URL>
python3 harness/cli/harnessctl.py request-review --id <WU-ID> --mode publication --reviewer-role reviewer-agent
```

Do not rerun implementation evidence or full close review unless code, scope, risk, or behavior changed.

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

Use the body for quick human understanding first, then traceability and verification. Do not make readers open evidence receipts or the diff just to understand what changed.

```text
Summary:
- Added the bounded scope gate for committed and uncommitted changes.
- Updated controller tests for out-of-bounds committed paths.

Work Unit: WU-123
Refs: #123
Risk: low

Verification:
- EV-SCOPE-COMMITTED ev-... via `python3 -m unittest ...`

Reviews:
- Plan: review-...
- Close: review-...
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

## Local archive after PR publication

Do not keep a local Work Unit active only because a PR is waiting for merge. The local Work Unit can be archived after implementation, evidence, close review, and PR/update publication are complete. Use a clear no-next-step reason, for example:

```bash
python3 harness/cli/harnessctl.py archive --id <WU-ID> --no-next-step-reason "Local work complete; PR #123 is awaiting remote review/merge."
```

If PR review or merge later requires changes, reopen the archived Work Unit or create a follow-up Work Unit with the new scope. Do not let remote PR waiting state keep `.harness/current` pointing at completed local work.

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
