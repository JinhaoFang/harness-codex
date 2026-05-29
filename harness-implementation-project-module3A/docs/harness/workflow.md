# Workflow Contract

## 1. Clarify

The agent should not start implementation while essential intent, scope, success, or risk questions are unresolved. Ask the smallest number of questions needed to freeze the Work Unit.

If the task is time-sensitive or the user asks for immediate action, proceed with explicit assumptions and mark them in the contract.

## 2. Specify

Create or update a Work Unit Contract. The contract is the shared truth for user intent and scope. Execution plans may change; the contract should not drift silently.

Gate:

```bash
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate spec --strict
python3 harness/cli/harnessctl.py lock --id <WU-ID> --status ready
```

For non-trivial work, unresolved open questions, placeholders, missing write boundary, missing required evidence, or missing stop conditions block lock/readiness. After lock, changes to intent, scope, risk, required evidence, success criteria, or stop conditions must be recorded with `harnessctl amend`; otherwise readiness/running transitions are blocked. Re-run plan review only when the amendment changes the plan, implementation boundary, evidence plan, risk, success criteria, or user intent. Do not force a new review for lifecycle-only corrections that do not affect implementation sufficiency.

## 3. Route context

Use the project map first. Then read only the docs, code, tests, ADRs, and runtime surfaces that are relevant to the contract.

Record context pointers in the contract or handoff when they materially affect implementation.

## 4. Implement with TDD discipline

Use behavior-first TDD for production changes:

1. Write or identify a failing regression or behavior test.
2. Run it and record RED evidence when it is useful.
3. Implement the smallest vertical slice.
4. Run the targeted test and broader required checks.
5. Record GREEN evidence.
6. Refactor only while green.

Do not apply TDD dogmatically to pure docs, mechanical renames, generated snapshots, or exploratory spikes. In those cases, write an explicit evidence plan or waiver.

## 5. Capture evidence

Every completion claim needs fresh, claim-relative evidence or waiver. Skipped checks are not pass results. For medium or higher risk, passing evidence should include a command log, artifact URI, or manual artifact reference so review can inspect what actually happened.

Evidence freshness is strict for implementation changes. Harness lifecycle artifacts under `.harness/` can change after evidence or review for handoff, receipts, review records, or archival notes; those lifecycle-only changes should warn rather than force all product evidence to be rerun.

Gate:

```bash
python3 harness/cli/harnessctl.py validate --id <WU-ID> --strict
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate verification --strict
```

CI / protected branch gate:

```bash
python3 harness/cli/harnessctl.py ci --strict
```

## 6. Review

Plan review checks whether the execution plan is grounded in repository truth before implementation starts. Close review checks whether diff, evidence, scope, risk, and maintainability satisfy the Work Unit Contract before acceptance.

For medium or higher risk, `running` requires a passing plan review or explicit self-check downgrade where allowed. For high or critical risk, use independent review or human gate. For medium or higher risk, a passing close review must cite the fresh evidence receipt IDs it relied on.

On Codex, subagents are explicit. When a Work Unit requires reviewer or worker isolation, the main agent must start the reviewer/worker directly and wait for the result before continuing; do not rely on automatic delegation.

Gates:

```bash
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate plan-review --strict
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate review --strict
```

## 7. GitHub collaboration

Use GitHub after the local task shape is grounded. Create issues, branches, commits, and PRs after the Work Unit is specified and the relevant plan review has passed. GitHub records collaboration state; it does not replace the contract, evidence receipts, review verdicts, waivers, or controller gates.

## 8. Handoff or archive

A task can be archived only when it has evidence/waiver, required review, and either a handoff or an explicit `--no-next-step-reason`.

## 9. Compound or prune

Keep or add a mechanism only if it has a failure trace, protected invariant, validation method, known cost, and removal condition.
