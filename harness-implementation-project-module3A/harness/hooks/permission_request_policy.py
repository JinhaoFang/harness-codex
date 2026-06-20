#!/usr/bin/env python3
from __future__ import annotations

from policy_common import command_policy, emit_permission_request, extract_command, load_event


def main() -> int:
    event = load_event()
    tool_name, command = extract_command(event)
    decision, reason = command_policy(tool_name, command)
    # Ask-class commands intentionally produce no decision, preserving Codex's
    # normal approval prompt. Only deterministic deny rules are enforced here.
    if decision == "deny":
        return emit_permission_request("deny", reason)
    return emit_permission_request("undecided", "")


if __name__ == "__main__":
    raise SystemExit(main())
