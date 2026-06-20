# Coding Agent Project Map

## Project facts

- Project: [one sentence]
- Runtime / stack: [fill]
- Build / test / lint entrypoints: [fill]
- High-risk areas: [fill]
- Local rules and architecture docs: [fill]

## Harness routing

This file is a short map, not the lifecycle manual or task-state store.

- Ambiguous or non-trivial request: use `$harness-clarify`.
- Approved product intent: use `$harness-spec`; tracked specs live in `docs/spec/<WU-ID>.md`.
- Technical design: use `$harness-plan`; local plans live in ignored `.harness/` runtime.
- Implementation: start only after the required plan review gate passes, then use `$harness-tdd`.
- Verification: use `$harness-evidence`; pass receipts are created by `harnessctl verify`, not agent claims.
- Plan and close review: use the same `$harness-review` track and reviewer identity.
- Git/GitHub collaboration: use `$harness-github`.
- Cross-session recovery: use `$harness-handoff`; use `harnessctl resume-work` after a local handoff/blocker; when local runtime is absent, run `harnessctl resume` and rebuild from the tracked spec, Git/GitHub, and current code.

## Non-negotiable boundaries

- Before `approve-spec`, product code must not be modified.
- Before plan review passes and `start-work` runs, product code must not be modified.
- Work only inside the approved spec write boundary; surface scope changes instead of expanding silently.
- Repository code, tests, and runtime define current project truth. The tracked spec defines desired intent. The local plan is an implementation hypothesis.
- Required evidence must actually run after the relevant implementation change. A skipped check blocks completion; revise and reapprove the spec when the evidence contract must change.
- Reviewer is read-only and must not fix the worker's code or manufacture evidence.
- Dangerous, production, secret, billing, migration, deployment, or irreversible operations require platform permissions and accountable human approval.

## Minimal commands

```bash
python3 harness/cli/harnessctl.py new --id <WU-ID> --title "..." --type feature --risk medium
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate spec --strict
python3 harness/cli/harnessctl.py approve-spec --id <WU-ID> --approved-by human:<identity> --approval-ref <durable-ref>
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate plan --strict
python3 harness/cli/harnessctl.py request-review --id <WU-ID> --mode plan --reviewer-id <REVIEWER-ID> --reviewer-session <REVIEW-SESSION> --planner-id <PLANNER-ID> --planner-session <PLANNER-SESSION>
python3 harness/cli/harnessctl.py submit-review --id <WU-ID> --mode plan --request-id <REQUEST-ID> --decision PASS --reviewer-id <REVIEWER-ID> --reviewer-session <REVIEW-SESSION>
python3 harness/cli/harnessctl.py start-work --id <WU-ID> --builder-id <ID> --builder-session <SESSION>
python3 harness/cli/harnessctl.py verify --id <WU-ID> --claim <EV-ID>
python3 harness/cli/harnessctl.py finalize-check --id <WU-ID> --strict
```

Detailed lifecycle guidance is in `docs/harness/`; deterministic behavior is in `harness/cli` and hooks.
