# Adoption Guide

## Step 1: Copy the thin layer

Copy:

```text
AGENTS.md
CLAUDE.md
docs/harness/README.md
harness/cli/harnessctl.py
harness/templates/
harness/schemas/
skills/harness-clarify/
skills/harness-evidence/
skills/harness-handoff/
```

Run:

```bash
python3 harness/cli/harnessctl.py init
python3 harness/cli/harnessctl.py doctor
```

## Step 2: Define the repository validation entrypoint

Add a project-specific `make check`, CI workflow, or documented command list. Store only the route in `AGENTS.md`/`CLAUDE.md`; store detailed validation in docs or scripts.

## Step 3: Use Work Units for non-trivial work

Create one Work Unit per task or issue. Keep the contract short enough for an agent and reviewer to read before work.

## Step 4: Add evidence receipts

Record targeted tests, typechecks, runtime evidence, migration dry-runs, screenshots, or manual QA artifacts as receipts.

## Step 5: Add review gates where they pay off

Start with self-check for low risk, close review for medium risk, and independent review or human gate for high/critical risk.

## Step 6: Add hooks as guardrails

Enable hooks only after the base workflow is understood. Hooks are best for reminders, deterministic command blocking, and stop-without-evidence checks. They are not the only safety boundary.

## Step 7: Add subagents only for isolation or throughput

Default retained role split:

- worker: implements one bounded Work Unit;
- reviewer: checks plan or close readiness from fresh inputs.

Do not add planner, monitor, verifier, or explorer as resident subagents by default. Use skills and controller commands for those responsibilities first; add an isolated role only when context isolation, permission isolation, review independence, or throughput has a concrete failure trace.

## Step 8: Add HEB evaluation before thickening

Before adding a scheduler or a heavy controller, run the HEB cases and compare variants. Remove mechanisms that do not improve evidence, recovery, boundary, ambiguity, or human burden.
