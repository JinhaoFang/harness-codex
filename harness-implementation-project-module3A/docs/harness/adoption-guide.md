# Adoption and upgrade guide

Install incrementally into an existing repository:

```bash
python3 scripts/adopt.py install /path/to/repo --profile codex
python3 scripts/adopt.py install /path/to/repo --profile claude
python3 scripts/adopt.py install /path/to/repo --profile thin-shared-codex
python3 scripts/adopt.py install /path/to/repo --profile thin-shared-claude
```

Use `--dry-run` first when the repository already has agent configuration.

## Ownership model

Installation writes `.harness-adoption.json`, a small tracked manifest containing hashes for assets that were safely installed or already exactly matched the source. It does **not** contain active Work Unit state.

- Missing assets are copied and managed.
- Existing identical assets become managed.
- Existing different repository-owned files are left untouched and are not claimed.
- `AGENTS.md` / `CLAUDE.md` use bounded marker blocks.
- Harness-owned local assets are added to `.gitignore`: `.harness/`, `docs/harness/`, `harness/`, `harnessctl`, `.codex`, and `.claude`.

## Check and upgrade

```bash
python3 scripts/adopt.py check /path/to/repo
python3 scripts/adopt.py upgrade /path/to/repo --dry-run
python3 scripts/adopt.py upgrade /path/to/repo
```

Upgrade overwrites a managed file only when its current hash still equals the previous installed hash. A local edit causes a visible conflict and no overwrite. Removed source assets are retained until an explicit migration; upgrade never silently deletes repository files.

Run the `adopt.py` from the new Harness source/package and point it at the target repository.

## Installed surfaces

Common tracked assets include `docs/harness`, `docs/spec/README.md`, controller/core/hooks/platforms/schemas/templates, canonical skills, adoption/sync scripts, and target-safe CI / Makefile assets when the target does not already own them.

Platform assets:

| Profile | Assets |
|---|---|
| Codex | bounded `AGENTS.md` block, `.codex/`, `.agents/skills/` |
| Claude Code | bounded `CLAUDE.md` block, `.claude/` |
| Thin shared Codex | bounded `AGENTS.md` block, `.codex/`, `.agents/skills/`, `harness.lock`, `harness/project.yaml`, minimal docs |
| Thin shared Claude Code | bounded `CLAUDE.md` block, `.claude/skills/`, `.claude/settings.json`, `harness.lock`, `harness/project.yaml`, minimal docs |

## After installation

1. Replace project-map placeholders in the bounded entrypoint block.
2. Review permissions, hook commands, and required validation entrypoints.
3. Run `adopt.py check`, `harnessctl doctor`, and skill checks. Run the repository's own product tests separately.
4. Pilot one low-risk Work Unit before broad adoption.

Never copy or commit active `.harness/` state. Team handover uses the tracked Spec, Git/GitHub, and current code; a new workspace reconstructs local runtime conservatively.
