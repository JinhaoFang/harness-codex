# Platform Adapters

Platform adapters map the same core invariants to different agent runtimes. They must not redefine the core standard.

## Codex

Use `AGENTS.md` as a concise project map. Keep task state in `.harness/`, not in the prompt or thread.

### Codex skills

Codex repository skills live in `.agents/skills/<skill-name>/SKILL.md`. Each `SKILL.md` must include `name` and `description` in YAML frontmatter.

This project treats `skills/` as the canonical editable catalog and syncs platform copies with:

```bash
python3 scripts/sync_platform_skills.py
```

Do not hand-edit `.agents/skills/` without syncing back to `skills/`.

### Codex subagents

Project subagents live in `.codex/agents/*.toml` and use these fields:

```toml
name = "harness_worker"
model = "gpt-5.5-codex"
description = "..."
sandbox_mode = "workspace-write"
model_reasoning_effort = "medium"
developer_instructions = """
...
"""
```

Do not use `instructions`; Codex subagents use `developer_instructions`. Optional fields can be omitted only when inheritance from the parent session is intentional. Do not add `[agent] instructions_file = "AGENTS.md"` to `.codex/config.toml`; Codex discovers `AGENTS.md` through its documented instruction-file mechanism.

Minimal retained roles:

| Role | Sandbox | Purpose |
|---|---|---|
| `harness_worker` | workspace-write | implement one bounded Work Unit inside the write boundary |
| `harness_reviewer` | read-only | perform independent plan/close review from fresh inputs |

Do not add planner, monitor, verifier, or explorer as resident subagents by default. Those responsibilities are covered by skills, controller gates, hooks, or ordinary task routing until a real failure trace proves that an isolated role is needed.

Subagents should receive a small input bundle:

- Work Unit Contract;
- current diff or path list;
- required evidence IDs;
- known risk boundary;
- explicit output contract.

Do not send all `.harness` history to a subagent.

### Codex Goals

A Goal is useful for a current Codex thread because it keeps objective, completion condition, evidence, constraints, and files-to-read visible during long-running work. In this implementation, a Goal is a thread-level execution objective; it does not replace the repository Work Unit Contract, evidence receipts, controller state, or review verdict.

Recommended mapping:

```text
Work Unit Contract -> Codex Goal text
Codex Goal -> current-thread execution objective
Controller state -> lifecycle authority
Evidence receipts -> verification authority
Review verdict / human gate -> acceptance authority
```

### Codex hooks

Codex hooks can run deterministic policy scripts before commands and at stop points. Treat them as defense-in-depth. Critical safety boundaries should also be protected by sandboxing, permissions, branch protection, CI, or human approval.

## Claude Code

Use `CLAUDE.md` as a short project map. Enforcement belongs in Claude Code permissions, hooks, sandboxing, CI, and controller checks.

### Claude Code skills

Claude project skills live in `.claude/skills/<skill-name>/SKILL.md`. The directory name is the slash-command name; `description` determines automatic loading, and `name` is a display label. Keep skill bodies concise because loaded skill content stays in context.

This project syncs the same canonical `skills/` catalog into `.claude/skills/` with:

```bash
python3 scripts/sync_platform_skills.py
```

### Claude Code subagents

Project subagents live in `.claude/agents/*.md` and use markdown frontmatter such as:

```yaml
---
name: harness-worker
description: Implement one bounded Work Unit using TDD and evidence capture.
tools: Read, Grep, Glob, Edit, MultiEdit, Bash
model: sonnet
---
```

Keep project subagents minimal: worker and reviewer are the default retained roles. Clarification, specification, grounding, evidence capture, handoff, and GitHub collaboration live in skills and controller commands unless a repository-specific failure trace justifies a new isolated subagent. Give reviewer agents fresh inputs from contract, diff, code, tests, and evidence rather than the builder's narrative.

### Permissions

Use deny/ask/allow profiles:

- deny irreversible or unsafe commands by default;
- ask before pushes, resets, migrations, deployment, broad deletes, or external side effects;
- allow low-risk reads, targeted tests, and controller commands.

## GitHub

GitHub is the preferred collaboration surface for non-trivial project work:

- issue or Work Unit defines intent and scope;
- branch/worktree isolates execution;
- PR contains summary, diff, evidence receipts, skipped checks, risk notes, and reviewer verdict;
- CI attaches fresh evidence;
- review comments become compounding candidates.

## Symphony or issue-based orchestration

Only add issue schedulers and per-issue workspaces when scale, concurrency, or recovery cost justifies them. Scheduler state is not completion authority; evidence and review remain separate gates.
