# Adoption guide

Install incrementally into an existing repository:

```bash
python3 scripts/adopt.py install /path/to/repo --profile codex
python3 scripts/adopt.py install /path/to/repo --profile claude
```

Use `--dry-run` first in repositories with existing agent configuration.

## What is installed

Common tracked assets:

```text
docs/harness/
docs/spec/README.md
harness/cli/
harness/hooks/
harness/schemas/
harness/templates/
harness/tests/
.github/workflows/harness-checks.yml
Makefile
```

Platform assets:

| Profile | Assets |
|---|---|
| Codex | concise `AGENTS.md` block, `.codex/`, `.agents/skills/` |
| Claude Code | concise `CLAUDE.md` block, `.claude/` |

Only `.harness/` is appended to `.gitignore`. Harness implementation, skills, CI and tracked specs remain visible to Git.

## After installation

1. Replace the project-map placeholders in `AGENTS.md` or `CLAUDE.md`.
2. Review platform permissions and hook commands.
3. Add project-specific build/test/lint entrypoints.
4. Run:

```bash
python3 harness/cli/harnessctl.py doctor
python3 harness/cli/harnessctl.py check --gate skills --strict
python3 -m unittest discover -s harness/tests
```

5. Create one low-risk pilot Work Unit before enabling the workflow broadly.

Do not copy active `.harness/` state between repositories or commit it. For team handover, commit the approved spec and use Git/GitHub; the next workspace rebuilds local runtime with `resume`.
