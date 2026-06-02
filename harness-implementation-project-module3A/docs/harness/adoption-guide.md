# Adoption Guide

## Step 1: Install the harness

Run the installer from the harness implementation package while pointing at the target repository:

```bash
python3 scripts/adopt.py install /path/to/repo --profile codex
python3 scripts/adopt.py install /path/to/repo --profile claude
```

Profiles:

| Profile | Copies | Use when |
|---|---|---|
| `codex` | common harness runtime + `AGENTS.md`, `.codex` | target repo uses Codex project instructions, skills, subagents, or hooks |
| `claude` | common harness runtime + `CLAUDE.md`, `.claude` | target repo uses Claude Code permissions, hooks, agents, or skills |

Installation is incremental. Existing target files are kept; `AGENTS.md` and `CLAUDE.md` receive a marked harness block instead of being replaced. Existing `.gitignore`, `.codex`, `.claude`, `.github`, and `Makefile` content is not removed. Installed harness-owned paths are appended to `.gitignore` because they are local harness files, not target-repository source.

Implementation-package docs are intentionally not copied to target repositories. This excludes `docs/harness/evaluation/`, `docs/harness/adoption-guide.md`, `docs/harness/source-analysis.md`, and `docs/harness/mechanism-registry.yaml`. `docs/harness/platform-adapters.md` is copied only with platform profiles.

The installer also initializes `.harness/` runtime state and runs doctor unless `--no-doctor` is used. After install, run:

```bash
python3 harness/cli/harnessctl.py doctor
python3 harness/cli/harnessctl.py validate --all --strict
```

## Step 2: Define the repository validation entrypoint

Add a project-specific `make check`, CI workflow, or documented command list. Store only the route in `AGENTS.md`/`CLAUDE.md`; store detailed validation in docs or scripts.

## Step 3: Use Work Units for non-trivial work

Create one Work Unit per task or issue. Keep the contract short enough for an agent and reviewer to read before work.

## Step 4: Add evidence receipts

Record targeted tests, typechecks, runtime evidence, migration dry-runs, screenshots, or manual QA artifacts as receipts.

Add `harnessctl validate --all --strict` to CI before verification/review gates so malformed state, receipt, review, or waiver artifacts cannot be accepted.

Add `harnessctl ci --strict` as the aggregate protected-branch gate. For repositories where every PR must correspond to a Work Unit, use `harnessctl ci --strict --require-active`.

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
