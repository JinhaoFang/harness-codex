#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    base = Path.cwd()
    cur = base / ".harness" / "current"
    if not cur.exists():
        return 0
    wu_id = cur.read_text(encoding="utf-8").strip()
    handoff = base / ".harness" / "work-units" / "active" / wu_id / "handoff.md"
    if handoff.exists() and "Not generated yet" not in handoff.read_text(encoding="utf-8"):
        return 0
    reason = "Active Work Unit has no generated handoff. For cross-session work, run `harnessctl handoff --id <WU-ID> --next-safe-action ...`."
    print(reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
