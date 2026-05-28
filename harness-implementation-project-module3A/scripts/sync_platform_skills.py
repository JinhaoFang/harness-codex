#!/usr/bin/env python3
"""Sync canonical harness skills into Codex and Claude Code locations."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "skills"
TARGETS = [ROOT / ".agents" / "skills", ROOT / ".claude" / "skills"]


def sync() -> None:
    skills = sorted(p for p in CANONICAL.glob("harness-*") if (p / "SKILL.md").exists())
    if not skills:
        raise SystemExit("No canonical harness skills found under skills/harness-*/SKILL.md")
    for target in TARGETS:
        target.mkdir(parents=True, exist_ok=True)
        for old in target.glob("harness-*"):
            if old.is_dir():
                shutil.rmtree(old)
        for skill in skills:
            shutil.copytree(skill, target / skill.name)
    print(f"Synced {len(skills)} skills to {', '.join(str(t.relative_to(ROOT)) for t in TARGETS)}")


if __name__ == "__main__":
    sync()
