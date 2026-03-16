# Runtime overview

This package turns the v3 design into a Codex-native runtime.

## Layers

- `AGENTS.md`: repository working agreement and routing hints.
- `.codex/config.toml`: project defaults and role registry.
- `.codex/agents/*.toml`: narrow role behavior.
- `.agents/skills/*`: reusable methods and stage-local guidance.
- `.codex/tools/agentctl.py`: deterministic controller.
- `.agentdocs/`: runtime truth and evidence storage.

## Long-lived runtime objects

- `.agentdocs/tasks/<task-id>/plan.md`
- `.agentdocs/tasks/<task-id>/workflow.md`
- `.agentdocs/tasks/<task-id>/reviews/*.json`
- `.agentdocs/tasks/<task-id>/evidence/*.json`

`subtask-pack.md` 是按需再生的派生对象；可以持久化，但不应被当作新的真相层。

## Role of the controller

The controller owns deterministic operations:

- initialize runtime storage
- create task shells
- update current workflow state
- refresh subtask packs
- write review JSON
- write evidence JSON
- validate refs
- archive and reopen tasks

## Role of skills

Skills provide progressive, narrow, reusable guidance.
They do not own state truth or completion truth.
They teach Codex when to inspect code, when to refresh a pack, how to write a review, and when to call the controller.
