# Claude Code Project Guide

This repository develops a portable coding-agent Harness. Target repositories receive `harness/templates/adoption/CLAUDE.md`; do not copy this file as their lifecycle manual.

## Map

- `harness/cli/harnessctl.py`: deterministic lifecycle, command execution, evidence freshness, and review lineage.
- `harness/hooks/`: narrow platform guards and recovery reminders.
- `skills/`: canonical skill source; sync to `.agents/skills` and `.claude/skills`.
- `harness/templates/adoption/`: concise target-repository entrypoints.
- `docs/harness/`: workflow and design rationale.
- `harness/tests/`: controller, hook, platform-layout, and adoption tests.

## Invariants while editing

- Tracked specs live in `docs/spec`; `.harness` is ignored local runtime and may be rebuilt.
- Clarification and planning must not mutate product code.
- A medium+ task requires approved spec, a plan reviewer separated from the planner, a worker separated from both, controller-observed evidence, and close review on the same reviewer track.
- Do not accept an agent-supplied result/exit code as pass evidence.
- Do not reintroduce waiver, stop-blocking hooks, `.codex/skills`, or large always-on adoption instructions without a concrete failure trace.
- Reviewer remains read-only; findings return to the worker.
- Keep tests and nearby docs synchronized with controller behavior.

## Validation

```bash
python3 scripts/sync_platform_skills.py
python3 -m unittest discover -s harness/tests -v
python3 harness/cli/harnessctl.py check --gate skills --strict
python3 harness/cli/harnessctl.py ci --strict
```
