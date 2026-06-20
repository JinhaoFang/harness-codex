#!/usr/bin/env python3
"""Emit small recovery/routing context at session and subagent boundaries."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


def load_event() -> Dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def find_root(start: Path) -> Path:
    cur = start.resolve()
    while True:
        if (cur / "harness" / "cli" / "harnessctl.py").exists():
            return cur
        if cur.parent == cur:
            return start.resolve()
        cur = cur.parent


def context(base: Path, event_name: str, event: Dict[str, Any]) -> str:
    sys.path.insert(0, str(base / "harness" / "cli"))
    import harnessctl  # type: ignore

    try:
        work_unit_id, wu_path = harnessctl.resolve_wu(base, None)
    except Exception:
        return "Harness: no active local Work Unit. For non-trivial coding work, use harness-clarify and harness-spec before implementation."
    state = harnessctl.load_json(harnessctl.state_path(wu_path), {})
    status = state.get("status", "unknown")
    spec = state.get("spec_path", f"docs/spec/{work_unit_id}.md")
    plan = state.get("plan_path", f".harness/work-units/active/{work_unit_id}/plan.md")
    next_action = state.get("next_safe_action", "read the tracked spec and current repository")
    if event_name == "SubagentStart":
        agent_type = str(event.get("agent_type") or event.get("agentType") or "subagent").lower()
        role = "reviewer (read-only)" if "review" in agent_type else "worker" if "worker" in agent_type else agent_type
        return f"Harness subagent: Work Unit {work_unit_id}, status={status}, role={role}. Read {spec}; read {plan} when present; re-ground in current code. Next safe action: {next_action}."
    return f"Harness recovery: Work Unit {work_unit_id}, status={status}. Intent: {spec}. Local plan: {plan}. Re-read current Git/code/evidence rather than trusting chat memory. Next safe action: {next_action}."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("event", choices=["SessionStart", "SubagentStart", "PostCompact"])
    args = parser.parse_args()
    event = load_event()
    base = find_root(Path(str(event.get("cwd") or Path.cwd())))
    message = context(base, args.event, event)
    if args.event == "PostCompact":
        print(json.dumps({"systemMessage": message}))
    else:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": args.event, "additionalContext": message}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
