"""Platform-observed session bindings for Codex and Claude Code adapters."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping

SCHEMA_VERSION = "harness.platform_session_binding.v1"


def infer_platform(event: Mapping[str, Any]) -> str:
    explicit = str(event.get("platform", "")).strip().lower()
    if explicit:
        return explicit
    if "agent_id" in event or "agent_type" in event:
        return "claude"
    return "codex"


def logical_session_id(platform: str, session_id: str, agent_id: str = "") -> str:
    raw = f"{platform}:{session_id}:{agent_id or 'root'}"
    return raw


def binding_key(platform: str, session_id: str, agent_id: str = "") -> str:
    return hashlib.sha256(logical_session_id(platform, session_id, agent_id).encode("utf-8")).hexdigest()[:20]


def binding_path(root: Path, platform: str, session_id: str, agent_id: str = "") -> Path:
    return root / ".harness" / "platform" / "session-bindings" / f"{binding_key(platform, session_id, agent_id)}.json"


def record(root: Path, event: Mapping[str, Any], *, work_unit_id: str, role: str, observed_at: str) -> Dict[str, Any]:
    platform = infer_platform(event)
    session_id = str(event.get("session_id") or event.get("thread_id") or "").strip()
    agent_id = str(event.get("agent_id") or "").strip()
    if not session_id:
        raise ValueError("Hook event has no platform session_id/thread_id.")
    binding = {
        "schema_version": SCHEMA_VERSION,
        "platform": platform,
        "session_id": session_id,
        "agent_id": agent_id,
        "agent_type": str(event.get("agent_type") or event.get("agentType") or ""),
        "logical_session_id": logical_session_id(platform, session_id, agent_id),
        "work_unit_id": work_unit_id,
        "role": role,
        "source": "platform_hook",
        "observed_at": observed_at,
    }
    path = binding_path(root, platform, session_id, agent_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(binding, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)
    latest = root / ".harness" / "platform" / "latest" / work_unit_id / f"{role}.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    temp_latest = latest.with_suffix(".tmp")
    temp_latest.write_text(json.dumps(binding, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp_latest.replace(latest)
    return binding


def latest(root: Path, work_unit_id: str, role: str) -> Dict[str, Any]:
    path = root / ".harness" / "platform" / "latest" / work_unit_id / f"{role}.json"
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}
