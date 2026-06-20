#!/usr/bin/env python3
"""Non-blocking session-pause reminder for Codex and Claude Code."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def find_root(start: Path) -> Path:
    cur = start.resolve()
    while True:
        if (cur / "harness" / "cli" / "harnessctl.py").exists():
            return cur
        if cur.parent == cur:
            return start.resolve()
        cur = cur.parent


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        event = {}
    root = find_root(Path(str(event.get("cwd") or Path.cwd())))
    sys.path.insert(0, str(root))
    try:
        from harness.cli import harnessctl
        work_unit_id, wu_path = harnessctl.resolve_wu(root, None)
    except Exception:
        return 0
    if not (wu_path / "handoff.md").exists():
        print(json.dumps({"continue": True, "systemMessage": f"Harness reminder: Work Unit {work_unit_id} has no local handoff. Session stop is allowed; generate one before handover."}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
