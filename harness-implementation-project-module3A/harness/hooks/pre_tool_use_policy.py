#!/usr/bin/env python3
from __future__ import annotations

import argparse

from policy_common import emit_pre_tool_use, extract_command, load_event, policy_decision


def main() -> int:
    parser = argparse.ArgumentParser(description="Harness PreToolUse policy hook")
    parser.add_argument("--platform", choices=["codex", "claude"], default="codex")
    args = parser.parse_args()
    event = load_event()
    tool_name, command = extract_command(event)
    decision, reason = policy_decision(tool_name, command)
    return emit_pre_tool_use(decision, reason, platform=args.platform)


if __name__ == "__main__":
    raise SystemExit(main())
