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

Codex hooks can run deterministic policy scripts at multiple lifecycle points. Treat them as defense-in-depth. Critical safety boundaries should also be protected by sandboxing, permissions, branch protection, CI, or human approval.

Default Codex hooks retained by this template:

| Event | Harness use | Boundary note |
|---|---|---|
| `SubagentStart` | inject minimal worker/reviewer role context | context only |
| `PreCompact` | stop compaction when changed active work has no handoff | recovery guard |
| `PostCompact` | add recovery context after compaction | context only |
| `Stop` | continue the turn when changed active work lacks fresh evidence | completion guard |

`SessionStart`, `UserPromptSubmit`, `PreToolUse`, and `PermissionRequest` are optional extensions, not defaults. For Codex, `.codex/hooks.json` must live at the project root that Codex opens; hooks nested under an unopened subdirectory may not run. Even when `SubagentStart` is configured, the main agent should still pass the Work Unit ID and required input bundle explicitly to worker/reviewer subagents.

Hook sounds are best-effort only. On macOS, `SubagentStart` plays a short system sound, and `Stop` plays a completion sound when it does not block the agent. Set `HARNESS_HOOK_SOUND=0` to disable sound; non-macOS and CI environments stay silent.

Do not return `permissionDecision: "ask"` from Codex `PreToolUse`. Ask-class behavior belongs in the native approval flow and `PermissionRequest`; `PreToolUse` should deny, add context, rewrite allowed input, or stay silent.

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

### Claude Code hooks

Claude Code supports a broader lifecycle surface than this template fully uses. Recommended retained hooks:

| Event | Harness use |
|---|---|
| `SessionStart` | active Work Unit recovery brief |
| `UserPromptSubmit` | non-trivial-work routing reminder |
| `PreToolUse` | deterministic dangerous command/path guard |
| `PostToolBatch` | short context nudge after a batch of tools |
| `TaskCompleted` | prevent task completion when changed active work lacks fresh evidence |
| `SubagentStart` | inject worker/reviewer output protocol |
| `PreCompact` / `PostCompact` | handoff-before-compact and recovery-after-compact |
| `Stop` | stop-without-evidence guard |

Use hooks for deterministic checks and lifecycle reminders. Use subagents or prompt hooks only when the check requires actual reasoning over repo facts; do not move critical safety solely into an LLM hook.

## GitHub

GitHub is collaboration and review surface, not completion authority. Use it by task type and risk:

Create GitHub issues, branches, commits, and PRs after the Work Unit is specified and the relevant plan review has passed. Do not use GitHub state as a replacement for clarification, spec, evidence, or review gates.

| Task class | Git repo artifacts | GitHub issue | PR / CI |
|---|---|---|---|
| trivial docs/comment | usually none beyond final note | no | optional |
| low local bugfix | optional lightweight Work Unit note | optional | PR evidence note is enough |
| medium multi-file or user-visible behavior | Work Unit Contract, state, receipts/review summaries | recommended | PR with evidence refs and CI artifacts |
| high auth/billing/security/migration | locked Work Unit, waiver/review records, rollback path | required | protected PR, CI artifacts, human gate when needed |
| critical production/data/compliance | audit-grade Work Unit and approvals | required | protected PR, retained artifacts, explicit human approval |

Stable harness implementation belongs in repo: `AGENTS.md`, `CLAUDE.md`, `harness/cli`, `harness/hooks`, schemas, templates, skills, adapters, and CI workflows. Large command logs, screenshots, traces, and raw session transcripts should usually live in CI/GitHub artifacts or temporary storage, not as committed repo noise.

## Symphony or issue-based orchestration

Only add issue schedulers and per-issue workspaces when scale, concurrency, or recovery cost justifies them. Scheduler state is not completion authority; evidence and review remain separate gates.
