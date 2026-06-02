# Coding Agent Project Harness

> Make AI coding agent development **reproducible, verifiable, reversible, resumable, and evolvable** — without context rot.

## What is this?

A portable implementation scaffold for using Codex, Claude Code, or similar coding agents in real codebases without turning the harness into a second product.

The implementation is intentionally **controller-light but invariant-heavy**:

- The repository and runtime remain the source of project truth
- Non-trivial work starts from a Work Unit Contract
- Agent work is bounded by explicit write and risk boundaries
- Completion requires fresh evidence or a waiver
- Review verdicts are separated from evidence receipts
- Handoff and state are generated from authoritative artifacts, not chat summaries
- Every non-trivial mechanism has a purpose, validation method, cost, and removal condition

## Repository Structure

```
codex_harness/
├── harness-implementation-project-module3A/  # Main harness implementation (copy to target repo)
│   ├── README.md                              # Project overview
│   ├── CLAUDE.md                              # Claude Code project guide
│   ├── AGENTS.md                              # Codex project guide
│   ├── .harness/                              # Work Unit lifecycle, evidence, reviews
│   ├── harness/cli/harnessctl.py              # Controller CLI
│   ├── harness/hooks/                         # Deterministic guard scripts
│   ├── harness/schemas/                       # JSON schemas for artifacts
│   ├── harness/templates/                    # Contract, handoff, review templates
│   ├── skills/                                # Platform-neutral skill catalog
│   ├── .claude/                               # Claude Code adapter examples
│   ├── .codex/                                # Codex adapter examples
│   └── docs/harness/                          # Detailed lifecycle docs
├── docs/                                      # Reference materials
│   ├── coding_agent_project_harness_standard_v0.6.2.md
│   └── harness_engineering_tutorial_v0.6.0.md
└── reference_project/                          # Reference implementations
```

## Fast Start

### Prerequisites

- Python 3.9+
- Git
- An AI coding agent (OpenAI Codex CLI, Claude Code, or similar)

### Install into a Target Repository

Use `scripts/adopt.py install` to install the platform profile your target repository needs:

```bash
cd harness-implementation-project-module3A
python3 scripts/adopt.py install /path/to/repo --profile codex
python3 scripts/adopt.py install /path/to/repo --profile claude
```

Adoption profiles:

| Profile | Description |
|---------|-------------|
| **codex** | Common harness runtime + `AGENTS.md`, `.codex` |
| **claude** | Common harness runtime + `CLAUDE.md`, `.claude` |

Installation is incremental: existing target files are kept or appended, not replaced. Installed harness-owned paths are added to `.gitignore` so they stay local to the target repository.

### Quick Workflow

```bash
# Initialize
python3 harness/cli/harnessctl.py init

# Create a Work Unit
python3 harness/cli/harnessctl.py new --id WU-001 --title "Fix login redirect" --type bugfix --risk medium

# Check status
python3 harness/cli/harnessctl.py status --id WU-001

# After implementation
python3 harness/cli/harnessctl.py evidence --id WU-001 --claim EV1 --type test --result pass --command "pytest tests/test_login.py" --command-log-ref ".harness/work-units/active/WU-001/evidence/artifacts/pytest-login.log"
python3 harness/cli/harnessctl.py validate --id WU-001 --strict
python3 harness/cli/harnessctl.py check --id WU-001 --gate verification
```

## Core Loop

```
Clarify -> Work Unit Contract -> Context Routing -> Plan Review when needed -> Implementation -> Evidence -> Verification -> Close Review -> CI Gate -> Handoff or Archive
```

## Adoption Profiles

| Target profile | Copy first | Add only when needed |
|---|---|---|
| Thin Local Harness | `AGENTS.md`, `CLAUDE.md`, `docs/harness/README.md`, `harness/cli/harnessctl.py`, selected skills | hooks, review agents |
| Controlled Repo Harness | Thin + `.harness` lifecycle, evidence receipts, scope checks, close review workflow | CI gates, path policy |
| Risk-Aware Harness | Controlled + waiver model, human gate, deny/ask permissions, boundary hooks | policy-as-code, security review |
| Scaled Multi-Agent Harness | Risk-aware + issue/PR discipline, minimal worker/reviewer subagents, worktrees, HEB evaluation | scheduler/orchestrator |

## Documentation

- [Harness Standard (v0.6.2)](docs/coding_agent_project_harness_standard_v0.6.2.md) — Core standard, capability model, and reference profiles
- [Harness Engineering Tutorial (v0.6.0)](docs/harness_engineering_tutorial_v0.6.0.md) — Why, how to evaluate, how to adopt, how to avoid over-engineering
- [Harness Implementation Guide](harness-implementation-project-module3A/docs/harness/README.md) — Detailed lifecycle documentation

## Core Skills

| Skill | Purpose |
|-------|---------|
| `harness-clarify` | Clarify ambiguous work before implementation |
| `harness-spec` | Create/lock/amend Work Unit Contracts |
| `harness-ground` | Establish repository truth and context |
| `harness-tdd` | Behavior-first test-driven development |
| `harness-evidence` | Capture claim-relative evidence receipts |
| `harness-review` | Plan, close, risk, security, or architecture review |
| `harness-github` | GitHub issues, branches, commits, PRs integration |
| `harness-handoff` | Generate recoverable handoffs |
| `harness-compound` | Convert failures into durable assets or pruning decisions |
| `harness-waiver` | Create scoped human-approved waivers |

## What this project is not

It is not a universal agent platform, a mandatory directory standard, or a replacement for project-specific engineering judgment. It provides a small set of enforceable invariants and adapter examples that can be copied, removed, or thickened according to real failure traces.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
