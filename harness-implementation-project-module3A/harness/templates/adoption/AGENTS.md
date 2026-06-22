# Coding Agent Project Map

## Project facts

- Project: [one sentence]
- Runtime / stack: [fill]
- Build / test / lint entrypoints: [fill]
- High-risk areas: [fill]
- Local rules and architecture docs: [fill]

## Harness routing

This file is a short map, not the lifecycle manual or task-state store.

- Ambiguous or non-trivial request: use `$harness-clarify`; do not implement.
- Approved product intent: use `$harness-spec`; tracked Specs live in `docs/spec/<WU-ID>.md`.
- Technical design: use `$harness-plan`; local plans live in ignored `.harness/` runtime.
- After the plan is complete, use native Codex reviewer/worker subagents for Plan Review, implementation, and Close Review. Keep `harnessctl` for checks, session binding, lifecycle state, and final gates.
- Implementation: use `$harness-tdd`; only a controller-bound Worker may edit product code.
- Verification: use `$harness-evidence`; pass receipts come from `harnessctl verify`, not agent claims.
- Plan and Close Review: use the same logical `$harness-review` platform session.
- Git/GitHub collaboration: use `$harness-github`.
- Recovery: use `resume-session` while local runtime exists; use `reconstruct` when it was lost.

## Non-negotiable boundaries

- Before explicit Spec approval, product code must not be modified.
- Before Plan Review passes and the controller starts a Worker, product code must not be modified.
- Work only inside the approved write boundary; surface scope changes instead of expanding silently.
- Code/tests/runtime define current project truth. The tracked Spec defines desired intent. The local plan is an implementation hypothesis.
- Required evidence must run after relevant changes. Skipped evidence blocks completion.
- Reviewer is read-only and cannot fix the Worker's code or manufacture evidence.
- Dangerous, production, secret, billing, migration, deployment, or irreversible operations require model-external boundaries and accountable human approval.

## Minimal commands

```bash
harnessctl new --id <WU-ID> --title "..." --type feature --risk medium
harnessctl check --id <WU-ID> --gate spec --strict
harnessctl approve-spec --id <WU-ID> --approved-by human:<identity> --approval-ref <durable-ref>
# Complete the local plan, then ask Codex to spawn or resume native reviewer/worker subagents.
harnessctl check --id <WU-ID> --gate plan --strict
harnessctl route --id <WU-ID> --platform codex
harnessctl finalize-check --id <WU-ID> --strict
```

Detailed lifecycle guidance is in `docs/harness/`; for Codex native reviewer/worker orchestration, use `docs/harness/codex-native-subagents.md`. Deterministic behavior is in the controller, hooks, Git/CI, and platform permissions.
