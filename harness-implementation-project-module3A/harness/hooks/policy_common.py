#!/usr/bin/env python3
"""Shared deterministic policy helpers for platform lifecycle hooks.

Hooks are defense in depth. The controller and platform sandbox remain the
stronger boundaries because hook interception is platform-dependent.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

DANGEROUS_PATTERNS = [
    (re.compile(r"\brm\s+-rf\s+(/|~|\$HOME)(\s|$)"), "Refuse recursive delete of root/home."),
    (re.compile(r"\bgit\s+reset\s+--hard\b"), "Hard reset requires explicit human approval."),
    (re.compile(r"\bgit\s+push\b.*\s--force(?:-with-lease)?\b"), "Force push requires explicit human approval."),
    (re.compile(r"\bgit\s+push\b.*\b(main|master)\b"), "Direct push to main/master is blocked by harness policy."),
    (re.compile(r"\b(drop\s+database|truncate\s+table)\b", re.IGNORECASE), "Destructive database operation requires a human gate."),
]
ASK_PATTERNS = [
    (re.compile(r"\b(npm|pnpm|yarn)\s+publish\b"), "Publishing packages requires human confirmation."),
    (re.compile(r"\b(terraform|pulumi)\s+(apply|up)\b"), "Infrastructure mutation requires human confirmation."),
    (re.compile(r"\b(kubectl|helm)\s+.*\b(apply|delete|upgrade)\b"), "Cluster mutation requires human confirmation."),
]
# Conservative indicators used only before implementation and in read-only roles.
# This cannot detect arbitrary programs that write files; sandbox/path policy and
# the controller scope gate remain required.
MUTATING_SHELL_PATTERNS = [
    re.compile(r"(^|[;&|]\s*)(rm|mv|cp|touch|mkdir|install|truncate)\b"),
    re.compile(r"\b(sed\s+-[^\n]*i|perl\s+-[^\n]*i)\b"),
    re.compile(r"(^|[;&|]\s*)tee\b"),
    re.compile(r"(^|[^>])>{1,2}(?!>)"),
    re.compile(r"\bgit\s+(apply|checkout|switch|restore|reset|clean|commit|merge|rebase|cherry-pick)\b"),
    re.compile(r"(^|[;&|]\s*)(patch|apply_patch)\b"),
    re.compile(r"\b(npm|pnpm|yarn|pip|uv|poetry|cargo|go)\s+(install|add|remove|update|fmt|format)\b"),
]
WRITE_TOOLS = {"edit", "write", "multiedit", "apply_patch", "patch"}
SHELL_TOOLS = {"bash", "shell", "terminal", "exec", "run_command", "unified_exec"}
PRE_IMPLEMENTATION_STATUSES = {"clarifying", "spec_approved", "planning", "plan_reviewing", "ready"}
READ_ONLY_STATUSES = {"reviewing", "handoff", "archived"}


def load_event() -> Dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def tool_input(event: Dict[str, Any]) -> Any:
    return event.get("tool_input") or event.get("toolInput") or event.get("input") or {}


def extract_command(event: Dict[str, Any]) -> Tuple[str, str]:
    tool_name = str(event.get("tool_name") or event.get("toolName") or event.get("tool") or "")
    value = tool_input(event)
    if isinstance(value, dict):
        command = value.get("command") or value.get("cmd") or value.get("script") or ""
    else:
        command = str(value)
    return tool_name, str(command)


def _patch_paths(command: str) -> List[str]:
    paths: List[str] = []
    patterns = [
        r"^\*\*\* (?:Update|Add|Delete) File:\s*(.+?)\s*$",
        r"^(?:\+\+\+|---)\s+(?:[ab]/)?(.+?)\s*$",
    ]
    for line in command.splitlines():
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                value = match.group(1).strip()
                if value != "/dev/null":
                    paths.append(value)
                break
    return paths


def extract_paths(event: Dict[str, Any]) -> List[str]:
    value = tool_input(event)
    paths: List[str] = []
    if not isinstance(value, dict):
        return paths
    for key in ("file_path", "filePath", "path", "target_path", "targetPath"):
        if value.get(key):
            paths.append(str(value[key]))
    edits = value.get("edits") or value.get("changes") or []
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict):
                for key in ("file_path", "filePath", "path"):
                    if edit.get(key):
                        paths.append(str(edit[key]))
    command = value.get("command")
    if command:
        paths.extend(_patch_paths(str(command)))
    return list(dict.fromkeys(paths))


def command_policy(tool_name: str, command: str) -> Tuple[str, str]:
    if tool_name and tool_name.lower() not in SHELL_TOOLS:
        return "allow", ""
    normalized = " ".join(command.split())
    for pattern, reason in DANGEROUS_PATTERNS:
        if pattern.search(normalized):
            return "deny", reason
    for pattern, reason in ASK_PATTERNS:
        if pattern.search(normalized):
            return "ask", reason
    return "allow", ""


def _controller(root: Path):
    sys.path.insert(0, str(root))
    try:
        from harness.cli import harnessctl  # type: ignore
        return harnessctl
    finally:
        try:
            sys.path.remove(str(root))
        except ValueError:
            pass


def _active_state(root: Path) -> Tuple[Any, Path, Dict[str, Any]] | None:
    try:
        ctl = _controller(root)
        _wu_id, wu_path = ctl.resolve_wu(root, None)
        return ctl, wu_path, ctl.load_json(ctl.state_path(wu_path), {})
    except Exception:
        return None


def _normalize_path(root: Path, raw: str) -> str:
    path = Path(raw)
    try:
        if path.is_absolute():
            return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
    return path.as_posix().lstrip("./")


def phase_write_policy(root: Path, event: Dict[str, Any]) -> Tuple[str, str]:
    tool_name = str(event.get("tool_name") or event.get("toolName") or event.get("tool") or "").lower()
    if tool_name not in WRITE_TOOLS:
        return "allow", ""
    paths = extract_paths(event)
    if not paths:
        # A write tool without an inspectable path cannot be safely authorized.
        return "deny", "Write tool input did not expose a path that the harness can authorize."
    active = _active_state(root)
    if active is None:
        return "allow", ""
    ctl, wu_path, state = active
    status = str(state.get("status", ""))
    spec_rel = str(state.get("spec_path", ""))
    plan_rel = str(state.get("plan_path", ""))
    normalized = [_normalize_path(root, path) for path in paths]

    if status == "clarifying":
        disallowed = [path for path in normalized if path != spec_rel]
        if disallowed:
            return "deny", f"Clarification phase may only edit the tracked spec {spec_rel}; blocked: {', '.join(disallowed)}"
        return "allow", ""

    if status in {"spec_approved", "planning", "plan_reviewing"}:
        allowed = {spec_rel, plan_rel}
        disallowed = [path for path in normalized if path not in allowed]
        if disallowed:
            return "deny", f"Planning phase may only edit the tracked spec or local plan; blocked: {', '.join(disallowed)}"
        return "allow", ""

    if status == "ready":
        return "deny", "Plan review passed, but implementation has not started. Run `harnessctl start-work` before editing product files."

    if status == "blocked":
        allowed = {spec_rel, plan_rel}
        disallowed = [path for path in normalized if path not in allowed]
        if disallowed:
            return "deny", f"Blocked work may only revise the tracked spec or local plan before an explicit resume; blocked: {', '.join(disallowed)}"
        return "allow", ""

    if status in READ_ONLY_STATUSES:
        return "deny", f"Work Unit status {status} is read-only for product files. Return findings to the worker or reopen the implementation phase."

    if status in {"running", "verifying"}:
        allowed_patterns, forbidden_patterns = ctl.scope_patterns(wu_path)
        for path in normalized:
            if path in {plan_rel, spec_rel}:
                return "deny", "Spec or plan changes during implementation require stopping and using the amendment/review flow."
            if forbidden_patterns and ctl.glob_matches(path, forbidden_patterns):
                return "deny", f"Path is explicitly out of bounds: {path}"
            if allowed_patterns and not ctl.glob_matches(path, allowed_patterns):
                return "deny", f"Path is outside the approved write boundary: {path}"
    return "allow", ""


def _has_shell_composition(command: str) -> bool:
    """Detect shell composition/expansion outside a single-quoted literal.

    Controller lifecycle commands receive a narrow exception from phase write
    blocking. The exception is safe only when the *entire* shell input is one
    direct controller argv. A substring check would let an attacker append
    ``; rm ...`` or ``&& ...`` after an otherwise legitimate command.
    """
    quote = ""
    escaped = False
    index = 0
    while index < len(command):
        char = command[index]
        if escaped:
            escaped = False
            index += 1
            continue
        if quote == "'":
            if char == "'":
                quote = ""
            index += 1
            continue
        if char == "\\":
            escaped = True
            index += 1
            continue
        if char == "'":
            quote = "'"
            index += 1
            continue
        if char == '"':
            quote = "" if quote == '"' else '"'
            index += 1
            continue
        # Command substitution is active outside single quotes, including
        # inside double quotes. Backticks are equivalent.
        if char == "`" or (char == "$" and index + 1 < len(command) and command[index + 1] == "("):
            return True
        if not quote and (char in ";&|<>" or char in "\r\n"):
            return True
        index += 1
    return bool(quote) or escaped


def _is_single_controller_command(command: str) -> bool:
    if _has_shell_composition(command):
        return False
    try:
        argv = shlex.split(command, posix=True)
    except ValueError:
        return False
    if not argv:
        return False
    first = Path(argv[0]).name.lower()
    if first in {"python", "python3", "python.exe", "python3.exe", "py"}:
        if len(argv) < 2:
            return False
        script = argv[1].replace("\\", "/")
        return script == "harness/cli/harnessctl.py" or script.endswith("/harness/cli/harnessctl.py")
    return first in {"harnessctl", "harnessctl.py"}


def phase_command_policy(root: Path, event: Dict[str, Any]) -> Tuple[str, str]:
    tool_name, command = extract_command(event)
    if tool_name.lower() not in SHELL_TOOLS or not command.strip():
        return "allow", ""
    active = _active_state(root)
    if active is None:
        return "allow", ""
    _ctl, _wu_path, state = active
    status = str(state.get("status", ""))
    normalized = " ".join(command.split())
    # Controller commands are the authorized way to update runtime lifecycle
    # data, but only when the complete shell input is one direct controller
    # argv. Merely containing the word harnessctl grants no exception.
    is_controller_command = _is_single_controller_command(command)
    mutates = any(pattern.search(command) for pattern in MUTATING_SHELL_PATTERNS)
    if not mutates or is_controller_command:
        return "allow", ""
    if status in PRE_IMPLEMENTATION_STATUSES:
        return "deny", f"Shell mutation is blocked while Work Unit status is {status}; finish spec and plan approval first."
    if status == "blocked":
        return "deny", "Shell mutation is blocked while the Work Unit is blocked; revise spec/plan through inspectable file tools or explicitly resume the lifecycle."
    if status in READ_ONLY_STATUSES:
        return "deny", f"Shell mutation is blocked while Work Unit status is {status}."
    return "allow", ""


def emit_pre_tool_use(decision: str, reason: str, *, platform: str = "codex") -> int:
    if decision == "allow":
        return 0
    if decision == "ask" and platform == "claude":
        output = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask", "permissionDecisionReason": reason}}
    else:
        if decision == "ask":
            reason += " Use the platform approval UI; Codex PreToolUse does not support ask."
        output = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}
    print(json.dumps(output))
    return 0


def emit_permission_request(decision: str, reason: str) -> int:
    if decision == "deny":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": {"behavior": "deny", "message": reason}}}))
    elif decision == "allow":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PermissionRequest", "decision": {"behavior": "allow"}}}))
    # No output means Codex keeps its normal approval flow.
    return 0


def emit(decision: str, reason: str) -> int:
    return emit_pre_tool_use(decision, reason, platform=os.environ.get("HARNESS_HOOK_PLATFORM", "codex"))
