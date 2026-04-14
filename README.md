# Agentic Codex Runtime v3

**English** | [中文](README.zh-CN.md)

> Make AI coding agent development **reproducible, verifiable, reversible, resumable, and evolvable** — without context rot.

## What is this?

A deterministic runtime framework for AI coding agents (Codex, Claude, etc.). It provides:

- **Truth Model** — Clear separation between Goal truth (`plan.md`), Process truth (`workflow.md`), and World truth (code/tests/runtime).
- **Controller** — A CLI tool (`agentctl.py`) that enforces gates, manages state transitions, and produces verifiable artifacts.
- **Skills** — Pluggable stage/method/review skills (world-grounding, freeze-plan, execute-subtask, tdd, plan-review, close-review, ...).
- **Subagent Coordination** — Structured handoff contracts for multi-agent collaboration with bootstrapping and context recovery.

## Repository Structure

```
codex_harness/
├── agentic_codex_runtime_v3_fusion/   # Main runtime package (copy to target repo root)
│   ├── AGENTS.md                       # Project-level agent protocol
│   ├── AGENTS.global.md                # Global template (~/.codex/AGENTS.md)
│   ├── .codex/
│   │   ├── config.toml                 # Codex config & agent registry
│   │   ├── agents/                     # Subagent role definitions
│   │   ├── tools/agentctl.py           # Deterministic control plane
│   │   └── templates/                  # Plan, workflow, evidence, review templates
│   ├── .agents/skills/                 # Runtime skills
│   ├── .agentdocs/                     # Task workspace (SSOT)
│   ├── .github/workflows/              # CI guardrails
│   └── docs/agentic/spec/              # Design specifications
└── docs/                               # Reference materials & migration guides
```

## Quick Start

### Prerequisites

- Python 3.9+
- Git
- An AI coding agent (OpenAI Codex CLI, Claude Code, or similar)

### Install into a Target Repository

1. Copy the runtime package to your project root:

   ```bash
   cp -r agentic_codex_runtime_v3_fusion/* /path/to/your-project/
   ```

2. (Optional) Set up the global protocol:

   ```bash
   cp agentic_codex_runtime_v3_fusion/AGENTS.global.md ~/.codex/AGENTS.md
   ```

3. Initialize the runtime workspace:

   ```bash
   python .codex/tools/agentctl.py init-agentdocs
   ```

4. Create your first task:

   ```bash
   python .codex/tools/agentctl.py create-task --slug my-first-task --title "My first task"
   ```

5. (Optional) Enable repo guardrails:

   ```bash
   bash .githooks/install.sh
   ```

### Recommended Workflow

```
Discuss → world-grounding → freeze-plan → refresh-subtask-pack
  → (optional: plan-eng-review) → plan-review
  → execute-subtask (+ tdd for code tasks)
  → evidence-capture → close-review → archive
```

## Architecture Principles

| Principle | Description |
|-----------|-------------|
| **Truth separation** | `plan.md` = Goal, `workflow.md` = Process, code/tests = World |
| **Deterministic control** | `agentctl.py` handles state transitions; agent handles judgment |
| **Pluggable skills** | Core stages + optional method/review skills |
| **Independent review** | Reviews use fresh context, never self-review |
| **TDD as method** | Required for all code-bearing development tasks |
| **Subagent bootstrap** | Subagents self-reconstruct context from `.agentdocs/*` |

## Documentation

- [Design Specifications](agentic_codex_runtime_v3_fusion/docs/agentic/spec/) — Numbered spec documents (00-08)
- [Controller Reference](agentic_codex_runtime_v3_fusion/docs/agentic/reference/) — Command reference and overview
- [Fusion Decision Checklist](agentic_codex_runtime_v3_fusion/docs/agentic/spec/08-fusion-decision-checklist.md) — Which modules are core vs optional
- [Reference Materials](docs/references/) — Agent engineering guides and design references

## Core Skills

| Skill | Stage | Description |
|-------|-------|-------------|
| `world-grounding` | Ground | Anchor task in current codebase reality |
| `freeze-plan` | Plan | Write and freeze `plan.md` as Goal truth |
| `refresh-subtask-pack` | Plan | Generate derived subtask packs |
| `plan-review` | Review | Independent plan review verdict |
| `execute-subtask` | Execute | Implement a grounded subtask |
| `evidence-capture` | Execute | Capture verification evidence |
| `close-review` | Review | Independent close review verdict |
| `reopen-fix` | Fix | Reopen with scope change reason |

## Optional Modules

- `tdd` — Test-driven development method overlay
- `subagent-bootstrap` — Self-context reconstruction for subagents
- `plan-eng-review` — Owner-side engineering challenge (not a gate)
- `worktree-isolation` — Parallel execution in isolated git worktrees
- `session-recovery` — Cross-session context recovery
- `github-collaboration` — Issue/PR traceability with `gh` CLI
- `contract-artifacts` — Long-lived business/API/UI contracts

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
