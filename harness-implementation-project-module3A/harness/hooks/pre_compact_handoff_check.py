#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


def root() -> Path:
    found = find_harness_root(Path.cwd().resolve()) or find_harness_root(Path(__file__).resolve().parents[2])
    if found:
        return found
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip()).resolve()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return Path.cwd().resolve()


def find_harness_root(start: Path) -> Optional[Path]:
    cur = start if start.is_dir() else start.parent
    while True:
        if (cur / ".harness" / "config.json").exists() and (cur / "harness" / "cli" / "harnessctl.py").exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent


def current_work_unit_id(base: Path) -> Optional[str]:
    cur = base / ".harness" / "current"
    if not cur.exists():
        return None
    value = cur.read_text(encoding="utf-8").strip()
    return value or None


def has_changes(base: Path) -> bool:
    try:
        out = subprocess.run(["git", "status", "--short"], cwd=base, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, timeout=5)
        return bool(out.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def main() -> int:
    base = root()
    wu_id = current_work_unit_id(base)
    if not wu_id or not has_changes(base):
        return 0
    handoff = base / ".harness" / "work-units" / "active" / wu_id / "handoff.md"
    if handoff.exists() and "Not generated yet" not in handoff.read_text(encoding="utf-8"):
        return 0
    reason = "Active Work Unit has local changes and no generated handoff. Run `harnessctl handoff --id %s --next-safe-action ...` before compacting or handing off." % wu_id
    print(json.dumps({"continue": False, "stopReason": reason, "systemMessage": reason}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
