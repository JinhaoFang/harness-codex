---
name: harness-ground
description: Establish repository truth and task context before planning, implementation, or review. Use when repo facts are uncertain, docs may be stale, affected files are unknown, API/framework behavior must be verified, or a subagent needs a concise context pointer pack instead of broad document reading.
---

# Harness Ground

Reduce wrong assumptions by routing context instead of accumulating it.

## Read order

1. Current Work Unit Contract or issue spec.
2. Short project map: `AGENTS.md` / `CLAUDE.md`.
3. Local rules near likely changed paths.
4. Code, tests, config, runtime logs, or generated artifacts that define current behavior.
5. ADRs or docs referenced by the contract or touched area.
6. Official external docs only when platform/API behavior is part of the task.

## Output

```text
Facts established:
Files/symbols inspected:
Relevant existing tests:
Docs/code conflicts:
Risk and unknowns:
Recommended context pointers:
Next legal action:
```

## Do not

- Do not read the whole knowledge base.
- Do not treat stale docs as stronger than current code/tests/runtime.
- Do not propose implementation until the parent task asks for it.
- Do not hide conflicts; surface them as tradeoffs or blockers.
