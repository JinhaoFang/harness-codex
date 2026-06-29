#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from policy_common import (
    command_policy,
    emit_pre_tool_use,
    extract_command,
    load_event,
    phase_command_policy,
    phase_write_policy,
)


def find_root(start: Path) -> Path:
    cur = start.resolve()
    while True:
        if (cur / "harness" / "cli" / "harnessctl.py").exists():
            return cur
        if cur.parent == cur:
            return start.resolve()
        cur = cur.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Harness PreToolUse policy hook")
    parser.add_argument("--platform", choices=["codex", "claude"], default="codex")
    args = parser.parse_args()
    event = load_event()
    root = find_root(Path(str(event.get("cwd") or Path.cwd())))
    tool_name, command = extract_command(event)
    decision, reason = command_policy(tool_name, command)
    if decision == "allow":
        decision, reason = phase_command_policy(root, event)
    if decision == "allow":
        decision, reason = phase_write_policy(root, event)
    return emit_pre_tool_use(decision, reason, platform=args.platform)


if __name__ == "__main__":
    raise SystemExit(main())
