#!/usr/bin/env python3
"""Apply a Plan Review record into the workflow markdown.

Supports the "reviewer is read-only" constraint:
- reviewer outputs the record in chat (structured block)
- main agent pastes it into a temp file and runs this script

Compatible with both workflow templates:
- V2: "## 7) Plan Review（独立 reviewer 填写）"
- V3: "## 10) Plan Review（由主 agent 回填 reviewer 原文）"

Exit code:
  0 success
  2 failure (section not found / invalid input)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


CANDIDATE_SECTION_TITLES = [
    "7) Plan Review（独立 reviewer 填写）",
    "10) Plan Review（由主 agent 回填 reviewer 原文）",
]


def find_heading(lines: list[str]) -> int | None:
    for i, ln in enumerate(lines):
        if not ln.startswith("## "):
            continue
        title = ln.removeprefix("## ").strip()
        if title in CANDIDATE_SECTION_TITLES:
            return i
        # fallback: contains match
        if "Plan Review" in title:
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

    if args.record:
        rec = Path(args.record).read_text(encoding="utf-8")
    else:
        rec = sys.stdin.read()

    rec = rec.strip("\n")
    if not rec:
        print("ERROR: empty record")
        sys.exit(2)

    text = wf.read_text(encoding="utf-8")
    lines = text.splitlines()

    heading = find_heading(lines)
    if heading is None:
        print("ERROR: plan review section not found (searched Plan Review headings)")
        sys.exit(2)

    # find next heading
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
    print("[OK] applied plan review record")


if __name__ == "__main__":
    main()
