---
name: harness-github
description: Connect an approved Work Unit to Git branches, issues, commits, pull requests, CI, and human review without creating a second task ledger. Use when collaboration or integration leaves the local session.
---

# Harness GitHub

Git/GitHub are first-class execution and integration surfaces. They do not replace the tracked spec or controller-executed verification.

- Use one branch/worktree per implementation Work Unit.
- Name the branch with the Work Unit or issue id.
- Keep commits bounded and reviewable.
- Put rationale and observable behavior before trace metadata in issue/PR bodies.
- Link the tracked `docs/spec/<WU-ID>.md` when useful.
- Report exact verification commands and CI run links.
- Do not open implementation PRs before plan approval.
- Do not change reviewed implementation during integration without returning to build, verification, and close review.

The local `.harness` directory is intentionally untracked. After it is removed, reconstruct progress from the tracked spec, branch/commits/diff, issue/PR/CI state, and current code/tests.
