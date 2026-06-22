# Claude Code Project Map

## Project facts

- Project: [one sentence]
- Runtime / stack: [fill]
- Build / test / lint entrypoints: [fill]
- High-risk areas: [fill]
- Local rules and architecture docs: [fill]

## Harness routing

Keep this file short. It routes Claude to skills and controller commands; it does not hold active state.

- Use `harness-clarify` for ambiguous or non-trivial work and stop at explicit Spec approval.
- Use `harness-spec` for `docs/spec/<WU-ID>.md` and `harness-plan` for the ignored local plan.
- After the plan is complete, call `harnessctl advance`; do not pause between normal delivery phases.
- Use `harness-tdd` in a separate Worker and `harness-evidence` for controller-observed checks.
- Reuse one logical `harness-review` session from Plan Review through Close Review.
- Use `harness-github` for issue/branch/PR/CI integration.
- Use `resume-session` while `.harness` exists; use `reconstruct` after local runtime loss.

## Boundaries

- Do not modify product code before Spec approval, Plan Review, and controller Worker start.
- Edit only paths inside the approved write boundary.
- Code/tests/runtime are current project truth; the Spec is desired intent; the local plan is not authoritative project documentation.
- Skipped evidence never passes. Produce it, materially revise/reapprove the Spec, or remain blocked.
- Reviewer is read-only. Findings return to the Worker.
- Use permissions, sandbox, hooks, CI, branch protection, and human approval for high-risk operations.

## Commands

```bash
harnessctl new --id <WU-ID> --title "..." --type feature --risk medium
harnessctl check --id <WU-ID> --gate spec --strict
harnessctl approve-spec --id <WU-ID> --approved-by human:<identity> --approval-ref <durable-ref>
# Complete the local plan, then continue automatically.
harnessctl advance --id <WU-ID> --platform claude \
  --reviewer-id <REVIEWER-ID> --planner-id <PLANNER-ID> \
  --planner-session <PLANNER-SESSION> --builder-id <WORKER-ID>
harnessctl finalize-check --id <WU-ID> --strict
```

Detailed lifecycle guidance is in `docs/harness/`.
