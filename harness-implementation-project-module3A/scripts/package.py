#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
out = root.parent / f"{root.name}.zip"
if out.exists():
    out.unlink()
shutil.make_archive(str(out.with_suffix("")), "zip", root)
print(out)
