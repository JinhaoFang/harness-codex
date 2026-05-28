#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

DANGEROUS_PATTERNS = [
    (re.compile(r"\brm\s+-rf\s+(/|~|\$HOME)(\s|$)"), "Refuse recursive delete of root/home."),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "Hard reset requires explicit human approval."),
    (re.compile(r"\bgit\s+push\b.*\s--force\b"), "Force push requires explicit human approval."),
    (re.compile(r"\bgit\s+push\b.*\b(main|master)\b"), "Direct push to main/master is blocked by harness policy."),
    (re.compile(r"\b(drop\s+database|truncate\s+table)\b", re.IGNORECASE), "Destructive database operation requires human gate."),
    (re.compile(r"\b(openai|anthropic|aws|gcp|azure)_?(api|secret|access)?_?key\b", re.IGNORECASE), "Potential secret handling requires explicit policy."),
]

ASK_PATTERNS = [
    (re.compile(r"\b(npm|pnpm|yarn)\s+publish\b"), "Publishing packages requires human confirmation."),
    (re.compile(r"\b(terraform|pulumi)\s+apply\b"), "Infrastructure apply requires human confirmation."),
    (re.compile(r"\b(kubectl|helm)\s+.*\b(apply|delete|upgrade)\b"), "Cluster mutation requires human confirmation."),
]


def load_event() -> Dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def extract_command(event: Dict[str, Any]) -> Tuple[str, str]:
    tool_name = str(event.get("tool_name") or event.get("toolName") or event.get("tool") or "")
    tool_input = event.get("tool_input") or event.get("toolInput") or event.get("input") or {}
    if isinstance(tool_input, dict):
        command = tool_input.get("command") or tool_input.get("cmd") or tool_input.get("script") or ""
    else:
        command = str(tool_input)
    return tool_name, str(command)


def policy_decision(tool_name: str, command: str) -> Tuple[str, str]:
    if tool_name and tool_name.lower() not in {"bash", "shell", "terminal", "exec", "run_command"}:
        return "allow", ""
    normalized = " ".join(command.split())
    for pattern, reason in DANGEROUS_PATTERNS:
        if pattern.search(normalized):
            return "deny", reason
    for pattern, reason in ASK_PATTERNS:
        if pattern.search(normalized):
            return "ask", reason
    return "allow", ""


def emit_pre_tool_use(decision: str, reason: str, *, platform: str = "codex") -> int:
    """Emit a platform-specific PreToolUse response.

    Codex PreToolUse currently supports deny, additional context, and allow with
    updatedInput. It does not support permissionDecision=ask or the legacy
    decision=approve shape. Claude Code supports ask, but this shared policy is
    used as a deterministic guardrail, so ask-class commands are blocked with a
    clear human-approval instruction unless a platform-specific permission hook
    handles them.
    """
    if decision == "deny":
        out: Dict[str, Any] = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            },
        }
    elif decision == "ask":
        msg = reason + " Use the platform permission request or explicit human gate; PreToolUse must not emit ask."
        if platform == "claude":
            out = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": reason,
                },
            }
        else:
            out = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": msg,
                },
            }
    else:
        # Exit 0 with no output lets the native permission flow continue.
        return 0
    print(json.dumps(out))
    return 0


def emit_permission_request(decision: str, reason: str) -> int:
    """Emit Codex PermissionRequest output. No output means normal approval UI."""
    if decision == "deny":
        out: Dict[str, Any] = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "deny", "message": reason},
            },
        }
    elif decision == "allow":
        out = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "allow"},
            },
        }
    else:
        return 0
    print(json.dumps(out))
    return 0


# Backward-compatible alias for older tests or adopters.
def emit(decision: str, reason: str) -> int:
    return emit_pre_tool_use(decision, reason, platform=os.environ.get("HARNESS_HOOK_PLATFORM", "codex"))
