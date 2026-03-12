#!/usr/bin/env python3
"""Apply a Final Review/Close record into the workflow markdown.

Compatible with both workflow templates:
- V2: heading contains "Final Review / Close"
- V3: heading contains "Final Review / Archive"

Exit code:
  0 success
  2 failure
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def find_heading(lines: list[str]) -> int | None:
    for i, ln in enumerate(lines):
        if not ln.startswith("## "):
            continue
        title = ln.removeprefix("## ").strip()
        if "Final Review" in title:
            return i
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", required=True)
    ap.add_argument("--record", default="", help="Path to a markdown snippet. If omitted, read from stdin")
    args = ap.parse_args()

    wf = Path(args.workflow)
    if not wf.exists():
        print(f"ERROR: workflow not found: {wf}")
        sys.exit(2)

    rec = Path(args.record).read_text(encoding="utf-8") if args.record else sys.stdin.read()
    rec = rec.strip("\n")
    if not rec:
        print("ERROR: empty record")
        sys.exit(2)

    text = wf.read_text(encoding="utf-8")
    lines = text.splitlines()

    heading = find_heading(lines)
    if heading is None:
        print("ERROR: close section not found (searched 'Final Review' heading)")
        sys.exit(2)

    j = heading + 1
    while j < len(lines):
        if lines[j].startswith("## ") and j != heading:
            break
        j += 1

    new_lines = lines[: heading + 1]
    new_lines.append("")
    new_lines.extend(rec.splitlines())
    new_lines.append("")
    new_lines.extend(lines[j:])

    wf.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")
    print("[OK] applied close record")


if __name__ == "__main__":
    main()
