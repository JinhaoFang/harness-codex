# Claude Code Project Map

This file should stay short. It routes Claude Code toward the right artifacts; it is not a policy engine or state store.

## Required behavior

- For non-trivial tasks, create or read a Work Unit Contract before implementation.
- Keep active state in `.harness/work-units/active/<id>/state.json`, not in this file.
- Capture verification using `harnessctl evidence`; do not rely on a natural-language claim.
- Use a separate reviewer agent or fresh context for close review when risk is high or critical.
- Record skipped evidence as skipped, never as pass.
- Use waivers only for explicit human risk acceptance.

## Minimal workflow

```bash
python3 harness/cli/harnessctl.py init
python3 harness/cli/harnessctl.py list
python3 harness/cli/harnessctl.py status --id <WU-ID>
cat .harness/work-units/active/<WU-ID>/contract.md
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate spec --strict
python3 harness/cli/harnessctl.py lock --id <WU-ID> --status ready
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate plan-review --strict
```

## Claude Code assets

- `.claude/settings.json` contains deny/ask/allow permission examples and hook wiring.
- `.claude/agents/` contains only the default worker and reviewer subagent examples. Planner, monitor, verifier, and grounder behavior stay in skills/controller commands until a failure trace justifies an isolated role.
- `.claude/skills/` contains Claude-native skill packages. These skills may draft or inspect artifacts, but lifecycle state is owned by the controller.
