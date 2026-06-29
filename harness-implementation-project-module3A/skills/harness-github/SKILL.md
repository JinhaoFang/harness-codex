---
name: harness-github
description: Bind an approved Work Unit to Git branches, issues, pull requests, CI checks, and human integration without creating a second task ledger.
---

# Harness GitHub

> `harness-ground` consults this GitHub state when grounding before any role turn; this skill owns the binding and delivery-gate mechanism, `harness-ground` owns the read/sync discipline.

Git/GitHub are execution and integration truth. They do not replace the tracked Spec, controller evidence, or Close Review.

- Use one implementation Work Unit per branch/worktree and keep commits behavior-bounded and reviewable.
- Link issue/PR references and exact required check names through the controller:

```bash
harnessctl delivery-link \
  --id <WU-ID> --issue <ISSUE> --branch <BRANCH> --pull-request <PR> \
  --required-check test --required-check lint
harnessctl github-sync --id <WU-ID>
harnessctl check --id <WU-ID> --gate delivery --strict
```

- The delivery gate verifies PR HEAD equals local HEAD and each declared check is successful.
- Do not treat a generic green CI run as evidence for a claim it does not cover.
- Any implementation change after Close Review returns to evidence and review.
- `.harness/` stays untracked; recovery uses the tracked Spec, Git/GitHub, and current code.
