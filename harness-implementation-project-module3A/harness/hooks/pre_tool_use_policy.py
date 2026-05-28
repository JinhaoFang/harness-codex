#!/usr/bin/env python3
from __future__ import annotations

from policy_common import emit, extract_command, load_event, policy_decision


def main() -> int:
    event = load_event()
    tool_name, command = extract_command(event)
    decision, reason = policy_decision(tool_name, command)
    return emit(decision, reason)


if __name__ == "__main__":
    raise SystemExit(main())
