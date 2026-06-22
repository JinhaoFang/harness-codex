#!/usr/bin/env python3
"""Atomically refresh the recovery checkpoint before context compaction."""
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
        harnessctl.update_state(root, wu_path, checkpoint_reason="pre_compact")
        checkpoint = harnessctl.checkpoint_core.checkpoint_path(wu_path).relative_to(root).as_posix()
    except Exception as exc:
        # Compaction remains available when there is no active Work Unit. A real
        # active-state write failure is surfaced rather than disguised as success.
        if "No Work Unit" in str(exc) or "Work Unit not found" in str(exc):
            return 0
        print(json.dumps({"continue": True, "systemMessage": f"Harness could not refresh the pre-compaction checkpoint: {exc}"}))
        return 0
    print(json.dumps({"continue": True, "systemMessage": f"Harness refreshed {checkpoint} for Work Unit {work_unit_id}. Resume from tracked spec, current Git/code, and this checkpoint."}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
