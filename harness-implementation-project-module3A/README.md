# Coding Agent Harness Implementation Project

This repository is a portable implementation scaffold for using Codex, Claude Code, or similar coding agents in a real codebase without turning the harness into a second product.

The implementation is intentionally **controller-light but invariant-heavy**:

- the repository and runtime remain the source of project truth;
- non-trivial work starts from a Work Unit Contract;
- agent work is bounded by explicit write and risk boundaries;
- completion requires fresh evidence or a waiver;
- review verdicts are separated from evidence receipts;
- handoff and state are generated from authoritative artifacts, not chat summaries;
- every non-trivial mechanism has a purpose, validation method, cost, and removal condition.

Use this project by installing the platform profile that matches your repository:

| Target profile | Copy first | Add only when needed |
|---|---|---|
| Codex Harness | Common runtime + `AGENTS.md`, `.codex` | policy-as-code, protected branch gates |
| Claude Harness | Common runtime + `CLAUDE.md`, `.claude` | policy-as-code, protected branch gates |

## Fast start

```bash
python3 harness/cli/harnessctl.py init
python3 harness/cli/harnessctl.py new --id WU-001 --title "Fix login redirect" --type bugfix --risk medium
cat .harness/work-units/active/WU-001/contract.md
python3 harness/cli/harnessctl.py status --id WU-001
```

After implementation work:

```bash
python3 harness/cli/harnessctl.py evidence --id WU-001 --claim EV1 --type test --result pass --command "pytest tests/test_login.py" --command-log-ref ".harness/work-units/active/WU-001/evidence/artifacts/pytest-login.log"
python3 harness/cli/harnessctl.py validate --id WU-001 --strict
python3 harness/cli/harnessctl.py check --id WU-001 --gate verification
python3 harness/cli/harnessctl.py request-review --id WU-001 --mode close --reviewer-role reviewer-agent
python3 harness/cli/harnessctl.py submit-review --id WU-001 --request-id <request-id> --mode close --decision PASS --reviewer-role reviewer-agent --independence-level fresh_context --evidence-ref <receipt-id>
python3 harness/cli/harnessctl.py ci --strict
python3 harness/cli/harnessctl.py handoff --id WU-001 --next-safe-action "Open PR with evidence receipt ev-..."
```

## Adoption profiles

Use `scripts/adopt.py install` to install the harness into a target repository:

```bash
python3 scripts/adopt.py install /path/to/repo --profile codex
python3 scripts/adopt.py install /path/to/repo --profile claude
```

The installer is incremental: existing files are kept, `AGENTS.md`/`CLAUDE.md` receive a marked harness block when already present, installed harness-owned paths are appended to `.gitignore`, and `.harness/config.json` is initialized only when missing. Package docs such as this adoption guide, source analysis, mechanism registry, and HEB evaluation cases are not copied into target repositories.

## What this project is not

It is not a universal agent platform, a mandatory directory standard, or a replacement for project-specific engineering judgment. It provides a small set of enforceable invariants and adapter examples that can be copied, removed, or thickened according to real failure traces.

## Directory map

```text
AGENTS.md                       Codex-oriented concise project map
CLAUDE.md                       Claude Code concise project map
.codex/                         Codex adapter examples: config, hooks, minimal worker/reviewer agents
.claude/                        Claude Code adapter examples: settings, hooks, minimal worker/reviewer agents, skills
.github/workflows/              Portable CI checks for the harness itself
.githooks/                      Optional local Git hooks
harness/cli/harnessctl.py       Small controller CLI, including validate/spec/scope/verification/review/ci/archive/skills gates
harness/hooks/                  Deterministic guard and lifecycle hook scripts
harness/schemas/                JSON schemas for Work Units, evidence, reviews, waivers
harness/templates/              Contract, handoff, review, waiver templates
harness/tests/                  Controller tests
skills/                         Platform-neutral skill catalog
scripts/                        Repository adoption and maintenance scripts
docs/harness/                   Source analysis, workflow, adapters, HEB evaluation docs
examples/                       Example Work Unit and policy files
```

## Core loop

```text
Clarify -> Specify Work Unit -> Route Context -> Execute with TDD -> Capture Evidence -> Review -> Handoff -> Compound or Prune
```

The controller does not try to judge product quality. It blocks only deterministic failures such as invalid harness artifacts, missing contracts, stale evidence, obvious scope violations, builder-authored close reviews, and high-risk work without independent review or human gate.
