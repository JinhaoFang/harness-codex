# Harness implementation map

This directory documents the concrete implementation. The short rules are:

1. `docs/spec/<WU-ID>.md` is the only task artifact committed by default.
2. `.harness/` contains disposable local execution state, including the technical plan.
3. Code/tests/runtime describe what exists; the approved spec describes what should exist.
4. Git/GitHub describe what changed and how it was integrated.
5. A pass receipt exists only when the controller actually executed the command.
6. Missing required evidence blocks. This profile intentionally has no generic waiver path.
7. The same reviewer track performs plan and close review; the reviewer stays read-only.

## Read by need

| Need | Document |
|---|---|
| Lifecycle and authority boundaries | [workflow.md](workflow.md) |
| Operator commands and recovery | [user-guide.md](user-guide.md) |
| Installing into another repository | [adoption-guide.md](adoption-guide.md) |
| Codex / Claude Code mappings | [platform-adapters.md](platform-adapters.md) |
| Risk escalation | [risk-gates.md](risk-gates.md) |
| Why external projects were used selectively | [source-analysis.md](source-analysis.md) |
| Why each retained mechanism exists | [mechanism-registry.yaml](mechanism-registry.yaml) |
| Harness evaluation | [evaluation/README.md](evaluation/README.md) |

## Authority map

| Question | Authority |
|---|---|
| What does the user want? | approved tracked spec |
| What is the project currently doing? | current code, tests and runtime |
| What did the worker change? | Git diff and commits |
| What was actually verified? | controller command log / CI artifact |
| Is the work sufficient? | reviewer or accountable human judgment |
| How can a local session resume? | `.harness/` when present; otherwise spec + Git/GitHub + current code |

Local summaries, plans and handoffs must never overwrite these sources.
