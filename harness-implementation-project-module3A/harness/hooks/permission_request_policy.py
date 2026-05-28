#!/usr/bin/env python3
from __future__ import annotations

from policy_common import emit_permission_request, extract_command, load_event, policy_decision


def main() -> int:
    event = load_event()
    tool_name, command = extract_command(event)
    decision, reason = policy_decision(tool_name, command)
    # PermissionRequest is where Codex can decide allow/deny or stay undecided.
    # Ask-class commands should fall through to the normal approval prompt, not be
    # auto-approved by this hook.
    if decision == "deny":
        return emit_permission_request("deny", reason)
    return emit_permission_request("undecided", "")


if __name__ == "__main__":
    raise SystemExit(main())
