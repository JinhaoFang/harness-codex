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


def emit(decision: str, reason: str) -> int:
    # Codex PreToolUse requires hookSpecificOutput.hookEventName. The top-level
    # decision is limited to approve/block. Codex does not accept
    # permissionDecision=allow, so plain approval omits hookSpecificOutput.
    if decision == "deny":
        out: Dict[str, Any] = {
            "decision": "block",
            "reason": reason,
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            },
        }
    elif decision == "ask":
        out = {
            "decision": "approve",
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason": reason,
            },
        }
    else:
        out = {"decision": "approve"}
    print(json.dumps(out))
    return 0
