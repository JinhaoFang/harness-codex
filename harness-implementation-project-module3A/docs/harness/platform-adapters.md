# Platform adapters

Adapters map platform capabilities to the same controller lifecycle. They do not own product intent, evidence truth, or acceptance.

## Shared contract

Both adapters:

- capability-probe the executable and required resume surface;
- launch Reviewer read-only and Worker workspace-write;
- require structured output matching a generated JSON schema;
- capture a real platform session/thread ID;
- persist a logical session binding under `.harness`;
- fail closed when the CLI, resume capability, session capture, or output contract is unavailable;
- never treat platform completion as Harness completion.

Use:

```bash
harnessctl adapter-doctor --platform codex --strict
harnessctl adapter-doctor --platform claude --strict
harnessctl route --id <WU-ID> --platform codex
harnessctl dispatch-review --id <WU-ID> --mode plan --platform claude ...
harnessctl dispatch-worker --id <WU-ID> --platform claude ...
harnessctl advance --id <WU-ID> --platform claude ...
```

## Codex

- `AGENTS.md` is a concise project map and skill router.
- Reviewer uses a read-only Codex execution sandbox.
- Worker uses workspace-write after the Plan Review gate.
- Close Review resumes the thread captured during Plan Review.
- The root Codex session should spawn or resume native reviewer/worker subagents; the controller no longer claims to create those Codex subagents itself.
- Native Codex subagents bind their observed session through hooks or `bind-session`, then use controller commands for `request-review`, `submit-review`, `start-work`, `verify`, and final gates.
- `goal-export` keeps an auditable repo-local projection of the approved Work Unit and plan.
- Worker dispatch uses the stable app-server `thread/start|resume` and `thread/goal/set` surface to bind that projection to actual persisted Codex Goal state before the execution turn.
- If Goal bootstrap is unavailable or fails, the adapter records an explicit degraded state and may continue with ordinary `codex exec`; evidence, review, and risk gates never degrade.
- Goal completion is a worker signal only, never evidence, review, delivery, or archive authority.

## Claude Code

- `CLAUDE.md` is a concise project map, not enforcement.
- Reviewer runs through the `harness-reviewer` agent with read-only tools.
- Worker runs through `harness-worker` with edit/write tools after the gate.
- Close Review resumes the session captured during Plan Review.
- Claude keeps the controller-managed `dispatch-review`, `dispatch-worker`, and `advance` workflow.
- Permissions, sandboxing, hooks, CI, and controller checks remain defense in depth.

## Hooks

Installed adapters include:

| Event | Purpose |
|---|---|
| `SubagentStart` | inject role/Work Unit routing context |
| `PreToolUse` | optionally intercept dangerous shell/tool usage early |
| `PreCompact` | write a fresh controller checkpoint/handoff |
| `PostCompact` | restore the compact recovery pointer |
| `Stop` | checkpoint/handoff reminder; never traps the user in a session |

Hooks are not the sole critical boundary. Controller gates, platform permissions/sandbox, CI, GitHub branch protection, and human gates still apply.

`PreToolUse` is an optional hardening layer. In the full profile it is kept narrow on purpose: dangerous shell commands may be denied or escalated early, but phase/write-boundary correctness belongs to controller gates such as `start-work`, `verify`, review continuity, scope checks, and final acceptance. Thin shared profiles omit `PreToolUse` entirely.

## Skills

Edit canonical `skills/`, then mirror:

```bash
python3 scripts/sync_platform_skills.py
```

Codex reads `.agents/skills`; Claude reads `.claude/skills`. Skills guide reasoning and call controller commands, but cannot mutate lifecycle state by prose.

## Failure behavior

Platform CLI behavior changes over time. Keep adapter command/resume/Goal-control tests in CI. A failed core capability probe or missing session ID must block and expose the error; it must not silently skip a Reviewer or Worker leg. Optional Goal-control failure must remain visible without weakening Controller acceptance gates.
