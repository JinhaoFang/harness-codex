# Harness Implementation Guide

## Design position

This implementation follows seven non-negotiable invariants:

1. No unbounded work.
2. No hidden state.
3. No completion without fresh evidence or waiver.
4. No non-negotiable boundary enforced only by prompt.
5. No review that manufactures evidence.
6. No compounding that increases future entropy.
7. No mechanism without purpose, cost, validation, and removal condition.

The harness starts thin. Add hooks, subagents, CI checks, or schedulers only when they solve a named failure mode.

## Lifecycle

```text
Discuss / Clarify
  -> Work Unit Contract
  -> Context Routing
  -> Execution Plan when needed
  -> TDD implementation
  -> Evidence Capture
  -> Verification Gate
  -> Plan or Close Review
  -> Handoff or Archive
  -> Compounding / Pruning decision
```

## Truth separation

| Question | Authority |
|---|---|
| What did the user ask for? | Work Unit Contract or approved issue spec |
| What is true about the project? | Current repo, tests, runtime, docs, ADRs |
| What did the agent do? | Git diff, command log, execution trace |
| What was verified? | Evidence receipts and CI/runtime artifacts |
| Is it acceptable? | Review verdict, waiver, human approval |
| How can work resume? | Controller state and handoff |
| What should persist? | Tests, lint, docs, ADRs, skills, controller checks |

## Work Unit Contract

A non-trivial task needs a contract. Non-trivial means any task that modifies production code, user-visible behavior, data/auth/billing/security/migration/deployment, multiple files, requires review, or may cross sessions.

Create one with:

```bash
python3 harness/cli/harnessctl.py new --id WU-001 --title "..." --type bugfix --risk medium
```

Then fill in:

- intent;
- expected outcome;
- non-goals;
- likely changed areas;
- write boundary;
- out-of-bounds paths;
- required evidence;
- stop conditions;
- open questions;
- context pointers.

Before implementation, lock the contract:

```bash
python3 harness/cli/harnessctl.py check --id WU-001 --gate spec --strict
python3 harness/cli/harnessctl.py lock --id WU-001 --status ready
```

Do not use summaries or generated briefs as a substitute for the Work Unit. The agent should read `contract.md` directly. If a locked contract changes, record an explicit amendment before continuing:

```bash
python3 harness/cli/harnessctl.py amend --id WU-001 --field scope --reason "..." --summary "..."
```

## Evidence

Use evidence receipts for deterministic or manual verification:

```bash
python3 harness/cli/harnessctl.py evidence \
  --id WU-001 \
  --claim EV1 \
  --type test \
  --result pass \
  --command "pytest tests/test_login.py"
```

Freshness is checked against current implementation content, current HEAD, and current diff hash. If implementation files change after evidence is recorded, re-run the relevant evidence or issue a waiver. If only harness lifecycle artifacts under `.harness/` change after evidence, the gate should warn rather than force all product evidence to be rerun.

## Artifact validation

Use validation to catch corrupted or drifted harness artifacts before review, archive, or CI acceptance:

```bash
python3 harness/cli/harnessctl.py validate --id WU-001 --strict
python3 harness/cli/harnessctl.py validate --all --strict
```

Validation checks schema versions, required fields, enum values, JSONL readability, Work Unit ID consistency, waiver ownership, and review-to-evidence references. It is intentionally lightweight and has no external dependency; it does not judge product correctness or replace verification/review gates.

For pull requests or protected branches, use the aggregate CI gate:

```bash
python3 harness/cli/harnessctl.py ci --strict
python3 harness/cli/harnessctl.py ci --strict --require-active
```

The CI gate runs artifact validation and, for active Work Units with non-`.harness/` repository changes, checks spec, scope, verification, and close review. `--require-active` is for repositories that want CI to reject changes that do not declare an active Work Unit.

## Review

Plan review is a pre-implementation gate. It checks the locked Work Unit, context pointers, relevant repo truth, and proposed execution plan before coding starts. Medium or higher risk Work Units cannot enter `running` without a passing plan review.

Close review is a pre-acceptance gate. Review verdicts must not be written by the builder for close review. For high or critical risk work, use an independent reviewer or human gate. A reviewer should inspect the contract, current diff, relevant code/tests, evidence receipts, skipped checks, and risk boundary.

## Handoff

Handoff is derived from authoritative artifacts. It should be enough for a new session to recover without reading chat history.

```bash
python3 harness/cli/harnessctl.py handoff --id WU-001 --next-safe-action "Run close review"
```

## Compounding

At the end of each non-trivial Work Unit, decide whether a future asset is needed:

```text
none | docs | adr | test | lint | ci | permission | hook | skill | controller-check | workflow | evaluator-rubric | deletion/pruning
```

Do not put all lessons into `AGENTS.md` or `CLAUDE.md`; choose the smallest durable asset that prevents the recurrence.
