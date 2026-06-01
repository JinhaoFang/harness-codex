#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


SOUNDS = {
    "complete": ["Hero.aiff", "Glass.aiff", "Ping.aiff"],
    "subagent": ["Pop.aiff", "Tink.aiff", "Ping.aiff"],
}


def enabled() -> bool:
    if os.environ.get("HARNESS_HOOK_SOUND", "").lower() in {"0", "false", "no", "off"}:
        return False
    if os.environ.get("CI"):
        return False
    return sys.platform == "darwin"


def play(kind: str) -> None:
    if not enabled():
        return
    for name in SOUNDS.get(kind, []):
        sound = Path("/System/Library/Sounds") / name
        if not sound.exists():
            continue
        try:
            subprocess.Popen(
                ["afplay", str(sound)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError:
            return
        return


def main() -> int:
    kind = sys.argv[1] if len(sys.argv) > 1 else "complete"
    play(kind)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
