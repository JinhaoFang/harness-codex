# Harness implementation map

1. `docs/spec/<WU-ID>.md` is the only task artifact committed by default.
2. Its marked JSON block is the canonical Work Unit contract; surrounding prose supports human walkthroughs.
3. `.harness/` is ignored local runtime: plan, state, receipts, Reviewer session lineage, checkpoints and handoff.
4. Code/tests/runtime describe what exists; the approved spec describes what should exist; Git/GitHub describe what changed.
5. Pass evidence exists only when the controller executed the contract-bound check and observed the result.
6. Plan and Close Review use the exact same logical Reviewer session. Reviewer takeover is explicit and resets lineage.
7. `resume-session` continues trusted local state; `reconstruct` builds a conservative new local state from tracked and Git facts.

## Read by need

| Need | Document |
|---|---|
| Lifecycle and authority boundaries | [workflow.md](workflow.md) |
| Commands and recovery | [user-guide.md](user-guide.md) |
| Codex native reviewer/worker orchestration | [codex-native-subagents.md](codex-native-subagents.md) |
| Installing into another repository | [adoption-guide.md](adoption-guide.md) |
| Codex / Claude Code mappings | [platform-adapters.md](platform-adapters.md) |
| Risk escalation | [risk-gates.md](risk-gates.md) |
| Selective reuse of external projects | [source-analysis.md](source-analysis.md) |
| Why retained mechanisms exist | [mechanism-registry.yaml](mechanism-registry.yaml) |
| Harness evaluation | [evaluation/README.md](evaluation/README.md) |

## Authority map

| Question | Authority |
|---|---|
| What does the user want? | approved tracked Work Unit contract |
| What is the project currently doing? | current code, tests and runtime |
| What did the Worker change? | Git diff and commits |
| What was actually verified? | controller command log or equivalent CI artifact |
| Is the work sufficient? | Reviewer / accountable human judgment |
| Where can this exact local session continue? | controller state plus platform session binding |
| How is lost local runtime rebuilt? | tracked spec + Git/GitHub + current repository |

Plans, Goals, summaries and handoffs are derived views; none may overwrite these authorities.
