# Platform adapters

Adapters map platform features to the same lifecycle. They do not own product intent, evidence truth or acceptance.

## Canonical skills

Edit `skills/`, then mirror with:

```bash
python3 scripts/sync_platform_skills.py
```

| Platform | Repository skill path |
|---|---|
| Codex | `.agents/skills/<name>/SKILL.md` |
| Claude Code | `.claude/skills/<name>/SKILL.md` |

`.codex/skills` is not used by the current adapter.

The default catalog is intentionally small:

```text
clarify, spec, plan, ground, tdd, evidence, review, github, handoff, compound
```

Skills guide reasoning and call controller commands. They do not change lifecycle state by prose alone.

## Codex

`AGENTS.md` is a concise project map and skill router. Keep active Work Unit state out of it.

Default retained subagents:

| Agent | Capability |
|---|---|
| worker | workspace write inside the approved scope |
| reviewer | read-only plan and close review |

Project agent definitions live under `.codex/agents/`. Pass a small input bundle: Work Unit ID, tracked spec, local plan when available, current diff/evidence, role and output contract.

Codex Goals may represent the current thread's approved execution objective after plan review. Goal completion never replaces `harnessctl verify`, close review or GitHub/CI integration. The tracked spec remains the durable intent source.

The default Codex hook surface is deliberately narrow:

| Event | Use |
|---|---|
| `PreCompact` | non-blocking reminder to write a local handoff |
| `PostCompact` | restore a short repository-grounded brief |
| `Stop` | non-blocking reminder only; the user can always end the session |

Codex hooks are defense in depth, not a complete sandbox: the adapter keeps controller, CI, permissions and worktree boundaries authoritative. Project hooks also depend on the repository being trusted by Codex. Optional repository-specific hooks such as `PreToolUse`, `PermissionRequest`, `SessionStart`, or `SubagentStart` may still be wired in later, but they are not part of the default installed surface.

## Claude Code

`CLAUDE.md` is a concise project map. `.claude/settings.json` uses permissions and narrow hooks:

| Event | Use |
|---|---|
| `PreCompact` | non-blocking handoff reminder |
| `PostCompact` | short recovery context |
| `Stop` | non-blocking session-end reminder |

Completion is gated by explicit controller commands and CI, not by preventing the user from stopping a session.

Claude agents under `.claude/agents/` mirror the worker/reviewer split. Set `HARNESS_ROLE=reviewer` for the deterministic read-only path policy when the platform adapter can supply role environment.

## Git and GitHub

Use normal software-development control surfaces:

```text
approved spec
→ branch/worktree
→ bounded commits
→ controller-observed local checks
→ PR and CI
→ human/reviewer integration
```

The tracked spec can include issue, branch and pull-request references in its Delivery tracking section. Git diff/commits are execution truth; GitHub issue/PR/CI/review are collaboration and integration truth. Neither replaces the evidence contract.

For medium+ work, prefer one Work Unit per branch/worktree and one reviewable PR. Parallel workers must use separate worktrees; the controller refuses two active implementation Work Units in one workspace.

## Platform failure behavior

Adapters must fail visibly when a required capability changes. Keep adapter command/config tests in CI and do not silently skip reviewer, hook or validation legs after a CLI/API change.
