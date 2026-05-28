# Agent Entry Point

This file is a short map, not the full harness manual.

## Always-on rules

1. For non-trivial work, read or create a Work Unit Contract before editing production files.
2. Read `.harness/work-units/active/<WU-ID>/contract.md` directly before implementation; do not rely on a compressed briefing as a substitute.
3. Treat the repository, tests, runtime behavior, contracts, evidence receipts, reviews, waivers, and handoffs as separate truth sources.
4. Do not call a task complete without fresh evidence or an explicit waiver.
5. Do not treat a review verdict as evidence. Review judges sufficiency; it does not manufacture test or runtime facts.
6. Do not expand scope silently. Amend the Work Unit or stop and ask for human direction.
7. High-risk work involving auth, permissions, billing, migrations, secrets, production data, deployment, or irreversible changes requires a risk gate and independent review or human approval.

## First commands

```bash
python3 harness/cli/harnessctl.py list
python3 harness/cli/harnessctl.py status --id <WU-ID>
```

## Context routing

Read in this order:

1. Work Unit Contract or issue spec.
2. `docs/harness/README.md` for the lifecycle.
3. Local rules near the files you will touch.
4. Current code, tests, runtime behavior, and CI configuration.
5. ADRs or docs referenced by the Work Unit or changed paths.

If docs conflict with code/tests/runtime, surface the conflict. Do not silently choose the convenient source.

## Validation entrypoint

Use project-specific validation if available. Otherwise start with:

```bash
python3 -m unittest discover -s harness/tests
python3 harness/cli/harnessctl.py doctor
```

## Platform adapters

- Codex-specific examples live in `.codex/`.
- Claude Code-specific examples live in `.claude/`.
- Platform-neutral reusable workflows live in `skills/`.
