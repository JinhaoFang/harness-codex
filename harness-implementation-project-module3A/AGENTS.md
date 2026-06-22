# Agent Project Guide

This repository is a portable coding-agent Harness implementation. This file is the project map for developing the Harness itself; target repositories receive `harness/templates/adoption/AGENTS.md`.

## Project layout

- Controller: `harnessctl`
- Hooks: `harness/hooks/`
- Canonical skills: `skills/`
- Codex skills mirror: `.agents/skills/`
- Claude skills mirror: `.claude/skills/`
- Adoption templates: `harness/templates/adoption/`
- Tests: `harness/tests/`
- Detailed guidance: `docs/harness/`
- Codex native subagent playbook: `docs/harness/codex-native-subagents.md`

## Development rules

- Keep tracked user intent in `docs/spec/<WU-ID>.md`; keep local plans, evidence logs, review tracks, handoffs, and runtime state under ignored `.harness/`.
- Preserve the hard boundary: clarify/spec approval → local technical plan → plan review → isolated worker → controller-executed evidence → the same logical reviewer session for close review.
- Repository code/tests/runtime are current project truth. The tracked spec is desired intent. A local plan is disposable implementation context.
- Pass evidence must come from `harnessctl verify`; do not reintroduce self-reported pass receipts.
- Missing required evidence blocks or requires a material spec revision and reapproval. Do not add a generic waiver path without a demonstrated failure trace.
- Planner, worker, and reviewer identities/sessions are separated for low+ work. Reviewer is read-only and plan/close review share one logical reviewer session and review track.
- Keep platform entry files short; route task-specific behavior through skills.
- Update controller tests, schemas, docs, platform mirrors, and adoption behavior together.

## Commands

```bash
python3 scripts/sync_platform_skills.py
python3 -m unittest discover -s harness/tests -v
harnessctl check --gate skills --strict
harnessctl ci --strict
python3 scripts/package.py --verify
```

Use minimal, purpose-fit changes. Every new Harness mechanism needs a failure mode, protected invariant, validation method, known cost, and removal condition.
