#!/usr/bin/env python3
"""Emit small recovery/routing context at subagent and post-compaction boundaries."""
from __future__ import annotations

import argparse
import json
import os
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


def infer_role(agent_type: str) -> str:
    lowered = agent_type.lower()
    if "review" in lowered or lowered == "pr_explorer":
        return "reviewer"
    if "worker" in lowered:
        return "worker"
    return "conductor"


def context(base: Path, event_name: str, event: Dict[str, Any]) -> str:
    sys.path.insert(0, str(base))
    from harness.cli import harnessctl  # type: ignore

    try:
        work_unit_id, wu_path = harnessctl.resolve_wu(base, None)
    except Exception:
        return "Harness: no active local Work Unit. For non-trivial coding work, ground via harness-ground first, then use harness-clarify and harness-spec before implementation."
    state = harnessctl.load_json(harnessctl.state_path(wu_path), {})
    status = state.get("status", "unknown")
    platform_session = str(event.get("session_id") or event.get("thread_id") or "").strip()
    if platform_session and event_name == "SubagentStart":
        agent_type = str(event.get("agent_type") or event.get("agentType") or "").lower()
        role = os.environ.get("HARNESS_ROLE", "").strip().lower()
        if not role:
            role = infer_role(agent_type)
        try:
            binding = harnessctl.session_core.record(
                base,
                event,
                work_unit_id=work_unit_id,
                role=role,
                observed_at=harnessctl.now_iso(),
            )
            harnessctl.update_state(base, wu_path, checkpoint_reason=f"{event_name.lower()}_session_bound", current_role=role)
            state["observed_logical_session_id"] = binding.get("logical_session_id", "")
        except Exception:
            # Context injection must never claim a binding it could not persist.
            state["observed_logical_session_id"] = ""
    spec = state.get("spec_path", f"docs/spec/{work_unit_id}.md")
    plan = state.get("plan_path", f".harness/work-units/active/{work_unit_id}/plan.md")
    next_action = state.get("next_safe_action", "read the tracked spec and current repository")
    if event_name == "SubagentStart":
        agent_type = str(event.get("agent_type") or event.get("agentType") or "subagent").lower()
        logical_role = infer_role(agent_type)
        role = "reviewer (read-only)" if logical_role == "reviewer" else "worker" if logical_role == "worker" else agent_type
        return f"Harness subagent: Work Unit {work_unit_id}, status={status}, role={role}. Read {spec}; read {plan} when present; re-ground in current code. Next safe action: {next_action}."
    return f"Harness recovery: Work Unit {work_unit_id}, status={status}. Intent: {spec}. Local plan: {plan}. Re-read current Git/code/evidence rather than trusting chat memory. Next safe action: {next_action}."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("event", choices=["SubagentStart", "PostCompact"])
    parser.add_argument("--platform", choices=["codex", "claude"], default="")
    args = parser.parse_args()
    event = load_event()
    if args.platform and not event.get("platform"):
        event["platform"] = args.platform
    base = find_root(Path(str(event.get("cwd") or Path.cwd())))
    message = context(base, args.event, event)
    if args.event == "PostCompact":
        print(json.dumps({"systemMessage": message}))
    else:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": args.event, "additionalContext": message}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
