# Contributing to Agentic Codex Runtime v3

Thank you for your interest in contributing! This document outlines the process and guidelines.

## Development Setup

1. Fork and clone the repository
2. Python 3.9+ is required
3. No external dependencies — the controller (`agentctl.py`) uses only the Python standard library

## How to Contribute

### Report Issues

- Open a [GitHub Issue](../../issues/new) with a clear title and description
- Include reproduction steps, expected behavior, and actual behavior

### Submit Changes

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

2. Make your changes with clear, focused commits

3. Run tests to verify nothing is broken:
   ```bash
   cd agentic_codex_runtime_v3_fusion
   python -m pytest tests/ -v
   ```

4. Push and open a Pull Request against `main`

### Commit Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new skill for X
fix: correct gate check in agentctl
docs: update spec 07 with clarification
refactor: restructure skill directory
chore: update CI workflow
```

## Code Guidelines

- **Minimal changes** — Prefer reusing existing code paths; mark DRY violations
- **Controller determinism** — `agentctl.py` must remain deterministic; no AI/model calls inside it
- **Skill isolation** — Each skill is self-contained in its own directory with a `SKILL.md`
- **Test coverage** — New features must include tests; behavior verification and edge cases should not be omitted
- **File size** — Keep files under 1000 lines; if exceeding, provide a split rationale

## Project Structure

- `agentic_codex_runtime_v3_fusion/` — Main runtime package
  - `.codex/tools/agentctl.py` — Controller (deterministic state machine)
  - `.agents/skills/` — Skill definitions
  - `docs/agentic/spec/` — Design specifications
  - `tests/` — Test suite
- `docs/` — Reference materials and migration guides

## Review Process

- At least one review is required before merge
- Reviewers check: correctness, spec compliance, test coverage, and minimal diff principle

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
