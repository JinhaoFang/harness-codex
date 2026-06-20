#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
out = root.parent / f"{root.name}.zip"
excluded_dirs = {".git", ".harness", "__pycache__", ".pytest_cache", ".venv"}
excluded_suffixes = {".pyc"}

if out.exists():
    out.unlink()
with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in excluded_dirs for part in rel.parts):
            continue
        if path.is_dir() or path.suffix in excluded_suffixes:
            continue
        archive.write(path, Path(root.name) / rel)
print(out)
