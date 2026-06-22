"""Small, atomic recovery checkpoints derived from controller-owned state."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

SCHEMA_VERSION = "harness.recovery_checkpoint.v1"


def checkpoint_path(work_unit_path: Path) -> Path:
    return work_unit_path / "checkpoint.json"


def build(state: Mapping[str, Any], *, reason: str, created_at: str) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "work_unit_id": state.get("work_unit_id", ""),
        "repository_id": state.get("repository_id", ""),
        "workspace_id": state.get("workspace_id", ""),
        "worktree": state.get("worktree", ""),
        "branch": state.get("branch", ""),
        "bound_repository_id": state.get("bound_repository_identity", ""),
        "bound_workspace_id": state.get("bound_workspace_id", ""),
        "bound_worktree": state.get("bound_worktree", ""),
        "bound_branch": state.get("bound_branch", ""),
        "base_commit": state.get("base_commit", ""),
        "head_commit": state.get("head_commit", ""),
        "diff_hash": state.get("diff_hash", ""),
        "implementation_diff_hash": state.get("implementation_diff_hash", ""),
        "status": state.get("status", ""),
        "current_role": state.get("current_role", ""),
        "builder_id": state.get("builder_id", ""),
        "builder_session_id": state.get("builder_session_id", ""),
        "review_track_id": state.get("review_track_id", ""),
        "logical_reviewer_session_id": state.get("logical_reviewer_session_id", ""),
        "latest_evidence_refs": list(state.get("latest_evidence_refs", []) or []),
        "known_failures": list(state.get("known_failures", []) or []),
        "blockers": list(state.get("blockers", []) or []),
        "next_safe_action": state.get("next_safe_action", ""),
        "rollback_or_reopen_path": state.get("rollback_or_reopen_path", ""),
        "reason": reason,
        "created_at": created_at,
    }


def write_atomic(path: Path, checkpoint: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(dict(checkpoint), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)
