#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

sys.dont_write_bytecode = True

from hook_sound import play as play_hook_sound


def load_event() -> Dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def root(event: Dict[str, Any]) -> Path:
    starts = []
    cwd = event.get("cwd")
    if cwd:
        starts.append(Path(str(cwd)).resolve())
    starts.append(Path.cwd().resolve())
    starts.append(Path(__file__).resolve().parents[2])
    for start in starts:
        found = find_harness_root(start)
        if found:
            return found
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip()).resolve()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return Path.cwd().resolve()


def find_harness_root(start: Path) -> Optional[Path]:
    cur = start if start.is_dir() else start.parent
    while True:
        if (cur / ".harness" / "config.json").exists() and (cur / "harness" / "cli" / "harnessctl.py").exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent


def current_work_unit_id(base: Path) -> Optional[str]:
    cur = base / ".harness" / "current"
    if not cur.exists():
        return None
    value = cur.read_text(encoding="utf-8").strip()
    return value or None


def load_state(base: Path, wu_id: str) -> Dict[str, Any]:
    state_path = base / ".harness" / "work-units" / "active" / wu_id / "state.json"
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def context_for_event(base: Path, event_name: str, event: Dict[str, Any]) -> str:
    if event_name == "SubagentStart":
        play_hook_sound("subagent")
    wu_id = current_work_unit_id(base)
    if not wu_id:
        if event_name == "UserPromptSubmit":
            return (
                "Harness routing: no active Work Unit. For non-trivial coding work, first use harness-clarify "
                "and harness-spec before editing. For trivial work, keep the evidence note lightweight."
            )
        return "Harness routing: no active Work Unit. Read AGENTS.md/CLAUDE.md as the short project map before editing."
    state = load_state(base, wu_id)
    status = state.get("status", "unknown")
    next_action = state.get("next_safe_action", "read contract.md and current state")
    changed = state.get("changed_files", [])[-8:]
    changed_text = ", ".join(changed) if changed else "none recorded"
    if event_name == "SubagentStart":
        agent_type = str(event.get("agent_type") or event.get("agentType") or "subagent")
        role_note = ""
        if "review" in agent_type.lower():
            role_note = " Reviewer must not ask the user by default; return PASS/CHANGES_REQUESTED/BLOCKED/NEEDS_HUMAN_GATE with concrete findings."
        elif "worker" in agent_type.lower():
            role_note = " Worker must implement only inside the Work Unit write boundary and record evidence."
        return (
            f"Harness subagent context: active Work Unit {wu_id}, status={status}. "
            f"Read .harness/work-units/active/{wu_id}/contract.md and state.json first. "
            f"Next safe action: {next_action}.{role_note}"
        )
    if event_name in {"PostCompact", "SessionStart"}:
        return (
            f"Harness recovery context: active Work Unit {wu_id}, status={status}. "
            f"Read contract.md, state.json, latest evidence, and handoff if present. "
            f"Recent changed files: {changed_text}. Next safe action: {next_action}."
        )
    return (
        f"Harness context: active Work Unit {wu_id}, status={status}. "
        f"Use contract.md as task truth; state.json is lifecycle authority. Next safe action: {next_action}."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit lightweight harness context for agent lifecycle hooks")
    parser.add_argument("event", choices=["SessionStart", "UserPromptSubmit", "SubagentStart", "PostCompact"])
    args = parser.parse_args()
    event = load_event()
    base = root(event)
    additional = context_for_event(base, args.event, event)
    if args.event == "PostCompact":
        print(json.dumps({"systemMessage": additional}))
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": args.event,
            "additionalContext": additional,
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
