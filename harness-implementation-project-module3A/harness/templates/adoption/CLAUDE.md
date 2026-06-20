# Claude Code Project Map

## Project facts

- Project: [one sentence]
- Runtime / stack: [fill]
- Build / test / lint entrypoints: [fill]
- High-risk areas: [fill]
- Local rules and architecture docs: [fill]

## Harness routing

Keep this file short. It routes Claude to skills and controller commands; it does not hold active state.

- Use `harness-clarify` for ambiguous or non-trivial work.
- Use `harness-spec` to create and approve `docs/spec/<WU-ID>.md`.
- Use `harness-plan` to create the local `.harness/.../plan.md` and request plan review.
- Start a separate worker only after plan review passes; use `harness-tdd` for implementation.
- Use `harness-evidence`; only `harnessctl verify` creates controller-observed pass receipts.
- Reuse one `harness-review` reviewer identity from plan review through close review.
- Use `harness-github` for issues, branches, PRs, CI, and human review.
- Use `harness-handoff` before handover; after a local handoff/blocker, use `harnessctl resume-work`; if `.harness` is absent, rebuild it with `harnessctl resume` from the tracked spec, Git/GitHub, and current code.

## Boundaries

- Do not modify product code before spec approval, plan approval, and `start-work`.
- Edit only paths inside the approved write boundary.
- Code/tests/runtime are current project truth; the spec is desired intent; the local plan is not authoritative project documentation.
- Skipped evidence never passes. Produce it, materially revise and reapprove the spec, or leave the task blocked.
- Reviewer is read-only. Findings return to the worker.
- Use permissions, hooks, CI, branch protection, and human approval for dangerous or high-risk operations.

## Commands

```bash
python3 harness/cli/harnessctl.py new --id <WU-ID> --title "..." --type feature --risk medium
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate spec --strict
python3 harness/cli/harnessctl.py approve-spec --id <WU-ID> --approved-by human:<identity> --approval-ref <durable-ref>
python3 harness/cli/harnessctl.py request-review --id <WU-ID> --mode plan --reviewer-id <REVIEWER-ID> --reviewer-session <REVIEW-SESSION> --planner-id <PLANNER-ID> --planner-session <PLANNER-SESSION>
python3 harness/cli/harnessctl.py submit-review --id <WU-ID> --mode plan --request-id <REQUEST-ID> --decision PASS --reviewer-id <REVIEWER-ID> --reviewer-session <REVIEW-SESSION>
python3 harness/cli/harnessctl.py start-work --id <WU-ID> --builder-id <ID> --builder-session <SESSION>
python3 harness/cli/harnessctl.py verify --id <WU-ID> --claim <EV-ID>
python3 harness/cli/harnessctl.py finalize-check --id <WU-ID> --strict
```

Detailed lifecycle guidance is in `docs/harness/`.
