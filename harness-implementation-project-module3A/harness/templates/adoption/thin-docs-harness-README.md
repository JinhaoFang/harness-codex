# Project Harness Notes

This repository uses a thin shared Harness profile.

- Tracked intent lives in `docs/spec/`.
- Local runtime lives in ignored `.harness/`.
- The Harness controller, hooks, and platform adapters are provided by an externally installed `harnessctl`.
- Platform-specific Harness skills are installed into this repository and remain the routing surface for the project map.
- Project automation should call `harnessctl --root <repo> ...` or run from this repository root.

Use `AGENTS.md` / `CLAUDE.md` for the project map and repository-specific workflow guidance.
