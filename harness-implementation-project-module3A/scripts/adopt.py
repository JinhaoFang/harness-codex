#!/usr/bin/env python3
"""Copy the portable thin harness layer into another repository."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil

DEFAULT_PATHS = [
    "AGENTS.md",
    "CLAUDE.md",
    "docs/harness",
    "harness/cli",
    "harness/hooks",
    "harness/schemas",
    "harness/templates",
    "skills/harness-clarify",
    "skills/harness-evidence",
    "skills/harness-handoff",
]


def copy_path(src_root: Path, dst_root: Path, rel: str, force: bool) -> None:
    src = src_root / rel
    dst = dst_root / rel
    if not src.exists():
        return
    if dst.exists():
        if not force:
            print(f"skip existing {rel}")
            return
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    print(f"copied {rel}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    src_root = Path(__file__).resolve().parents[1]
    dst_root = args.target.resolve()
    for rel in DEFAULT_PATHS:
        copy_path(src_root, dst_root, rel, args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
