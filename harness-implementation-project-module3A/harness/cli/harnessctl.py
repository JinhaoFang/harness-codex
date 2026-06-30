#!/usr/bin/env python3
"""Deterministic controller for the repository coding-agent harness.

Tracked product intent lives in ``docs/spec``. Local plans, evidence, review
lineage, platform sessions, and recovery checkpoints live in ignored
``.harness`` state. Agents produce candidate work; this controller owns only
mechanical lifecycle and acceptance gates.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from harness.core import checkpoints as checkpoint_core
from harness.core import contracts as contract_core
from harness.core import plans as plan_core
from harness.core import sessions as session_core
from harness.core.checks import CheckExecution, execution_argv, red_failure_matches, run_check
from harness.core.repository import (
    RepoSnapshot,
    current_branch,
    find_root,
    full_diff_hash,
    git_identity,
    head_commit,
    implementation_changed_files,
    implementation_diff_hash,
    is_git_repo,
    is_non_implementation_path,
    repository_id,
    run_git,
    status_paths,
    work_unit_changed_files,
    workspace_id,
)
from harness.core.storage import (
    StorageError,
    append_jsonl,
    atomic_write_text,
    file_hash,
    load_json,
    now_iso,
    read_jsonl,
    write_json,
)
from harness.platforms import adapters as platform_adapters

STATE_SCHEMA = "harness.work_unit_state.v3"
EVIDENCE_SCHEMA = "harness.evidence_receipt.v4"
REVIEW_REQUEST_SCHEMA = "harness.review_request.v4"
REVIEW_VERDICT_SCHEMA = "harness.review_verdict.v4"
REVIEW_TRACK_SCHEMA = "harness.review_track.v2"
AMENDMENT_SCHEMA = "harness.spec_amendment.v2"
GOAL_SCHEMA = "harness.codex_goal_projection.v1"
GOAL_BINDING_SCHEMA = "harness.codex_goal_binding.v1"
GITHUB_SCHEMA = "harness.github_pr_snapshot.v2"

VALID_STATUSES = {
    "clarifying",
    "spec_approved",
    "planning",
    "plan_reviewing",
    "ready",
    "running",
    "verifying",
    "reviewing",
    "handoff",
    "archived",
    "blocked",
}
RISK_ORDER = {"trivial": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
PASS_DECISIONS = {"PASS"}
REVIEW_MODES = ("plan", "close")
WORK_UNIT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class HarnessError(RuntimeError):
    """Expected user-facing controller failure."""


def validate_work_unit_id(value: str) -> str:
    value = value.strip()
    if not WORK_UNIT_ID_RE.fullmatch(value) or value in {".", ".."}:
        raise HarnessError("Work Unit id must use 1-128 letters, numbers, '.', '_', or '-' characters.")
    return value


# ---------------------------------------------------------------------------
# Paths and local storage
# ---------------------------------------------------------------------------

def harness_dir(root: Path) -> Path:
    return root / ".harness"


def work_units_dir(root: Path) -> Path:
    return harness_dir(root) / "work-units"


def active_dir(root: Path) -> Path:
    return work_units_dir(root) / "active"


def archive_dir(root: Path) -> Path:
    return work_units_dir(root) / "archive"


def session_id() -> str:
    for name in ("HARNESS_SESSION_ID", "CLAUDE_SESSION_ID", "CODEX_THREAD_ID"):
        value = os.environ.get(name, "").strip()
        if value:
            return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return "default"


def runtime_dir(root: Path) -> Path:
    return harness_dir(root) / "runtime" / workspace_id(root) / session_id()


def current_file(root: Path) -> Path:
    return runtime_dir(root) / "current"


def state_path(wu_path: Path) -> Path:
    return wu_path / "state.json"


def plan_path(wu_path: Path) -> Path:
    return wu_path / "plan.md"


def receipts_path(wu_path: Path) -> Path:
    return wu_path / "evidence" / "receipts.jsonl"


def evidence_artifacts_dir(wu_path: Path) -> Path:
    return wu_path / "evidence" / "artifacts"


def amendments_path(wu_path: Path) -> Path:
    return wu_path / "amendments.jsonl"


def reviews_dir(wu_path: Path) -> Path:
    return wu_path / "reviews"


def review_requests_dir(wu_path: Path) -> Path:
    return reviews_dir(wu_path) / "requests"


def review_verdicts_dir(wu_path: Path) -> Path:
    return reviews_dir(wu_path) / "verdicts"


def review_track_path(wu_path: Path) -> Path:
    return reviews_dir(wu_path) / "track.json"


def github_snapshot_path(wu_path: Path) -> Path:
    return wu_path / "github" / "pull-request.json"


def spec_path_for_id(root: Path, work_unit_id: str) -> Path:
    return root / "docs" / "spec" / f"{validate_work_unit_id(work_unit_id)}.md"


def root_from_wu_path(wu_path: Path) -> Path:
    for parent in (wu_path.resolve(), *wu_path.resolve().parents):
        if parent.name == ".harness":
            return parent.parent
    raise HarnessError(f"Cannot derive repository root from {wu_path}.")


def spec_path(wu_path: Path) -> Path:
    root = root_from_wu_path(wu_path)
    state = load_json(state_path(wu_path), {})
    rel = str(state.get("spec_path", "")).strip()
    return root / rel if rel else spec_path_for_id(root, wu_path.name)


def resolve_wu(root: Path, work_unit_id: Optional[str]) -> Tuple[str, Path]:
    if not work_unit_id:
        pointer = current_file(root)
        if pointer.exists():
            work_unit_id = pointer.read_text(encoding="utf-8").strip()
    if not work_unit_id and active_dir(root).exists():
        candidates = sorted(path.name for path in active_dir(root).iterdir() if path.is_dir())
        if len(candidates) == 1:
            work_unit_id = candidates[0]
    if not work_unit_id:
        raise HarnessError("No Work Unit id supplied and no workspace/session-local current Work Unit exists.")
    work_unit_id = validate_work_unit_id(work_unit_id)
    for base in (active_dir(root), archive_dir(root)):
        candidate = base / work_unit_id
        if candidate.exists():
            return work_unit_id, candidate
    raise HarnessError(f"Work Unit not found: {work_unit_id}")


def ensure_gitignore_entry(root: Path, entry: str = ".harness/") -> None:
    path = root / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = [line.strip() for line in text.splitlines()]
    if entry in lines or entry.rstrip("/") in lines:
        return
    atomic_write_text(path, text + ("" if not text or text.endswith("\n") else "\n") + entry + "\n")


def glob_matches(path: str, patterns: Iterable[str]) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    for raw in patterns:
        pattern = str(raw).replace("\\", "/").strip().lstrip("./")
        if not pattern:
            continue
        if pattern.endswith("/**"):
            prefix = pattern[:-3]
            if normalized == prefix or normalized.startswith(prefix + "/"):
                return True
        if fnmatch.fnmatch(normalized, pattern):
            return True
    return False


def repository_identity(root: Path) -> str:
    """Compatibility alias used by tests and older hook integrations."""
    return repository_id(root)


def clean_scalar(value: str) -> str:
    """Remove whitespace and only a complete matching outer quote pair."""
    return contract_core.unquote_pair(value)


# ---------------------------------------------------------------------------
# Contract, plan, state, and checkpoint helpers
# ---------------------------------------------------------------------------

def spec_content_hash(path: Path) -> str:
    try:
        return contract_core.content_hash(path)
    except contract_core.ContractError as exc:
        raise HarnessError(str(exc)) from exc


def update_spec_approval_metadata(path: Path, values: Dict[str, str]) -> None:
    try:
        contract_core.update_approval(path, values)
    except contract_core.ContractError as exc:
        raise HarnessError(str(exc)) from exc


def required_evidence_items(wu_path: Path) -> List[Dict[str, Any]]:
    try:
        return contract_core.evidence_items(contract_core.load_contract(spec_path(wu_path)))
    except contract_core.ContractError:
        return []


def scope_patterns(wu_path: Path) -> Tuple[List[str], List[str]]:
    try:
        return contract_core.scope_patterns(contract_core.load_contract(spec_path(wu_path)))
    except contract_core.ContractError:
        return [], []


def spec_summary(wu_path: Path, max_chars: int = 900) -> str:
    try:
        contract = contract_core.load_contract(spec_path(wu_path))
    except contract_core.ContractError as exc:
        return f"Invalid tracked spec: {exc}"
    value = {
        "intent": contract.get("intent", ""),
        "expected_outcomes": contract.get("expected_outcomes", []),
        "non_goals": contract.get("non_goals", []),
    }
    text = json.dumps(value, ensure_ascii=False, indent=2)
    return text[:max_chars] + ("…" if len(text) > max_chars else "")


def _checkpoint(root: Path, wu_path: Path, state: Mapping[str, Any], reason: str) -> Dict[str, Any]:
    checkpoint = checkpoint_core.build(state, reason=reason, created_at=now_iso())
    checkpoint_core.write_atomic(checkpoint_core.checkpoint_path(wu_path), checkpoint)
    return checkpoint


def update_state(root: Path, wu_path: Path, *, checkpoint_reason: str = "state_transition", **patch: Any) -> Dict[str, Any]:
    state = load_json(state_path(wu_path), {})
    base = str(state.get("base_commit", ""))
    state.update(patch)
    dynamic = git_identity(root, base)
    # Immutable workspace binding is recorded separately. Dynamic fields show
    # the current checkout but cannot rewrite the binding that recovery checks.
    state.update(
        {
            "repository_id": dynamic["repository_id"],
            "workspace_id": dynamic["workspace_id"],
            "worktree": dynamic["worktree"],
            "branch": dynamic["branch"],
            "head_commit": dynamic["head_commit"],
            "changed_files": dynamic["changed_files"],
            "implementation_changed_files": dynamic["implementation_changed_files"],
            "diff_hash": dynamic["diff_hash"],
            "implementation_diff_hash": dynamic["implementation_diff_hash"],
            "updated_at": now_iso(),
        }
    )
    write_json(state_path(wu_path), state)
    _checkpoint(root, wu_path, state, checkpoint_reason)
    return state


def _new_state(root: Path, work_unit_id: str, risk: str, status: str) -> Dict[str, Any]:
    base = head_commit(root)
    identity = git_identity(root, base)
    now = now_iso()
    return {
        "schema_version": STATE_SCHEMA,
        "work_unit_id": work_unit_id,
        "status": status,
        "risk": risk,
        "generation": 1,
        "spec_path": spec_path_for_id(root, work_unit_id).relative_to(root).as_posix(),
        "plan_path": f".harness/work-units/active/{work_unit_id}/plan.md",
        "spec_approved_hash": "",
        "spec_approved_at": "",
        "spec_approved_by": "",
        "spec_approval_ref": "",
        "plan_approved_hash": "",
        "review_track_id": "",
        "logical_reviewer_session_id": "",
        "builder_id": "",
        "builder_session_id": "",
        "current_role": "conductor",
        "base_commit": base,
        "bound_repository_identity": identity["repository_id"],
        "bound_workspace_id": identity["workspace_id"],
        "bound_worktree": identity["worktree"],
        "bound_branch": identity["branch"],
        **identity,
        "latest_evidence_refs": [],
        "known_failures": [],
        "blockers": [],
        "next_safe_action": "Clarify intent and complete the tracked spec.",
        "rollback_or_reopen_path": "Reopen this Work Unit or revert its branch before integration.",
        "created_at": now,
        "updated_at": now,
    }


def _create_runtime_work_unit(root: Path, work_unit_id: str, risk: str, *, status: str = "clarifying") -> Path:
    wu_path = active_dir(root) / work_unit_id
    if wu_path.exists():
        raise HarnessError(f"Work Unit already exists: {work_unit_id}")
    for path in (evidence_artifacts_dir(wu_path), review_requests_dir(wu_path), review_verdicts_dir(wu_path)):
        path.mkdir(parents=True, exist_ok=True)
    state = _new_state(root, work_unit_id, risk, status)
    write_json(state_path(wu_path), state)
    receipts_path(wu_path).touch()
    amendments_path(wu_path).touch()
    _checkpoint(root, wu_path, state, "work_unit_created")
    current_file(root).parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(current_file(root), work_unit_id + "\n")
    return wu_path


def _approval_is_valid(contract: Mapping[str, Any], path: Path) -> bool:
    approval = contract.get("approval", {})
    if not isinstance(approval, dict):
        return False
    return (
        approval.get("status") == "approved"
        and str(approval.get("approved_by", "")).startswith("human:")
        and bool(approval.get("approved_at"))
        and bool(approval.get("approval_ref"))
        and approval.get("approved_content_hash") == spec_content_hash(path)
    )


def _write_default_plan(wu_path: Path, work_unit_id: str, title: str) -> None:
    atomic_write_text(plan_path(wu_path), plan_core.render_plan(plan_core.default_plan(work_unit_id, title)))


# ---------------------------------------------------------------------------
# Spec and plan checks
# ---------------------------------------------------------------------------

def check_spec_document(path: Path, expected_id: Optional[str] = None, *, allow_approval_mismatch: bool = False) -> Tuple[List[str], List[str]]:
    if not path.exists():
        return [f"Missing tracked spec: {path}"], []
    try:
        contract = contract_core.load_contract(path)
        blocking, warnings = contract_core.validate_contract(contract, expected_id)
    except contract_core.ContractError as exc:
        return [str(exc)], []
    approval = contract.get("approval", {}) if isinstance(contract.get("approval"), dict) else {}
    status = str(approval.get("status", "draft"))
    if status not in {"draft", "approved"}:
        blocking.append(f"Invalid approval status: {status!r}.")
    if status == "approved":
        if not str(approval.get("approved_by", "")).startswith("human:"):
            blocking.append("Approved spec approved_by must use human:<identity>.")
        for key in ("approved_at", "approval_ref", "approved_content_hash"):
            if not str(approval.get(key, "")).strip():
                blocking.append(f"Approved spec is missing {key}.")
        if approval.get("approved_content_hash") != spec_content_hash(path) and not allow_approval_mismatch:
            blocking.append("Approved spec content changed after approval; use amend and re-review the plan.")
    return blocking, warnings


def check_spec(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    blocking, warnings = check_spec_document(spec_path(wu_path), wu_path.name)
    state = load_json(state_path(wu_path), {})
    approved = str(state.get("spec_approved_hash", ""))
    if state.get("status") not in {"clarifying", "blocked"}:
        if not approved:
            blocking.append("Controller state has no approved spec revision.")
        elif approved != spec_content_hash(spec_path(wu_path)):
            blocking.append("Tracked spec differs from the controller-approved revision.")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def check_plan(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    try:
        plan = plan_core.load_plan(plan_path(wu_path))
        contract = contract_core.load_contract(spec_path(wu_path))
    except (plan_core.PlanError, contract_core.ContractError) as exc:
        return "BLOCK", [str(exc)], []
    risk = str(contract.get("risk", "low"))
    blocking, warnings = plan_core.validate_plan(plan, wu_path.name, RISK_ORDER.get(risk, 1))
    claims = {str(item.get("id", "")) for item in contract_core.evidence_items(contract)}
    checks = contract_core.check_definitions(contract)
    covered_claims: set[str] = set()
    for row in plan.get("behavior_slices", []) if isinstance(plan.get("behavior_slices"), list) else []:
        if not isinstance(row, dict):
            continue
        behavior_id = str(row.get("id", "<unknown>"))
        claim = str(row.get("claim_ref", ""))
        if claim not in claims:
            blocking.append(f"Behavior {behavior_id} references unknown evidence claim {claim!r}.")
        else:
            covered_claims.add(claim)
        for phase in ("red", "green"):
            value = row.get(phase, {})
            check_id = str(value.get("check_id", "")) if isinstance(value, dict) else ""
            if check_id not in checks:
                blocking.append(f"Behavior {behavior_id} {phase}.check_id {check_id!r} is not declared by the spec.")
    for claim in sorted(claims - covered_claims):
        blocking.append(f"Required evidence claim {claim!r} is not covered by any TDD behavior slice.")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def check_scope(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    state = load_json(state_path(wu_path), {})
    allowed, forbidden = scope_patterns(wu_path)
    snapshot = RepoSnapshot.capture(root, str(state.get("base_commit", "")))
    changed = list(snapshot.implementation_changed_files)
    blocking: List[str] = []
    warnings: List[str] = []
    for rel in changed:
        if forbidden and glob_matches(rel, forbidden):
            blocking.append(f"Implementation change touches out-of-bounds path: {rel}")
        elif allowed and not glob_matches(rel, allowed):
            blocking.append(f"Implementation change is outside write boundary: {rel}")
    if not changed:
        warnings.append("No implementation changes detected relative to the Work Unit base commit.")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


# ---------------------------------------------------------------------------
# Evidence and freshness
# ---------------------------------------------------------------------------

def evidence_receipts(wu_path: Path) -> List[Dict[str, Any]]:
    return [row for row in read_jsonl(receipts_path(wu_path)) if row.get("work_unit_id") == wu_path.name]


def latest_final_for_claim(wu_path: Path, claim_ref: str) -> Optional[Dict[str, Any]]:
    rows = [row for row in evidence_receipts(wu_path) if row.get("claim_ref") == claim_ref and row.get("phase") == "final"]
    return sorted(rows, key=lambda row: (str(row.get("ended_at", "")), str(row.get("receipt_id", ""))))[-1] if rows else None


def latest_pass_for_claim(wu_path: Path, claim_ref: str) -> Optional[Dict[str, Any]]:
    row = latest_final_for_claim(wu_path, claim_ref)
    return row if row and row.get("result") == "pass" else None


def verification_detail_report(root: Path, wu_path: Path) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    state = load_json(state_path(wu_path), {})
    try:
        contract = contract_core.load_contract(spec_path(wu_path))
    except contract_core.ContractError as exc:
        return [], [str(exc)], []
    current_impl = RepoSnapshot.capture(root, str(state.get("base_commit", ""))).implementation_diff_hash
    details: List[Dict[str, Any]] = []
    blocking: List[str] = []
    warnings: List[str] = []
    declared_ids = {str(item.get("id", "")) for item in contract_core.evidence_items(contract)}
    for item in contract_core.evidence_items(contract):
        claim_id = str(item.get("id", ""))
        check_id = str(item.get("check_id", ""))
        definition = contract_core.check_definition(contract, check_id)
        expected_hash = contract_core.check_definition_hash(check_id, definition)
        expected_argv = execution_argv(definition)
        receipt = latest_final_for_claim(wu_path, claim_id)
        status = "satisfied"
        reason = ""
        if receipt is None:
            status, reason = "missing", f"Missing final pass evidence for {claim_id}."
        elif receipt.get("result") == "skipped":
            status, reason = "skipped", f"Latest final observation for {claim_id} was skipped."
        elif receipt.get("result") != "pass":
            status, reason = "failed", f"Latest final observation for {claim_id} failed."
        elif receipt.get("observation") != "controller_executed_check":
            status, reason = "untrusted", f"Evidence for {claim_id} was not controller-executed."
        elif receipt.get("spec_hash") != state.get("spec_approved_hash"):
            status, reason = "stale", f"Evidence for {claim_id} targets another spec revision."
        elif receipt.get("plan_hash") != state.get("plan_approved_hash"):
            status, reason = "stale", f"Evidence for {claim_id} targets another plan revision."
        elif receipt.get("workspace_id") != state.get("bound_workspace_id"):
            status, reason = "stale", f"Evidence for {claim_id} belongs to another workspace."
        elif receipt.get("implementation_diff_hash") != current_impl:
            status, reason = "stale", f"Evidence for {claim_id} is stale because implementation changed after it was produced."
        elif receipt.get("check_id") != check_id or receipt.get("check_definition_hash") != expected_hash:
            status, reason = "invalid", f"Evidence for {claim_id} did not use the current check definition."
        elif list(receipt.get("argv", [])) != expected_argv:
            status, reason = "invalid", f"Evidence for {claim_id} did not execute the declared argv."
        else:
            log_ref = str(receipt.get("command_log_ref", ""))
            log_path = root / log_ref if log_ref else Path()
            if not log_ref or not log_path.is_file():
                status, reason = "invalid", f"Evidence for {claim_id} has no readable command log."
            elif receipt.get("command_log_hash") != file_hash(log_path):
                status, reason = "invalid", f"Evidence log for {claim_id} was modified."
        if status != "satisfied":
            blocking.append(reason)
        details.append(
            {
                "claim": claim_id,
                "check_id": check_id,
                "status": status,
                "receipt_id": receipt.get("receipt_id") if receipt else None,
                "requires_rerun": status != "satisfied",
                "reason": reason,
                "minimal_next_action": f"harnessctl verify --id {wu_path.name} --claim {claim_id} --phase final" if status != "satisfied" else "none",
            }
        )
    for row in evidence_receipts(wu_path):
        if row.get("result") == "pass" and str(row.get("claim_ref", "")) not in declared_ids:
            warnings.append(f"Pass receipt {row.get('receipt_id')} references a non-contract claim.")
    return details, blocking, warnings


def check_verification(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    _details, blocking, warnings = verification_detail_report(root, wu_path)
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def _write_execution_log(root: Path, wu_path: Path, receipt_id: str, execution: CheckExecution, metadata: Mapping[str, Any]) -> Tuple[str, str]:
    path = evidence_artifacts_dir(wu_path) / f"{receipt_id}.log"
    header = {**dict(metadata), "argv": execution.argv, "cwd": str(execution.cwd), "timeout_seconds": execution.timeout_seconds}
    atomic_write_text(
        path,
        json.dumps(header, ensure_ascii=False, indent=2)
        + "\n\n--- stdout ---\n"
        + execution.stdout
        + "\n--- stderr ---\n"
        + execution.stderr
        + "\n",
    )
    return path.relative_to(root).as_posix(), file_hash(path)


# ---------------------------------------------------------------------------
# Review lineage and acceptance
# ---------------------------------------------------------------------------

def review_requests(wu_path: Path) -> List[Dict[str, Any]]:
    return [load_json(path, {}) for path in sorted(review_requests_dir(wu_path).glob("*.json"))]


def review_verdicts(wu_path: Path) -> List[Dict[str, Any]]:
    return [load_json(path, {}) for path in sorted(review_verdicts_dir(wu_path).glob("*.json"))]


def latest_review_request(wu_path: Path, mode: str, pending_only: bool = False) -> Optional[Dict[str, Any]]:
    resolved = {str(row.get("request_id", "")) for row in review_verdicts(wu_path)}
    rows = [row for row in review_requests(wu_path) if row.get("mode") == mode]
    if pending_only:
        rows = [row for row in rows if str(row.get("request_id", "")) not in resolved]
    return sorted(rows, key=lambda row: (str(row.get("created_at", "")), str(row.get("request_id", ""))))[-1] if rows else None


def latest_passing_verdict(wu_path: Path, mode: str) -> Optional[Dict[str, Any]]:
    rows = [row for row in review_verdicts(wu_path) if row.get("mode") == mode and row.get("decision") in PASS_DECISIONS]
    return sorted(rows, key=lambda row: (str(row.get("created_at", "")), str(row.get("review_id", ""))))[-1] if rows else None


def _role_session(root: Path, work_unit_id: str, role: str, explicit: str, env_name: str, fallback: str = "") -> Tuple[str, str, Dict[str, Any]]:
    binding = session_core.latest(root, work_unit_id, role)
    if binding:
        logical = str(binding.get("logical_session_id", ""))
        raw = str(binding.get("session_id", ""))
        supplied = explicit or os.environ.get(env_name, "")
        if supplied and supplied not in {logical, raw}:
            raise HarnessError(f"Supplied {role} session differs from the platform-observed binding.")
        return logical, "platform_hook", binding
    value = (os.environ.get(env_name, "") or explicit or fallback).strip()
    source = f"environment:{env_name}" if os.environ.get(env_name, "") else "cli_attestation" if explicit else "default"
    return value, source, {}


def _default_builder_id(binding: Mapping[str, Any], logical_session_id: str) -> str:
    platform = str(binding.get("platform", "")).strip().lower() or "worker"
    session = logical_session_id.strip() or str(binding.get("logical_session_id", "")).strip()
    if not session:
        return ""
    return f"worker:{platform}:{session}"


def review_independence_errors(verdict: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    mode = str(verdict.get("mode", ""))
    reviewer = str(verdict.get("reviewer_id", ""))
    reviewer_session = str(verdict.get("logical_reviewer_session_id", ""))
    subject = str(verdict.get("planner_id" if mode == "plan" else "builder_id", ""))
    subject_session = str(verdict.get("planner_session_id" if mode == "plan" else "builder_session_id", ""))
    level = str(verdict.get("independence_level", ""))
    if level == "human_gate":
        if not reviewer.startswith("human:"):
            errors.append("Human-gate reviewer must use human:<identity>.")
        if not verdict.get("approval_ref"):
            errors.append("Human-gate review requires approval_ref.")
    elif verdict.get("is_independent"):
        if not reviewer or reviewer == subject:
            errors.append(f"Independent {mode} reviewer identity is not separate from the subject.")
        if not reviewer_session or reviewer_session == subject_session:
            errors.append(f"Independent {mode} reviewer session is not separate from the subject session.")
    return errors


def check_plan_review(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    state = load_json(state_path(wu_path), {})
    verdict = latest_passing_verdict(wu_path, "plan")
    track = load_json(review_track_path(wu_path), {})
    blocking: List[str] = []
    warnings: List[str] = []
    if not verdict:
        blocking.append("A passing plan review is required before implementation.")
    else:
        blocking.extend(review_independence_errors(verdict))
        if track.get("schema_version") != REVIEW_TRACK_SCHEMA:
            blocking.append("Review track is not using the single-logical-session protocol.")
        for label, left, right in (
            ("track", verdict.get("review_track_id"), track.get("review_track_id")),
            ("state track", verdict.get("review_track_id"), state.get("review_track_id")),
            ("reviewer", verdict.get("reviewer_id"), track.get("reviewer_id")),
            ("reviewer session", verdict.get("logical_reviewer_session_id"), track.get("logical_reviewer_session_id")),
            ("generation", verdict.get("review_track_generation"), track.get("generation")),
        ):
            if left != right:
                blocking.append(f"Plan review {label} differs from the active review track.")
        if verdict.get("reviewed_spec_hash") != state.get("spec_approved_hash"):
            blocking.append("Plan review does not cover the approved spec revision.")
        current_plan_hash = file_hash(plan_path(wu_path))
        if verdict.get("reviewed_plan_hash") != current_plan_hash or state.get("plan_approved_hash") != current_plan_hash:
            blocking.append("Technical plan changed after plan review.")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def check_review(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    state = load_json(state_path(wu_path), {})
    risk = str(state.get("risk", "low"))
    verdict = latest_passing_verdict(wu_path, "close")
    blocking: List[str] = []
    warnings: List[str] = []
    if not verdict:
        if risk == "trivial":
            return "WARN", [], ["Trivial Work Unit has no close review."]
        return "BLOCK", ["A passing close review is required."], []
    track = load_json(review_track_path(wu_path), {})
    blocking.extend(review_independence_errors(verdict))
    if verdict.get("review_track_id") != track.get("review_track_id") or verdict.get("review_track_id") != state.get("review_track_id"):
        blocking.append("Close review does not belong to the active plan-review track.")
    if verdict.get("review_track_generation") != track.get("generation"):
        blocking.append("Close review belongs to a superseded reviewer generation.")
    if verdict.get("reviewer_id") != track.get("reviewer_id"):
        blocking.append("Close review used another reviewer identity.")
    if verdict.get("logical_reviewer_session_id") != track.get("logical_reviewer_session_id"):
        blocking.append("Close review did not resume the plan-review logical session.")
    if verdict.get("reviewed_spec_hash") != state.get("spec_approved_hash"):
        blocking.append("Close review does not cover the approved spec.")
    if verdict.get("reviewed_plan_hash") != state.get("plan_approved_hash"):
        blocking.append("Close review does not cover the approved plan.")
    snapshot = RepoSnapshot.capture(root, str(state.get("base_commit", "")))
    if verdict.get("reviewed_head_commit") != snapshot.head_commit:
        blocking.append("Repository HEAD changed after close review.")
    if verdict.get("reviewed_implementation_diff_hash") != snapshot.implementation_diff_hash:
        blocking.append("Implementation changed after close review.")
    if verdict.get("reviewer_id") == state.get("builder_id") or verdict.get("logical_reviewer_session_id") == state.get("builder_session_id"):
        blocking.append("Builder cannot own the close review verdict.")
    verification_decision, verification_blocking, verification_warnings = check_verification(root, wu_path)
    if verification_decision == "BLOCK":
        blocking.extend(verification_blocking)
    warnings.extend(verification_warnings)
    current_receipts = {
        str(row.get("receipt_id"))
        for item in required_evidence_items(wu_path)
        for row in [latest_pass_for_claim(wu_path, str(item.get("id", "")))]
        if row
    }
    cited = {str(value) for value in verdict.get("evidence_refs", [])}
    if RISK_ORDER.get(risk, 1) >= 2 and current_receipts and not current_receipts.intersection(cited):
        blocking.append("Medium+ close review must cite current evidence receipts.")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def _normalize_github_checks(rows: Any) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    if not isinstance(rows, list):
        return normalized
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        name = str(row.get("name") or row.get("context") or row.get("workflowName") or "").strip()
        if not name:
            continue
        status = str(row.get("status") or "").upper()
        outcome = str(row.get("conclusion") or row.get("state") or "").upper()
        normalized.append(
            {
                "name": name,
                "kind": str(row.get("__typename") or "unknown"),
                "status": status,
                "outcome": outcome,
                "successful": outcome == "SUCCESS",
                "details_url": str(row.get("detailsUrl") or row.get("targetUrl") or ""),
            }
        )
    return normalized


def check_delivery(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    try:
        contract = contract_core.load_contract(spec_path(wu_path))
    except contract_core.ContractError as exc:
        return "BLOCK", [str(exc)], []
    delivery = contract.get("delivery", {}) if isinstance(contract.get("delivery"), dict) else {}
    pr_ref = str(delivery.get("pull_request", "")).strip()
    required = [str(value).strip() for value in delivery.get("required_checks", []) if str(value).strip()] if isinstance(delivery.get("required_checks", []), list) else []
    if not pr_ref:
        if required:
            blocking.append("GitHub required checks are configured but no pull request is linked.")
        return ("BLOCK" if blocking else "PASS"), blocking, warnings
    path = github_snapshot_path(wu_path)
    if not path.exists():
        return "BLOCK", ["Linked pull request has no controller-captured GitHub snapshot; run github-sync."], []
    snapshot = load_json(path, {})
    if snapshot.get("schema_version") != GITHUB_SCHEMA or snapshot.get("work_unit_id") != wu_path.name:
        blocking.append("GitHub snapshot is missing, unsupported, or belongs to another Work Unit.")
    if pr_ref.isdigit() and str(snapshot.get("number", "")) != pr_ref:
        blocking.append("GitHub snapshot belongs to a different pull request than the tracked delivery reference.")
    repo_snapshot = RepoSnapshot.capture(root)
    if str(snapshot.get("headRefOid", "")) != repo_snapshot.head_commit:
        blocking.append("GitHub PR HEAD does not match the current local HEAD.")
    pr_state = str(snapshot.get("state", "")).upper()
    if pr_state == "CLOSED":
        blocking.append("Linked pull request is closed without a merged state.")
    checks = snapshot.get("normalized_checks", [])
    by_name = {str(row.get("name", "")): row for row in checks if isinstance(row, Mapping)} if isinstance(checks, list) else {}
    if required:
        for name in required:
            row = by_name.get(name)
            if row is None:
                blocking.append(f"Required GitHub check {name!r} is missing from the latest snapshot.")
            elif not bool(row.get("successful")):
                outcome = str(row.get("outcome") or row.get("status") or "pending")
                blocking.append(f"Required GitHub check {name!r} is not successful ({outcome}).")
    else:
        warnings.append("Pull request is linked but delivery.required_checks is empty; only PR/HEAD identity is gated.")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def check_archive(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    for label, func in (("spec", check_spec), ("scope", check_scope), ("verification", check_verification), ("review", check_review), ("delivery", check_delivery)):
        _decision, reasons, warns = func(root, wu_path)
        blocking.extend(f"{label}: {reason}" for reason in reasons)
        warnings.extend(f"{label}: {warning}" for warning in warns)
    state = load_json(state_path(wu_path), {})
    if not (wu_path / "handoff.md").exists() and not str(state.get("no_next_step_reason", "")).strip():
        blocking.append("Archive requires a handoff or explicit no-next-step reason.")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


# ---------------------------------------------------------------------------
# Lifecycle commands
# ---------------------------------------------------------------------------

def init(args: argparse.Namespace) -> int:
    root = args.root
    for path in (active_dir(root), archive_dir(root), runtime_dir(root), harness_dir(root) / "tmp"):
        path.mkdir(parents=True, exist_ok=True)
    (root / "docs" / "spec").mkdir(parents=True, exist_ok=True)
    ensure_gitignore_entry(root)
    config = harness_dir(root) / "config.json"
    if not config.exists():
        write_json(
            config,
            {
                "schema_version": "harness.config.v3",
                "profile": getattr(args, "profile", "codex"),
                "tracked_specs_dir": "docs/spec",
                "runtime_dir": ".harness",
                "created_at": now_iso(),
            },
        )
    if not getattr(args, "quiet", False):
        print(f"Initialized ignored harness runtime at {harness_dir(root)}")
    return 0


def new(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id = validate_work_unit_id(args.id)
    init(argparse.Namespace(root=root, profile=getattr(args, "profile", "codex"), quiet=True))
    preexisting = [path for path in status_paths(root) if not is_non_implementation_path(path)]
    if preexisting:
        raise HarnessError("New Work Unit requires a clean implementation worktree: " + ", ".join(preexisting))
    tracked = spec_path_for_id(root, work_unit_id)
    if tracked.exists():
        raise HarnessError(f"Tracked spec already exists: {tracked}. Use resume-session or reconstruct.")
    contract = contract_core.default_contract(work_unit_id, args.title, args.type, args.risk)
    tracked.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(tracked, contract_core.render_spec(contract))
    wu_path = _create_runtime_work_unit(root, work_unit_id, args.risk)
    _write_default_plan(wu_path, work_unit_id, args.title)
    print(json.dumps({"work_unit_id": work_unit_id, "spec": tracked.relative_to(root).as_posix(), "runtime": wu_path.relative_to(root).as_posix(), "status": "clarifying"}, ensure_ascii=False, indent=2))
    return 0


def resume_session(args: argparse.Namespace) -> int:
    work_unit_id = validate_work_unit_id(args.id)
    wu_path = active_dir(args.root) / work_unit_id
    if not wu_path.exists():
        raise HarnessError("No local runtime exists. Use `reconstruct`; resume-session never invents lost state.")
    state = load_json(state_path(wu_path), {})
    mismatches = []
    if state.get("bound_repository_identity") != repository_id(args.root):
        mismatches.append("repository")
    if state.get("bound_workspace_id") != workspace_id(args.root):
        mismatches.append("workspace")
    if state.get("bound_worktree") != str(args.root.resolve()):
        mismatches.append("worktree")
    if state.get("bound_branch") != current_branch(args.root):
        mismatches.append("branch")
    if mismatches:
        raise HarnessError("Local runtime is bound to another " + ", ".join(mismatches) + "; use the original workspace or reconstruct explicitly.")
    current_file(args.root).parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(current_file(args.root), work_unit_id + "\n")
    state = update_state(args.root, wu_path, checkpoint_reason="session_resumed")
    print(json.dumps({"work_unit_id": work_unit_id, "status": state.get("status"), "recovery": "continuation", "checkpoint": checkpoint_core.checkpoint_path(wu_path).relative_to(args.root).as_posix(), "required_next_action": state.get("next_safe_action", "")}, ensure_ascii=False, indent=2))
    return 0


def reconstruct(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id = validate_work_unit_id(args.id)
    init(argparse.Namespace(root=root, profile=getattr(args, "profile", "codex"), quiet=True))
    if (active_dir(root) / work_unit_id).exists():
        raise HarnessError("Local runtime already exists; use resume-session rather than reconstruct.")
    tracked = spec_path_for_id(root, work_unit_id)
    if not tracked.exists():
        raise HarnessError(f"Tracked spec not found: {tracked}")
    try:
        contract = contract_core.load_contract(tracked)
    except contract_core.ContractError as exc:
        raise HarnessError(str(exc) + " Run migrate-spec for a legacy spec.") from exc
    risk = str(contract.get("risk", "low")) if str(contract.get("risk", "low")) in RISK_ORDER else "low"
    approved = _approval_is_valid(contract, tracked)
    status_value = "spec_approved" if approved else "clarifying"
    wu_path = _create_runtime_work_unit(root, work_unit_id, risk, status=status_value)
    _write_default_plan(wu_path, work_unit_id, str(contract.get("title", work_unit_id)))
    approval = contract.get("approval", {}) if isinstance(contract.get("approval"), dict) else {}
    patch: Dict[str, Any] = {
        "status": status_value,
        "next_safe_action": "Rebuild the plan from current code and run plan review; old local evidence/review is not recovered." if approved else "Reconfirm and approve the tracked spec.",
        "reconstructed_at": now_iso(),
        "reconstruction_basis": [tracked.relative_to(root).as_posix(), "git", "current_codebase"],
    }
    if approved:
        patch.update(
            {
                "spec_approved_hash": spec_content_hash(tracked),
                "spec_approved_at": approval.get("approved_at", ""),
                "spec_approved_by": approval.get("approved_by", ""),
                "spec_approval_ref": approval.get("approval_ref", ""),
            }
        )
    update_state(root, wu_path, checkpoint_reason="runtime_reconstructed", **patch)
    print(json.dumps({"work_unit_id": work_unit_id, "status": status_value, "recovery": "reconstruction_not_continuation", "recovered_from": patch["reconstruction_basis"], "required_next_action": patch["next_safe_action"]}, ensure_ascii=False, indent=2))
    return 0


def resume(args: argparse.Namespace) -> int:
    """Deprecated safe alias; it intentionally does not reconstruct."""
    return resume_session(args)


def migrate_spec(args: argparse.Namespace) -> int:
    path = spec_path_for_id(args.root, validate_work_unit_id(args.id))
    if not path.exists():
        raise HarnessError(f"Tracked spec not found: {path}")
    try:
        contract_core.load_contract(path)
    except contract_core.ContractError:
        try:
            contract = contract_core.migrate_legacy(path.read_text(encoding="utf-8"), args.id)
        except contract_core.ContractError as exc:
            raise HarnessError(str(exc)) from exc
        backup = path.with_suffix(path.suffix + ".legacy.bak")
        if backup.exists():
            raise HarnessError(f"Migration backup already exists: {backup}")
        atomic_write_text(backup, path.read_text(encoding="utf-8"))
        atomic_write_text(path, contract_core.render_spec(contract, "Migrated from the legacy spec; review every field before approval."))
        print(json.dumps({"work_unit_id": args.id, "migrated": True, "backup": backup.relative_to(args.root).as_posix()}, indent=2))
        return 0
    raise HarnessError("Spec already uses the canonical JSON contract; no migration performed.")


def list_wu(args: argparse.Namespace) -> int:
    for label, base in (("active", active_dir(args.root)), ("archive", archive_dir(args.root))):
        if not base.exists():
            continue
        for path in sorted(item for item in base.iterdir() if item.is_dir()):
            state = load_json(state_path(path), {})
            print(f"{label}\t{path.name}\t{state.get('status', 'unknown')}\t{state.get('spec_path', '')}")
    return 0


def status(args: argparse.Namespace) -> int:
    _work_unit_id, wu_path = resolve_wu(args.root, args.id)
    print(json.dumps(update_state(args.root, wu_path, checkpoint_reason="status_observed"), ensure_ascii=False, indent=2))
    return 0


def brief(args: argparse.Namespace) -> int:
    work_unit_id, wu_path = resolve_wu(args.root, args.id)
    state = update_state(args.root, wu_path, checkpoint_reason="brief_generated")
    packet = {
        "work_unit_id": work_unit_id,
        "status": state.get("status"),
        "spec": state.get("spec_path"),
        "plan": state.get("plan_path"),
        "branch": state.get("branch"),
        "head": state.get("head_commit"),
        "next_safe_action": state.get("next_safe_action"),
        "spec_summary": spec_summary(wu_path),
        "latest_evidence": evidence_receipts(wu_path)[-5:],
        "review_track": load_json(review_track_path(wu_path), {}),
    }
    print(json.dumps(packet, ensure_ascii=False, indent=2))
    return 0


def approve_spec(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    state = load_json(state_path(wu_path), {})
    if state.get("spec_approved_hash"):
        raise HarnessError("Spec already has an approved revision; use amend for a material change.")
    path = spec_path(wu_path)
    blocking, warnings = check_spec_document(path, work_unit_id, allow_approval_mismatch=True)
    # A draft is expected here; approval metadata is populated atomically below.
    blocking = [reason for reason in blocking if not reason.startswith("Approved spec")]
    if blocking:
        raise HarnessError("Spec cannot be approved: " + "; ".join(blocking))
    approved_by = (args.approved_by or "").strip()
    if not approved_by.startswith("human:"):
        raise HarnessError("approve-spec requires --approved-by human:<identity>.")
    if not (args.approval_ref or "").strip():
        raise HarnessError("approve-spec requires --approval-ref.")
    approved_at = now_iso()
    approved_hash = spec_content_hash(path)
    update_spec_approval_metadata(
        path,
        {
            "status": "approved",
            "approved_by": approved_by,
            "approved_at": approved_at,
            "approval_ref": args.approval_ref,
            "approved_content_hash": approved_hash,
        },
    )
    state = update_state(
        root,
        wu_path,
        checkpoint_reason="spec_approved",
        status="spec_approved",
        spec_approved_hash=approved_hash,
        spec_approved_at=approved_at,
        spec_approved_by=approved_by,
        spec_approval_ref=args.approval_ref,
        next_safe_action="Create/review the repository-grounded technical plan, then dispatch plan review without pausing the lifecycle.",
        blockers=[],
    )
    print(json.dumps({"work_unit_id": work_unit_id, "status": state["status"], "approved_content_hash": approved_hash, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 0


def amend(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    path = spec_path(wu_path)
    blocking, warnings = check_spec_document(path, work_unit_id, allow_approval_mismatch=True)
    # The old approval hash mismatch is precisely why amend exists.
    blocking = [reason for reason in blocking if "content changed after approval" not in reason]
    if blocking:
        raise HarnessError("Amended spec is invalid: " + "; ".join(blocking))
    actor = (args.actor or "").strip()
    if not actor.startswith("human:"):
        raise HarnessError("Material amendment requires --actor human:<identity>.")
    if not (args.approval_ref or "").strip():
        raise HarnessError("Material amendment requires --approval-ref.")
    old_state = load_json(state_path(wu_path), {})
    new_hash = spec_content_hash(path)
    when = now_iso()
    update_spec_approval_metadata(
        path,
        {
            "status": "approved",
            "approved_by": actor,
            "approved_at": when,
            "approval_ref": args.approval_ref,
            "approved_content_hash": new_hash,
        },
    )
    append_jsonl(
        amendments_path(wu_path),
        {
            "schema_version": AMENDMENT_SCHEMA,
            "amendment_id": "amend-" + uuid.uuid4().hex[:12],
            "work_unit_id": work_unit_id,
            "reason": args.reason,
            "summary": args.summary,
            "actor": actor,
            "approval_ref": args.approval_ref,
            "prior_spec_hash": old_state.get("spec_approved_hash", ""),
            "new_spec_hash": new_hash,
            "created_at": when,
        },
    )
    if review_track_path(wu_path).exists():
        review_track_path(wu_path).unlink()
    state = update_state(
        root,
        wu_path,
        checkpoint_reason="spec_amended",
        generation=int(old_state.get("generation", 1)) + 1,
        status="spec_approved",
        spec_approved_hash=new_hash,
        spec_approved_at=when,
        spec_approved_by=actor,
        spec_approval_ref=args.approval_ref,
        plan_approved_hash="",
        review_track_id="",
        logical_reviewer_session_id="",
        builder_id="",
        builder_session_id="",
        latest_evidence_refs=[],
        blockers=[],
        next_safe_action="Rebuild and re-review the technical plan; previous plan review and evidence are superseded.",
    )
    print(json.dumps({"work_unit_id": work_unit_id, "status": state["status"], "generation": state["generation"], "warnings": warnings}, ensure_ascii=False, indent=2))
    return 0


def _request_review_internal(
    root: Path,
    wu_path: Path,
    mode: str,
    reviewer_id: str,
    reviewer_session: str,
    reviewer_session_source: str,
    planner_id: str = "",
    planner_session: str = "",
    platform_binding: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    state = load_json(state_path(wu_path), {})
    if mode == "plan":
        spec_decision, spec_blocking, _ = check_spec(root, wu_path)
        plan_decision, plan_blocking, _ = check_plan(root, wu_path)
        if spec_decision == "BLOCK" or plan_decision == "BLOCK":
            raise HarnessError("Plan review cannot start: " + "; ".join(spec_blocking + plan_blocking))
        if state.get("status") not in {"spec_approved", "planning", "plan_reviewing", "blocked"}:
            raise HarnessError("Plan review is only valid after spec approval and before implementation.")
        if not planner_id or not planner_session:
            raise HarnessError("Plan review requires planner identity and session.")
        if reviewer_id == planner_id or reviewer_session == planner_session:
            raise HarnessError("Plan reviewer identity and session must differ from the planner.")
        existing = load_json(review_track_path(wu_path), {})
        if existing:
            if reviewer_id != existing.get("reviewer_id") or reviewer_session != existing.get("logical_reviewer_session_id"):
                raise HarnessError("Existing review track can only be reused by its exact reviewer logical session; use reviewer-takeover explicitly.")
            track = existing
        else:
            track = {
                "schema_version": REVIEW_TRACK_SCHEMA,
                "review_track_id": "rt-" + uuid.uuid4().hex[:12],
                "work_unit_id": wu_path.name,
                "generation": 1,
                "reviewer_id": reviewer_id,
                "logical_reviewer_session_id": reviewer_session,
                "reviewer_session_source": reviewer_session_source,
                "platform": (platform_binding or {}).get("platform", ""),
                "platform_session_id": (platform_binding or {}).get("session_id", ""),
                "platform_agent_id": (platform_binding or {}).get("agent_id", ""),
                "plan_review_id": "",
                "close_review_id": "",
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
            write_json(review_track_path(wu_path), track)
        update_state(
            root,
            wu_path,
            checkpoint_reason="plan_review_requested",
            status="plan_reviewing",
            review_track_id=track["review_track_id"],
            logical_reviewer_session_id=reviewer_session,
            current_role="reviewer",
            next_safe_action="Complete plan review in the bound reviewer session; automatically return findings or continue to worker dispatch on PASS.",
        )
    else:
        verification_decision, reasons, _ = check_verification(root, wu_path)
        scope_decision, scope_reasons, _ = check_scope(root, wu_path)
        if verification_decision == "BLOCK" or scope_decision == "BLOCK":
            raise HarnessError("Close review cannot start: " + "; ".join(reasons + scope_reasons))
        track = load_json(review_track_path(wu_path), {})
        if not track:
            raise HarnessError("Close review requires an existing plan-review track.")
        if reviewer_id != track.get("reviewer_id"):
            raise HarnessError("Close review must use the plan reviewer identity.")
        if reviewer_session != track.get("logical_reviewer_session_id"):
            raise HarnessError("Close review must resume the exact plan-review logical session.")
        if reviewer_id == state.get("builder_id") or reviewer_session == state.get("builder_session_id"):
            raise HarnessError("Builder cannot own close review.")
        update_state(
            root,
            wu_path,
            checkpoint_reason="close_review_requested",
            status="reviewing",
            current_role="reviewer",
            next_safe_action="Complete close review in the same reviewer session, re-grounding in current code, diff, and fresh evidence.",
        )
    request_id = "rr-" + uuid.uuid4().hex[:12]
    snapshot = RepoSnapshot.capture(root, str(state.get("base_commit", "")))
    request = {
        "schema_version": REVIEW_REQUEST_SCHEMA,
        "request_id": request_id,
        "work_unit_id": wu_path.name,
        "mode": mode,
        "review_track_id": track["review_track_id"],
        "review_track_generation": track.get("generation", 1),
        "reviewer_id": reviewer_id,
        "logical_reviewer_session_id": reviewer_session,
        "reviewer_session_source": reviewer_session_source,
        "planner_id": planner_id if mode == "plan" else "",
        "planner_session_id": planner_session if mode == "plan" else "",
        "builder_id": state.get("builder_id", "") if mode == "close" else "",
        "builder_session_id": state.get("builder_session_id", "") if mode == "close" else "",
        "spec_hash": state.get("spec_approved_hash", ""),
        "plan_hash": file_hash(plan_path(wu_path)),
        "head_commit": snapshot.head_commit,
        "implementation_diff_hash": snapshot.implementation_diff_hash,
        "workspace_id": snapshot.workspace_id,
        "created_at": now_iso(),
    }
    write_json(review_requests_dir(wu_path) / f"{request_id}.json", request)
    return request


def request_review(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    reviewer_session, source, binding = _role_session(root, work_unit_id, "reviewer", args.reviewer_session, "HARNESS_REVIEWER_SESSION")
    reviewer_id = (args.reviewer_id or os.environ.get("HARNESS_REVIEWER_ID", "")).strip()
    if not reviewer_id or not reviewer_session:
        raise HarnessError("Review requires reviewer identity and a real/attested logical session.")
    planner_id = (args.planner_id or os.environ.get("HARNESS_PLANNER_ID", "")).strip()
    planner_session = (args.planner_session or os.environ.get("HARNESS_PLANNER_SESSION", "")).strip()
    request = _request_review_internal(root, wu_path, args.mode, reviewer_id, reviewer_session, source, planner_id, planner_session, binding)
    print(json.dumps(request, ensure_ascii=False, indent=2))
    return 0


def _submit_review_internal(
    root: Path,
    wu_path: Path,
    request: Mapping[str, Any],
    *,
    decision: str,
    reviewer_id: str,
    reviewer_session: str,
    independence_level: str,
    approval_ref: str,
    evidence_refs: Sequence[str],
    findings: Sequence[str],
    required_rework: Sequence[str],
) -> Dict[str, Any]:
    state = load_json(state_path(wu_path), {})
    track = load_json(review_track_path(wu_path), {})
    mode = str(request.get("mode", ""))
    snapshot = RepoSnapshot.capture(root, str(state.get("base_commit", "")))
    if reviewer_id != request.get("reviewer_id") or reviewer_session != request.get("logical_reviewer_session_id"):
        raise HarnessError("Review submission identity/session differs from the request.")
    if reviewer_id != track.get("reviewer_id") or reviewer_session != track.get("logical_reviewer_session_id"):
        raise HarnessError("Review submission does not come from the active reviewer logical session.")
    if request.get("review_track_generation") != track.get("generation"):
        raise HarnessError("Review request belongs to a superseded reviewer generation.")
    if mode == "plan":
        if request.get("spec_hash") != state.get("spec_approved_hash") or request.get("plan_hash") != file_hash(plan_path(wu_path)):
            raise HarnessError("Spec or plan changed after the review request.")
    else:
        if request.get("head_commit") != snapshot.head_commit:
            raise HarnessError("HEAD changed after close review request; create a new request.")
        if request.get("implementation_diff_hash") != snapshot.implementation_diff_hash:
            raise HarnessError("Implementation changed after close review request.")
        if reviewer_id == state.get("builder_id") or reviewer_session == state.get("builder_session_id"):
            raise HarnessError("Builder cannot submit close review.")
    independent = independence_level in {"separate_role", "fresh_context", "human_gate"}
    review_id = "review-" + uuid.uuid4().hex[:12]
    verdict = {
        "schema_version": REVIEW_VERDICT_SCHEMA,
        "review_id": review_id,
        "request_id": request.get("request_id"),
        "work_unit_id": wu_path.name,
        "mode": mode,
        "decision": decision,
        "review_track_id": track.get("review_track_id"),
        "review_track_generation": track.get("generation"),
        "reviewer_id": reviewer_id,
        "reviewer_session_id": reviewer_session,
        "logical_reviewer_session_id": reviewer_session,
        "planner_id": request.get("planner_id", ""),
        "planner_session_id": request.get("planner_session_id", ""),
        "builder_id": state.get("builder_id", ""),
        "builder_session_id": state.get("builder_session_id", ""),
        "independence_level": independence_level,
        "is_independent": independent,
        "approval_ref": approval_ref,
        "reviewed_spec_hash": state.get("spec_approved_hash", ""),
        "reviewed_plan_hash": file_hash(plan_path(wu_path)) if mode == "plan" else state.get("plan_approved_hash", ""),
        "reviewed_head_commit": snapshot.head_commit,
        "reviewed_implementation_diff_hash": snapshot.implementation_diff_hash,
        "evidence_refs": list(evidence_refs),
        "findings": list(findings),
        "required_rework": list(required_rework),
        "re_grounded_on_close": mode == "close",
        "read_only_attestation": True,
        "created_at": now_iso(),
    }
    errors = review_independence_errors(verdict)
    if errors:
        raise HarnessError("Review independence invalid: " + "; ".join(errors))
    write_json(review_verdicts_dir(wu_path) / f"{review_id}.json", verdict)
    if decision == "PASS":
        if mode == "plan":
            track.update({"plan_review_id": review_id, "close_review_id": "", "updated_at": now_iso()})
            write_json(review_track_path(wu_path), track)
            update_state(
                root,
                wu_path,
                checkpoint_reason="plan_review_passed",
                status="ready",
                plan_approved_hash=file_hash(plan_path(wu_path)),
                current_role="conductor",
                next_safe_action="Start an isolated worker session/worktree and implement the approved plan using TDD.",
            )
        else:
            track.update({"close_review_id": review_id, "updated_at": now_iso()})
            write_json(review_track_path(wu_path), track)
            update_state(
                root,
                wu_path,
                checkpoint_reason="close_review_passed",
                status="reviewing",
                current_role="conductor",
                next_safe_action="Run finalize-check, synchronize PR/CI, then archive or integrate.",
            )
    else:
        next_action = "Revise the plan and request review again." if mode == "plan" else "Return findings to the worker; after changes, rerun evidence and close review in this same reviewer session."
        update_state(root, wu_path, checkpoint_reason="review_changes_requested", status="planning" if mode == "plan" else "running", current_role="planner" if mode == "plan" else "worker", blockers=list(required_rework) or list(findings), next_safe_action=next_action)
    return verdict


def submit_review(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    request_id = args.request_id or ""
    request = load_json(review_requests_dir(wu_path) / f"{request_id}.json", {}) if request_id else latest_review_request(wu_path, args.mode, pending_only=True)
    if not request or request.get("mode") != args.mode:
        raise HarnessError("Matching pending review request not found.")
    reviewer_session, _source, _binding = _role_session(root, work_unit_id, "reviewer", args.reviewer_session, "HARNESS_REVIEWER_SESSION", str(request.get("logical_reviewer_session_id", "")))
    reviewer_id = (args.reviewer_id or os.environ.get("HARNESS_REVIEWER_ID", "") or str(request.get("reviewer_id", ""))).strip()
    verdict = _submit_review_internal(
        root,
        wu_path,
        request,
        decision=args.decision,
        reviewer_id=reviewer_id,
        reviewer_session=reviewer_session,
        independence_level=args.independence_level,
        approval_ref=args.approval_ref or "",
        evidence_refs=args.evidence_ref or [],
        findings=args.finding or [],
        required_rework=args.required_rework or [],
    )
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if args.decision == "PASS" else 2


def reviewer_takeover(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    track = load_json(review_track_path(wu_path), {})
    if not track:
        raise HarnessError("No review track exists to take over.")
    if not args.approved_by.startswith("human:") or not args.approval_ref:
        raise HarnessError("Reviewer takeover requires human approval and approval_ref.")
    session = args.new_reviewer_session.strip()
    if not session:
        raise HarnessError("Reviewer takeover requires a new logical reviewer session.")
    old = dict(track)
    track.update(
        {
            "generation": int(track.get("generation", 1)) + 1,
            "reviewer_id": args.new_reviewer_id,
            "logical_reviewer_session_id": session,
            "reviewer_session_source": "explicit_takeover",
            "platform": "",
            "platform_session_id": "",
            "platform_agent_id": "",
            "plan_review_id": "",
            "close_review_id": "",
            "takeover": {
                "old_reviewer_id": old.get("reviewer_id"),
                "old_logical_session_id": old.get("logical_reviewer_session_id"),
                "reason": args.reason,
                "approved_by": args.approved_by,
                "approval_ref": args.approval_ref,
                "created_at": now_iso(),
            },
            "updated_at": now_iso(),
        }
    )
    write_json(review_track_path(wu_path), track)
    update_state(root, wu_path, checkpoint_reason="reviewer_takeover", status="planning", plan_approved_hash="", logical_reviewer_session_id=session, latest_evidence_refs=[], blockers=[], next_safe_action="The new reviewer must perform plan review from current repo truth before implementation/close review continues.")
    print(json.dumps({"work_unit_id": work_unit_id, "review_track": track, "continuity": "explicit_takeover_not_original_session_continuity"}, ensure_ascii=False, indent=2))
    return 0


def start_work(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    decision, reasons, _ = check_plan_review(root, wu_path)
    if decision == "BLOCK":
        raise HarnessError("Implementation cannot start: " + "; ".join(reasons))
    state = load_json(state_path(wu_path), {})
    track = load_json(review_track_path(wu_path), {})
    builder_session, _source, binding = _role_session(root, work_unit_id, "worker", args.builder_session, "HARNESS_BUILDER_SESSION")
    builder_id = (args.builder_id or os.environ.get("HARNESS_BUILDER_ID", "")).strip()
    if not builder_id and binding:
        builder_id = _default_builder_id(binding, builder_session)
    if not builder_id or not builder_session:
        raise HarnessError("start-work requires builder identity and session.")
    if builder_id in {track.get("reviewer_id"), latest_review_request(wu_path, "plan").get("planner_id") if latest_review_request(wu_path, "plan") else ""}:
        raise HarnessError("Worker identity must differ from planner and reviewer.")
    plan_request = latest_review_request(wu_path, "plan") or {}
    if builder_session in {track.get("logical_reviewer_session_id"), plan_request.get("planner_session_id")}:
        raise HarnessError("Worker session must differ from planner and reviewer sessions.")
    state = update_state(root, wu_path, checkpoint_reason="worker_started", status="running", builder_id=builder_id, builder_session_id=builder_session, current_role="worker", blockers=[], next_safe_action="Implement behavior slices with RED reason verification, GREEN, refactor, then final evidence and automatic close review.")
    print(json.dumps({"work_unit_id": work_unit_id, "status": state["status"], "builder_id": builder_id, "builder_session_id": builder_session}, ensure_ascii=False, indent=2))
    return 0


def resume_work(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    state = load_json(state_path(wu_path), {})
    if state.get("status") not in {"handoff", "blocked", "running", "verifying"}:
        raise HarnessError("resume-work is only valid for paused/blocked/running implementation.")
    decision, reasons, _ = check_plan_review(root, wu_path)
    if decision == "BLOCK":
        raise HarnessError("Worker resume blocked: " + "; ".join(reasons))
    builder_id = (args.builder_id or state.get("builder_id", "")).strip()
    builder_session, _source, _binding = _role_session(root, work_unit_id, "worker", args.builder_session, "HARNESS_BUILDER_SESSION")
    track = load_json(review_track_path(wu_path), {})
    if not builder_id or not builder_session:
        raise HarnessError("resume-work requires builder identity and a new/current session.")
    if builder_id == track.get("reviewer_id") or builder_session == track.get("logical_reviewer_session_id"):
        raise HarnessError("Worker cannot reuse reviewer identity/session.")
    update_state(root, wu_path, checkpoint_reason="worker_resumed", status="running", builder_id=builder_id, builder_session_id=builder_session, current_role="worker", blockers=[], next_safe_action="Continue implementation; rerun all affected final evidence before close review.")
    print(json.dumps({"work_unit_id": work_unit_id, "status": "running", "builder_id": builder_id, "builder_session_id": builder_session}, ensure_ascii=False, indent=2))
    return 0



def verify(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    spec_decision, spec_blocking, _ = check_spec(root, wu_path)
    if spec_decision == "BLOCK":
        raise HarnessError("Spec gate blocks verification: " + "; ".join(spec_blocking))
    plan_decision, plan_blocking, _ = check_plan_review(root, wu_path)
    if plan_decision == "BLOCK":
        raise HarnessError("Plan review gate blocks verification: " + "; ".join(plan_blocking))
    state = load_json(state_path(wu_path), {})
    if state.get("status") not in {"running", "verifying", "reviewing"}:
        raise HarnessError("Verification is available only after implementation has started.")
    try:
        contract = contract_core.load_contract(spec_path(wu_path))
        plan = plan_core.load_plan(plan_path(wu_path))
    except (contract_core.ContractError, plan_core.PlanError) as exc:
        raise HarnessError(str(exc)) from exc
    claim = contract_core.evidence_by_id(contract, args.claim)
    if claim is None:
        expected = sorted(str(row.get("id", "")) for row in contract_core.evidence_items(contract))
        raise HarnessError(f"Unknown required evidence claim {args.claim!r}; expected one of {expected}")

    behavior_id = args.behavior or ""
    expected_failure: Mapping[str, Any] = {}
    if args.phase == "final":
        check_id = str(claim.get("check_id", ""))
        if args.expect not in {None, "pass"}:
            raise HarnessError("Final verification must expect pass; expected failures belong to RED.")
    else:
        if not behavior_id:
            raise HarnessError("RED/GREEN verification requires --behavior to bind the command to an approved TDD slice.")
        try:
            behavior = plan_core.behavior_slice(plan, behavior_id)
        except plan_core.PlanError as exc:
            raise HarnessError(str(exc)) from exc
        if str(behavior.get("claim_ref", "")) != args.claim:
            raise HarnessError(f"Behavior {behavior_id} is not bound to claim {args.claim}.")
        phase_value = behavior.get(args.phase, {})
        if not isinstance(phase_value, dict):
            raise HarnessError(f"Behavior {behavior_id} has no valid {args.phase} definition.")
        check_id = str(phase_value.get("check_id", ""))
        if args.phase == "red":
            expected_failure = phase_value.get("expected_failure", {}) if isinstance(phase_value.get("expected_failure"), dict) else {}
            if args.expect not in {None, "fail"}:
                raise HarnessError("RED verification must expect a nonzero failure for the approved reason.")
        elif args.expect not in {None, "pass"}:
            raise HarnessError("GREEN verification must expect pass.")
    try:
        definition = contract_core.check_definition(contract, check_id)
        execution = run_check(
            root,
            check_id,
            definition,
            argv_override=list(args.command or []) or None,
            timeout_override=args.timeout,
        )
    except contract_core.ContractError as exc:
        raise HarnessError(str(exc)) from exc

    started = now_iso()
    if args.phase == "red":
        expected_met, mismatch_reasons = red_failure_matches(execution, expected_failure)
        expected_description: Any = dict(expected_failure)
    else:
        expected_met = execution.exit_code == 0
        mismatch_reasons = [] if expected_met else [f"Expected exit 0, observed {execution.exit_code}."]
        expected_description = {"kind": "exit_zero"}
    result = "pass" if expected_met else "fail"
    ended = now_iso()
    receipt_id = "ev-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
    base = str(state.get("base_commit", ""))
    log_path = evidence_artifacts_dir(wu_path) / f"{receipt_id}.log"
    try:
        relative_cwd = execution.cwd.relative_to(root.resolve()).as_posix() or "."
    except ValueError:
        relative_cwd = str(execution.cwd)
    header = {
        "receipt_id": receipt_id,
        "work_unit_id": work_unit_id,
        "claim_ref": args.claim,
        "behavior_ref": behavior_id,
        "phase": args.phase,
        "check_id": check_id,
        "check_definition_hash": execution.definition_hash,
        "runner": execution.runner,
        "argv": execution.argv,
        "cwd": relative_cwd,
        "expected": expected_description,
        "exit_code": execution.exit_code,
        "mismatch_reasons": mismatch_reasons,
        "started_at": started,
        "ended_at": ended,
        "duration_seconds": execution.duration_seconds,
    }
    atomic_write_text(
        log_path,
        json.dumps(header, ensure_ascii=False, indent=2)
        + "\n\n--- stdout ---\n" + execution.stdout
        + "\n--- stderr ---\n" + execution.stderr + "\n",
    )
    snapshot = RepoSnapshot.capture(root, base)
    receipt = {
        "schema_version": EVIDENCE_SCHEMA,
        "receipt_id": receipt_id,
        "work_unit_id": work_unit_id,
        "claim_ref": args.claim,
        "behavior_ref": behavior_id,
        "actor": "controller",
        "observation": "controller_executed_check",
        "type": args.type,
        "phase": args.phase,
        "check_id": check_id,
        "check_definition_hash": execution.definition_hash,
        "runner": execution.runner,
        "command": shlex.join(execution.argv),
        "argv": execution.argv,
        "cwd": relative_cwd,
        "expected_outcome": "declared_red_failure" if args.phase == "red" else "exit_zero",
        "expected_failure": expected_description if args.phase == "red" else {},
        "observed_outcome": "exit_zero" if execution.exit_code == 0 else "exit_nonzero",
        "result": result,
        "mismatch_reasons": mismatch_reasons,
        "started_at": started,
        "ended_at": ended,
        "duration_seconds": execution.duration_seconds,
        "exit_code": execution.exit_code,
        "repository_id": snapshot.repository_id,
        "base_commit": base,
        "head_commit": snapshot.head_commit,
        "branch": snapshot.branch,
        "workspace_id": snapshot.workspace_id,
        "spec_hash": str(state.get("spec_approved_hash", "")),
        "plan_hash": str(state.get("plan_approved_hash", "")),
        "diff_hash": snapshot.diff_hash,
        "implementation_diff_hash": snapshot.implementation_diff_hash,
        "changed_files": list(snapshot.changed_files),
        "implementation_changed_files": list(snapshot.implementation_changed_files),
        "verification_scope": args.verification_scope,
        "freshness_basis": "controller_executed_structured_check",
        "command_log_ref": log_path.relative_to(root).as_posix(),
        "command_log_hash": file_hash(log_path),
        "environment_ref": args.environment_ref or "local",
        "note": args.note or "",
    }
    append_jsonl(receipts_path(wu_path), receipt)
    latest = list(state.get("latest_evidence_refs", []) or [])
    failures = list(state.get("known_failures", []) or [])
    if result == "pass" and args.phase == "final":
        latest = [value for value in latest if value != receipt_id] + [receipt_id]
    elif result == "fail":
        failures.append(f"{args.claim}/{args.phase}: {receipt_id}: " + "; ".join(mismatch_reasons))
    update_state(
        root,
        wu_path,
        status="verifying",
        current_role="worker",
        latest_evidence_refs=latest[-20:],
        known_failures=failures[-20:],
        next_safe_action=(
            "Correct the test/implementation mismatch and rerun the bound check."
            if result == "fail"
            else "Run remaining required evidence, then automatically dispatch close review."
        ),
        checkpoint_reason=f"verification_{args.phase}_{result}",
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if expected_met else 2




def record_skipped(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    try:
        contract = contract_core.load_contract(spec_path(wu_path))
    except contract_core.ContractError as exc:
        raise HarnessError(str(exc)) from exc
    claim = contract_core.evidence_by_id(contract, args.claim)
    if claim is None:
        raise HarnessError(f"Unknown required evidence claim {args.claim!r}.")
    state = load_json(state_path(wu_path), {})
    if state.get("status") not in {"running", "verifying", "reviewing"}:
        raise HarnessError("Skipped verification can only be recorded after implementation has started.")
    check_id = str(claim.get("check_id", ""))
    definition = contract_core.check_definition(contract, check_id)
    base = str(state.get("base_commit", ""))
    snapshot = RepoSnapshot.capture(root, base)
    receipt = {
        "schema_version": EVIDENCE_SCHEMA,
        "receipt_id": "ev-" + uuid.uuid4().hex[:12],
        "work_unit_id": work_unit_id,
        "claim_ref": args.claim,
        "actor": args.actor,
        "observation": "skipped_not_evidence",
        "type": args.type,
        "phase": "final",
        "check_id": check_id,
        "check_definition_hash": contract_core.check_definition_hash(check_id, definition),
        "runner": str(definition.get("runner", "exec")),
        "command": "",
        "argv": [],
        "cwd": str(definition.get("cwd", ".")),
        "expected_outcome": "exit_zero",
        "expected_failure": {},
        "observed_outcome": "not_run",
        "result": "skipped",
        "mismatch_reasons": ["check_not_run"],
        "started_at": now_iso(),
        "ended_at": now_iso(),
        "duration_seconds": 0.0,
        "exit_code": None,
        "repository_id": snapshot.repository_id,
        "base_commit": base,
        "head_commit": snapshot.head_commit,
        "branch": snapshot.branch,
        "workspace_id": snapshot.workspace_id,
        "spec_hash": str(state.get("spec_approved_hash", "")),
        "plan_hash": str(state.get("plan_approved_hash", "")),
        "diff_hash": snapshot.diff_hash,
        "implementation_diff_hash": snapshot.implementation_diff_hash,
        "changed_files": list(snapshot.changed_files),
        "implementation_changed_files": list(snapshot.implementation_changed_files),
        "verification_scope": args.verification_scope,
        "freshness_basis": "not_applicable",
        "command_log_ref": "",
        "command_log_hash": "",
        "environment_ref": args.environment_ref or "local",
        "skip": {
            "reason": args.reason,
            "replacement_evidence": args.replacement,
            "risk_impact": args.risk_impact,
            "owner": args.owner,
        },
        "note": "Skipped checks never count as pass evidence.",
    }
    append_jsonl(receipts_path(wu_path), receipt)
    update_state(
        root,
        wu_path,
        status="blocked",
        blockers=[f"Required evidence {args.claim} was skipped: {args.reason}"],
        next_safe_action="Produce the required evidence, revise and reapprove the spec, or obtain the risk gate required by policy.",
        checkpoint_reason="required_evidence_skipped",
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0



# ---------------------------------------------------------------------------
# Platform review dispatch and routing
# ---------------------------------------------------------------------------

def _review_output_schema() -> Dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["decision", "findings", "required_rework", "evidence_refs"],
        "properties": {
            "decision": {"enum": ["PASS", "CHANGES_REQUESTED", "REJECTED", "BLOCKED", "NEEDS_HUMAN_GATE"]},
            "findings": {"type": "array", "items": {"type": "string"}},
            "required_rework": {"type": "array", "items": {"type": "string"}},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
        },
    }


def _review_prompt(root: Path, wu_path: Path, mode: str) -> str:
    state = load_json(state_path(wu_path), {})
    evidence = verification_detail_report(root, wu_path)[0]
    snapshot = RepoSnapshot.capture(root, str(state.get("base_commit", "")))
    mode_instruction = (
        "Review the technical plan against the current repository truth. Inspect all relevant code/tests, not only cited anchors. Do not modify files."
        if mode == "plan"
        else "Re-ground in the current repository, final diff, tests, and receipts. Treat the prior plan as a hypothesis, not truth. Do not modify files."
    )
    return f"""You are the independent read-only {mode} reviewer for Work Unit {wu_path.name}.

{mode_instruction}

Authoritative inputs:
- tracked contract: {spec_path(wu_path).relative_to(root).as_posix()}
- local technical plan: {plan_path(wu_path).relative_to(root).as_posix()}
- current branch/head: {snapshot.branch} / {snapshot.head_commit}
- implementation diff hash: {snapshot.implementation_diff_hash}
- evidence summary: {json.dumps(evidence, ensure_ascii=False)}

Check intent/scope, repository grounding, architecture, TDD oracle quality, fresh claim-relative evidence, regressions, risk, and maintainability. Return only the requested structured verdict. PASS only when no material finding remains.
"""


def adapter_doctor(args: argparse.Namespace) -> int:
    platforms = [args.platform] if args.platform else ["codex", "claude"]
    rows = []
    failed = False
    for platform in platforms:
        probe = platform_adapters.probe(platform, args.executable or "")
        row = {"platform": probe.platform, "available": probe.available, "executable": probe.executable, "capabilities": probe.capabilities, "detail": probe.detail}
        row["decision"] = "PASS" if probe.available and all(probe.capabilities.get(key) for key in ("resume", "structured_output", "read_only")) else "BLOCK"
        failed = failed or row["decision"] == "BLOCK"
        rows.append(row)
    print(json.dumps({"adapters": rows}, ensure_ascii=False, indent=2))
    return 2 if failed and args.strict else 0


def dispatch_review(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    platform = args.platform
    reviewer_id = args.reviewer_id or f"reviewer:{platform}"
    track = load_json(review_track_path(wu_path), {})
    resume_raw = str(track.get("platform_session_id", "")) if args.mode == "close" else ""
    if args.mode == "close":
        if not track:
            raise HarnessError("Close dispatch requires an existing plan-review track.")
        if track.get("platform") and track.get("platform") != platform:
            raise HarnessError("Close review must resume the platform used by plan review; use explicit takeover otherwise.")
        reviewer_id = str(track.get("reviewer_id", reviewer_id))
    prompt_dir = wu_path / "reviews" / "dispatch"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = prompt_dir / f"{args.mode}-prompt.md"
    schema_file = prompt_dir / "review-output.schema.json"
    atomic_write_text(prompt_file, _review_prompt(root, wu_path, args.mode))
    write_json(schema_file, _review_output_schema())
    command = platform_adapters.review_command(platform, prompt_file=prompt_file, schema_file=schema_file, cwd=root, session_id=resume_raw, executable=args.executable or "")
    if args.dry_run:
        print(json.dumps({"work_unit_id": work_unit_id, "mode": args.mode, "platform": platform, "resume_session_id": resume_raw, "command": command, "prompt": prompt_file.relative_to(root).as_posix(), "state_changed": False}, ensure_ascii=False, indent=2))
        return 0
    try:
        run = platform_adapters.run_review(platform, prompt_file=prompt_file, schema_file=schema_file, cwd=root, session_id=resume_raw, executable=args.executable or "", timeout_seconds=args.timeout)
    except platform_adapters.AdapterError as exc:
        raise HarnessError(f"Reviewer adapter failed closed: {exc}") from exc
    if not run.session_id:
        raise HarnessError("Reviewer adapter returned no resumable platform session id; review was not accepted.")
    event = {"platform": platform, "session_id": run.session_id, "agent_id": "", "agent_type": "reviewer"}
    binding = session_core.record(root, event, work_unit_id=work_unit_id, role="reviewer", observed_at=now_iso())
    logical = str(binding["logical_session_id"])
    if args.mode == "plan":
        planner_id = args.planner_id or os.environ.get("HARNESS_PLANNER_ID", "planner:conductor")
        planner_session = args.planner_session or os.environ.get("HARNESS_PLANNER_SESSION", session_id())
    else:
        planner_id = planner_session = ""
        if logical != track.get("logical_reviewer_session_id"):
            raise HarnessError("Resumed platform session does not map to the logical reviewer session bound at plan review.")
    request = _request_review_internal(root, wu_path, args.mode, reviewer_id, logical, "platform_adapter", planner_id, planner_session, binding)
    structured = run.structured_result
    verdict = _submit_review_internal(
        root,
        wu_path,
        request,
        decision=str(structured.get("decision", "BLOCKED")),
        reviewer_id=reviewer_id,
        reviewer_session=logical,
        independence_level="separate_role",
        approval_ref="",
        evidence_refs=[str(value) for value in structured.get("evidence_refs", [])],
        findings=[str(value) for value in structured.get("findings", [])],
        required_rework=[str(value) for value in structured.get("required_rework", [])],
    )
    track = load_json(review_track_path(wu_path), {})
    track.update({"platform": platform, "platform_session_id": run.session_id, "platform_agent_id": "", "logical_reviewer_session_id": logical, "updated_at": now_iso()})
    write_json(review_track_path(wu_path), track)
    print(json.dumps({"adapter": platform, "platform_session_id": run.session_id, "logical_reviewer_session_id": logical, "verdict": verdict}, ensure_ascii=False, indent=2))
    return 0 if verdict.get("decision") == "PASS" else 2


def _worker_output_schema() -> Dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["status", "summary", "evidence_refs", "blockers", "next_safe_action"],
        "properties": {
            "status": {"enum": ["COMPLETED", "BLOCKED", "NEEDS_HUMAN"]},
            "summary": {"type": "string"},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "blockers": {"type": "array", "items": {"type": "string"}},
            "next_safe_action": {"type": "string"},
        },
    }


def _goal_packet(root: Path, wu_path: Path, thread_ref: str = "") -> Dict[str, Any]:
    state = load_json(state_path(wu_path), {})
    if not state.get("spec_approved_hash") or not state.get("plan_approved_hash"):
        raise HarnessError("Goal projection requires approved spec and plan review.")
    try:
        contract = contract_core.load_contract(spec_path(wu_path))
        plan = plan_core.load_plan(plan_path(wu_path))
    except (contract_core.ContractError, plan_core.PlanError) as exc:
        raise HarnessError(str(exc)) from exc
    generation = int(state.get("generation", 1))
    return {
        "schema_version": GOAL_SCHEMA,
        "work_unit_id": wu_path.name,
        "goal_id": f"goal-{wu_path.name}-{generation}",
        "generation": generation,
        "thread_ref": thread_ref,
        "objective": str(contract.get("intent", "")),
        "completion_conditions": [str(item.get("claim", "")) for item in contract_core.evidence_items(contract)],
        "verification_surface": [str(item.get("check_id", "")) for item in contract_core.evidence_items(contract)],
        "constraints": contract.get("scope", {}),
        "blocked_conditions": contract.get("stop_conditions", {}).get("blocked", []) if isinstance(contract.get("stop_conditions"), dict) else [],
        "plan_behavior_slices": [str(row.get("id", "")) for row in plan.get("behavior_slices", []) if isinstance(row, dict)],
        "spec_hash": state.get("spec_approved_hash"),
        "plan_hash": state.get("plan_approved_hash"),
        "acceptance_authority": "harness_controller_not_goal_completion",
        "created_at": now_iso(),
    }


def _worker_prompt(root: Path, wu_path: Path, platform: str, thread_ref: str = "") -> str:
    state = load_json(state_path(wu_path), {})
    snapshot = RepoSnapshot.capture(root, str(state.get("base_commit", "")))
    goal = _goal_packet(root, wu_path, thread_ref)
    goal_path = wu_path / "platform" / "goal-projection.json"
    write_json(goal_path, goal)
    return f"""You are the isolated implementation worker for Work Unit {wu_path.name}.

Authoritative inputs:
- tracked approved contract: {spec_path(wu_path).relative_to(root).as_posix()}
- approved technical plan: {plan_path(wu_path).relative_to(root).as_posix()}
- controller goal projection: {goal_path.relative_to(root).as_posix()}
- repository branch/head: {snapshot.branch} / {snapshot.head_commit}

Use repository code, tests, and runtime as current project truth. Implement only the approved behavior slices and write boundary. Follow behavior-first TDD: produce a RED receipt for the declared reason, make the smallest GREEN change, refactor under passing tests, then run every final required check through `harnessctl verify`. Do not edit the approved spec or plan during implementation. Do not submit review verdicts. Stop and return BLOCKED/NEEDS_HUMAN on material intent, scope, risk, or evidence-plan drift.

For Codex, treat the goal projection as the thread Goal contract, but never treat Goal completion as Work Unit acceptance. Return only the requested structured worker result after recording receipts and a recovery checkpoint.
"""


def _codex_goal_objective(root: Path, wu_path: Path) -> str:
    """Keep the platform Goal compact; detailed truth remains in repo artifacts."""

    spec_ref = spec_path(wu_path).relative_to(root).as_posix()
    plan_ref = plan_path(wu_path).relative_to(root).as_posix()
    projection_ref = (wu_path / "platform" / "goal-projection.json").relative_to(root).as_posix()
    objective = (
        f"Implement approved Work Unit {wu_path.name}. Read {spec_ref}, {plan_ref}, and {projection_ref} first. "
        "Follow the approved behavior slices with RED-for-the-declared-reason, minimal GREEN, and refactor under passing tests. "
        "Run each required check through harnessctl verify and leave fresh receipts plus a recovery checkpoint. "
        "Do not edit the approved spec/plan or cross its write boundary. Stop for material intent, scope, risk, or evidence-plan drift. "
        "Goal completion is only a worker signal; the Harness Controller, independent reviewer, and any human risk gate own acceptance."
    )
    if len(objective) > 4000:
        raise HarnessError("Generated Codex Goal exceeds the platform limit; shorten Work Unit identifiers/paths.")
    return objective


def dispatch_worker(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    state = load_json(state_path(wu_path), {})
    plan_decision, reasons, _ = check_plan_review(root, wu_path)
    if plan_decision == "BLOCK":
        raise HarnessError("Worker dispatch blocked: " + "; ".join(reasons))
    if state.get("status") not in {"ready", "running", "verifying", "handoff", "blocked"}:
        raise HarnessError(f"Worker dispatch is not valid while status is {state.get('status')!r}.")

    platform = args.platform
    builder_id = args.builder_id or f"worker:{platform}"
    binding = session_core.latest(root, work_unit_id, "worker")
    resume_raw = str(binding.get("session_id", "")) if args.resume else ""
    prompt_dir = wu_path / "platform" / "worker"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_file = prompt_dir / "worker-prompt.md"
    schema_file = prompt_dir / "worker-output.schema.json"
    atomic_write_text(prompt_file, _worker_prompt(root, wu_path, platform, resume_raw))
    write_json(schema_file, _worker_output_schema())
    command = platform_adapters.worker_command(
        platform,
        prompt_file=prompt_file,
        schema_file=schema_file,
        cwd=root,
        session_id=resume_raw,
        executable=args.executable or "",
        output_file=prompt_file.with_suffix(".result.json") if platform == "codex" else None,
    )
    if args.dry_run:
        print(json.dumps({
            "work_unit_id": work_unit_id,
            "platform": platform,
            "resume_session_id": resume_raw,
            "command": command,
            "prompt": prompt_file.relative_to(root).as_posix(),
            "goal_bootstrap": "codex_app_server" if platform == "codex" else "not_applicable",
            "state_changed": False,
        }, ensure_ascii=False, indent=2))
        return 0

    goal_binding: Optional[platform_adapters.GoalBinding] = None
    goal_warning = ""
    if platform == "codex":
        goal_state_path = wu_path / "platform" / "codex-goal-state.json"
        try:
            goal_binding = platform_adapters.ensure_codex_goal(
                cwd=root,
                objective=_codex_goal_objective(root, wu_path),
                session_id=resume_raw,
                executable=args.executable or "",
                timeout_seconds=min(max(5, args.timeout), 30),
            )
            resume_raw = goal_binding.thread_id
            atomic_write_text(prompt_file, _worker_prompt(root, wu_path, platform, resume_raw))
            write_json(
                goal_state_path,
                {
                    "schema_version": GOAL_BINDING_SCHEMA,
                    "work_unit_id": work_unit_id,
                    "status": "active",
                    "platform": "codex",
                    "thread_id": goal_binding.thread_id,
                    "session_id": goal_binding.session_id,
                    "objective_hash": hashlib.sha256(goal_binding.objective.encode("utf-8")).hexdigest(),
                    "goal": goal_binding.goal,
                    "bound_at": now_iso(),
                    "acceptance_authority": "harness_controller_not_goal_completion",
                },
            )
        except platform_adapters.AdapterError as exc:
            # Goal is an execution enhancement, not a lifecycle authority. A
            # platform-specific Goal failure may degrade to ordinary exec, but
            # Controller evidence/review gates remain unchanged and visible.
            goal_warning = str(exc)
            write_json(
                goal_state_path,
                {
                    "schema_version": GOAL_BINDING_SCHEMA,
                    "work_unit_id": work_unit_id,
                    "status": "degraded",
                    "platform": "codex",
                    "thread_id": resume_raw,
                    "warning": goal_warning,
                    "recorded_at": now_iso(),
                    "acceptance_authority": "harness_controller_not_goal_completion",
                },
            )

    # Goal bootstrap may have created the real thread before the execution
    # turn, so reconstruct argv after the thread id is known.
    command = platform_adapters.worker_command(
        platform,
        prompt_file=prompt_file,
        schema_file=schema_file,
        cwd=root,
        session_id=resume_raw,
        executable=args.executable or "",
        output_file=prompt_file.with_suffix(".result.json") if platform == "codex" else None,
    )

    provisional = resume_raw or f"dispatch:{platform}:{uuid.uuid4().hex[:12]}"
    if state.get("status") == "ready":
        start_work(argparse.Namespace(root=root, id=work_unit_id, builder_id=builder_id, builder_session=provisional))
    else:
        resume_work(argparse.Namespace(root=root, id=work_unit_id, builder_id=builder_id, builder_session=provisional))
    try:
        run = platform_adapters.run_worker(
            platform,
            prompt_file=prompt_file,
            schema_file=schema_file,
            cwd=root,
            session_id=resume_raw,
            executable=args.executable or "",
            timeout_seconds=args.timeout,
            env={"HARNESS_WORK_UNIT_ID": work_unit_id, "HARNESS_BUILDER_ID": builder_id},
        )
    except platform_adapters.AdapterError as exc:
        update_state(
            root,
            wu_path,
            checkpoint_reason="worker_adapter_failed",
            status="blocked",
            current_role="conductor",
            blockers=[str(exc)],
            next_safe_action="Inspect the adapter failure and resume the worker without weakening controller gates.",
        )
        raise HarnessError(f"Worker adapter failed closed: {exc}") from exc
    if not run.session_id:
        update_state(root, wu_path, checkpoint_reason="worker_session_missing", status="blocked", blockers=["Worker adapter returned no resumable platform session id."], next_safe_action="Repair the platform adapter or bind a verified worker session explicitly.")
        raise HarnessError("Worker adapter returned no resumable platform session id.")

    event = {"platform": platform, "session_id": run.session_id, "agent_id": "", "agent_type": "worker"}
    observed = session_core.record(root, event, work_unit_id=work_unit_id, role="worker", observed_at=now_iso())
    structured = run.structured_result
    raw_path = prompt_dir / f"worker-result-{uuid.uuid4().hex[:8]}.json"
    write_json(raw_path, {"session_id": run.session_id, "structured_result": structured, "raw_result": run.raw_result})
    worker_status = str(structured.get("status", "BLOCKED"))
    blockers = [str(value) for value in structured.get("blockers", [])]
    next_action = str(structured.get("next_safe_action", "")) or "Inspect worker output and continue from the controller checkpoint."
    if worker_status in {"BLOCKED", "NEEDS_HUMAN"}:
        update_state(
            root,
            wu_path,
            checkpoint_reason="worker_reported_blocked",
            status="blocked",
            current_role="conductor",
            builder_id=builder_id,
            builder_session_id=observed["logical_session_id"],
            blockers=blockers or [worker_status],
            next_safe_action=next_action,
        )
        print(json.dumps({"adapter": platform, "platform_session_id": run.session_id, "worker_result": structured, "output": raw_path.relative_to(root).as_posix()}, ensure_ascii=False, indent=2))
        return 2

    update_state(
        root,
        wu_path,
        checkpoint_reason="worker_completed_turn",
        status="verifying",
        current_role="worker",
        builder_id=builder_id,
        builder_session_id=observed["logical_session_id"],
        blockers=[],
        next_safe_action="Dispatch close review automatically if all final evidence remains fresh; otherwise rerun missing checks.",
    )
    verification, verification_reasons, _ = check_verification(root, wu_path)
    result = {
        "adapter": platform,
        "platform_session_id": run.session_id,
        "logical_worker_session_id": observed["logical_session_id"],
        "codex_goal": {
            "status": "active" if goal_binding else "degraded" if platform == "codex" else "not_applicable",
            "thread_id": goal_binding.thread_id if goal_binding else resume_raw if platform == "codex" else "",
            "warning": goal_warning,
        },
        "worker_result": structured,
        "verification": verification,
        "verification_reasons": verification_reasons,
        "output": raw_path.relative_to(root).as_posix(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if verification != "BLOCK" else 2


def advance(args: argparse.Namespace) -> int:
    """Execute deterministic automatic transitions until a human/worker gate."""
    work_unit_id, wu_path = resolve_wu(args.root, args.id)
    events: List[Dict[str, Any]] = []
    for _step in range(max(1, args.max_steps)):
        decision = route_decision(args.root, wu_path, args.platform)
        events.append(dict(decision))
        action = str(decision.get("action", ""))
        if args.dry_run:
            print(json.dumps({"work_unit_id": work_unit_id, "planned_transitions": events, "state_changed": False}, ensure_ascii=False, indent=2))
            return 0
        if action in {
            "human_clarification",
            "complete_plan",
            "continue_tdd_and_evidence",
            "continue_review_or_rework",
            "resume_session_or_worker",
            "native_plan_review",
            "native_worker",
            "native_close_review",
            "none",
        }:
            print(json.dumps({"work_unit_id": work_unit_id, "stopped_at": action, "events": events}, ensure_ascii=False, indent=2))
            return 2 if args.strict and action not in {"none"} else 0
        if action in {"dispatch_plan_review", "dispatch_close_review"}:
            code = dispatch_review(argparse.Namespace(
                root=args.root,
                id=work_unit_id,
                mode="plan" if action == "dispatch_plan_review" else "close",
                platform=args.platform,
                reviewer_id=args.reviewer_id,
                planner_id=args.planner_id,
                planner_session=args.planner_session,
                executable=args.reviewer_executable or args.executable,
                timeout=args.review_timeout,
                dry_run=False,
            ))
            if code != 0:
                return code
            continue
        if action == "dispatch_worker":
            code = dispatch_worker(argparse.Namespace(
                root=args.root,
                id=work_unit_id,
                platform=args.platform,
                builder_id=args.builder_id,
                executable=args.worker_executable or args.executable,
                timeout=args.worker_timeout,
                resume=False,
                dry_run=False,
            ))
            if code != 0:
                return code
            continue
        if action == "finalize":
            return finalize_check(argparse.Namespace(root=args.root, id=work_unit_id, strict=args.strict))
    print(json.dumps({"work_unit_id": work_unit_id, "stopped_at": "max_steps", "events": events}, ensure_ascii=False, indent=2))
    return 2

def route_decision(root: Path, wu_path: Path, platform: str = "") -> Dict[str, Any]:
    state = load_json(state_path(wu_path), {})
    status_value = str(state.get("status", ""))
    native_codex = platform == "codex"
    if status_value == "clarifying":
        return {"action": "human_clarification", "automatic": False, "reason": "Intent is not approved."}
    if status_value in {"spec_approved", "planning", "plan_reviewing"}:
        decision, reasons, _ = check_plan(root, wu_path)
        if decision == "BLOCK":
            return {"action": "complete_plan", "automatic": False, "reasons": reasons}
        if native_codex:
            return {
                "action": "native_plan_review",
                "automatic": False,
                "platform": "codex",
                "reason": "Plan is ready; launch or resume the native reviewer subagent, bind its session, and submit plan review through the controller.",
            }
        return {"action": "dispatch_plan_review", "automatic": True, "reasons": reasons}
    if status_value == "ready":
        if native_codex:
            return {
                "action": "native_worker",
                "automatic": False,
                "platform": "codex",
                "reason": "Plan review passed; launch or resume the native worker subagent, bind its session, and start work through the controller.",
            }
        return {"action": "dispatch_worker", "automatic": True, "reason": "Plan review passed; start an isolated platform worker."}
    if status_value in {"running", "verifying"}:
        decision, reasons, _ = check_verification(root, wu_path)
        if decision == "BLOCK":
            return {"action": "continue_tdd_and_evidence", "automatic": False, "reasons": reasons}
        if native_codex:
            return {
                "action": "native_close_review",
                "automatic": False,
                "platform": "codex",
                "reason": "Final evidence is fresh; resume the same native reviewer subagent and submit close review through the controller.",
            }
        return {"action": "dispatch_close_review", "automatic": True, "reasons": reasons}
    if status_value == "reviewing":
        decision, reasons, _ = check_review(root, wu_path)
        return {"action": "finalize" if decision != "BLOCK" else "continue_review_or_rework", "automatic": decision != "BLOCK", "reasons": reasons}
    if status_value in {"handoff", "blocked"}:
        return {"action": "resume_session_or_worker", "automatic": False, "reason": state.get("next_safe_action", "")}
    return {"action": "none", "automatic": False, "reason": f"No route for status {status_value}."}


def route(args: argparse.Namespace) -> int:
    work_unit_id, wu_path = resolve_wu(args.root, args.id)
    decision = route_decision(args.root, wu_path, args.platform)
    if args.execute and decision.get("action") in {"dispatch_plan_review", "dispatch_close_review"}:
        dispatch_args = argparse.Namespace(
            root=args.root,
            id=work_unit_id,
            mode="plan" if decision["action"] == "dispatch_plan_review" else "close",
            platform=args.platform,
            reviewer_id=args.reviewer_id,
            planner_id=args.planner_id,
            planner_session=args.planner_session,
            executable=args.executable,
            timeout=args.timeout,
            dry_run=False,
        )
        return dispatch_review(dispatch_args)
    print(json.dumps({"work_unit_id": work_unit_id, **decision}, ensure_ascii=False, indent=2))
    return 2 if args.strict and not decision.get("automatic") else 0


# ---------------------------------------------------------------------------
# Recovery, Goal, Git, GitHub, and worktrees
# ---------------------------------------------------------------------------

def checkpoint(args: argparse.Namespace) -> int:
    work_unit_id, wu_path = resolve_wu(args.root, args.id)
    state = update_state(args.root, wu_path, checkpoint_reason=args.reason)
    value = load_json(checkpoint_core.checkpoint_path(wu_path), {})
    print(json.dumps({"work_unit_id": work_unit_id, "checkpoint": value, "path": checkpoint_core.checkpoint_path(wu_path).relative_to(args.root).as_posix()}, ensure_ascii=False, indent=2))
    return 0


def bind_session(args: argparse.Namespace) -> int:
    work_unit_id, wu_path = resolve_wu(args.root, args.id)
    event = {"platform": args.platform, "session_id": args.session_id, "agent_id": args.agent_id, "agent_type": args.agent_type}
    try:
        binding = session_core.record(args.root, event, work_unit_id=work_unit_id, role=args.role, observed_at=now_iso())
    except ValueError as exc:
        raise HarnessError(str(exc)) from exc
    patch: Dict[str, Any] = {"current_role": args.role}
    if args.role == "worker":
        patch["builder_session_id"] = binding["logical_session_id"]
    elif args.role == "reviewer":
        track = load_json(review_track_path(wu_path), {})
        if track and track.get("logical_reviewer_session_id") not in {"", binding["logical_session_id"]}:
            raise HarnessError("Observed reviewer session conflicts with the active review track.")
    update_state(args.root, wu_path, checkpoint_reason="platform_session_bound", **patch)
    print(json.dumps(binding, ensure_ascii=False, indent=2))
    return 0


def handoff(args: argparse.Namespace) -> int:
    work_unit_id, wu_path = resolve_wu(args.root, args.id)
    state = update_state(args.root, wu_path, checkpoint_reason="handoff_generated", status="handoff", current_role="conductor", next_safe_action=args.next_safe_action)
    cp = load_json(checkpoint_core.checkpoint_path(wu_path), {})
    details, _blocking, _warnings = verification_detail_report(args.root, wu_path)
    track = load_json(review_track_path(wu_path), {})
    text = (
        f"# Handoff: {work_unit_id}\n\n"
        "> Derived from controller-owned state. Re-read the tracked contract, current Git/code, and referenced evidence; do not trust this note over them.\n\n"
        f"## Recovery checkpoint\n\n```json\n{json.dumps(cp, ensure_ascii=False, indent=2)}\n```\n\n"
        f"## Evidence status\n\n```json\n{json.dumps(details, ensure_ascii=False, indent=2)}\n```\n\n"
        f"## Reviewer continuity\n\n```json\n{json.dumps(track, ensure_ascii=False, indent=2)}\n```\n\n"
        f"## Next safe action\n\n{args.next_safe_action}\n"
    )
    atomic_write_text(wu_path / "handoff.md", text)
    print(json.dumps({"work_unit_id": work_unit_id, "status": state["status"], "handoff": (wu_path / "handoff.md").relative_to(args.root).as_posix(), "checkpoint": checkpoint_core.checkpoint_path(wu_path).relative_to(args.root).as_posix()}, ensure_ascii=False, indent=2))
    return 0


def goal_export(args: argparse.Namespace) -> int:
    work_unit_id, wu_path = resolve_wu(args.root, args.id)
    state = load_json(state_path(wu_path), {})
    binding = session_core.latest(args.root, work_unit_id, "worker") or session_core.latest(args.root, work_unit_id, "conductor")
    packet = _goal_packet(args.root, wu_path, args.thread_ref or str(binding.get("session_id", "")))
    output = wu_path / "platform" / "codex-goal.json"
    write_json(output, packet)
    # Deliberately no lifecycle transition: Goal completion is execution state,
    # never archive/completion authority.
    print(json.dumps({**packet, "output": output.relative_to(args.root).as_posix(), "lifecycle_state_unchanged": state.get("status")}, ensure_ascii=False, indent=2))
    return 0


def delivery_link(args: argparse.Namespace) -> int:
    work_unit_id, wu_path = resolve_wu(args.root, args.id)
    path = spec_path(wu_path)
    old_hash = spec_content_hash(path)
    try:
        contract = contract_core.update_delivery(
            path,
            issue=args.issue,
            branch=args.branch if args.branch is not None else current_branch(args.root),
            pull_request=args.pull_request,
            required_checks=args.required_check,
        )
    except contract_core.ContractError as exc:
        raise HarnessError(str(exc)) from exc
    if old_hash != spec_content_hash(path):
        raise HarnessError("Delivery metadata changed product-intent hash; refusing update.")
    update_state(args.root, wu_path, checkpoint_reason="delivery_linked", delivery=contract.get("delivery", {}))
    print(json.dumps({"work_unit_id": work_unit_id, "delivery": contract.get("delivery", {}), "intent_hash_unchanged": True}, ensure_ascii=False, indent=2))
    return 0


def github_sync(args: argparse.Namespace) -> int:
    work_unit_id, wu_path = resolve_wu(args.root, args.id)
    if shutil.which("gh") is None:
        raise HarnessError("GitHub sync requires the gh CLI; local state was not changed.")
    contract = contract_core.load_contract(spec_path(wu_path))
    delivery = contract.get("delivery", {}) if isinstance(contract.get("delivery"), dict) else {}
    pr_ref = args.pull_request or str(delivery.get("pull_request", ""))
    command = ["gh", "pr", "view", *( [pr_ref] if pr_ref else [] ), "--json", "number,url,state,headRefName,headRefOid,baseRefName,mergeable,statusCheckRollup"]
    proc = subprocess.run(command, cwd=args.root, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=30)
    if proc.returncode != 0:
        raise HarnessError("GitHub PR sync failed: " + proc.stderr.strip())
    try:
        snapshot = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise HarnessError("GitHub CLI returned invalid JSON.") from exc
    # `gh pr view` without an explicit PR may discover the current branch's PR.
    # Persist that stable reference through the contract helper so future
    # delivery checks cannot silently become optional again.
    discovered_pr = str(snapshot.get("number", "")).strip()
    discovered_branch = str(snapshot.get("headRefName", "")).strip()
    if discovered_pr and (not str(delivery.get("pull_request", "")).strip() or args.pull_request):
        old_hash = spec_content_hash(spec_path(wu_path))
        contract = contract_core.update_delivery(
            spec_path(wu_path),
            pull_request=discovered_pr,
            branch=discovered_branch or None,
        )
        if old_hash != spec_content_hash(spec_path(wu_path)):
            raise HarnessError("GitHub reference update changed product-intent hash; refusing sync.")
        delivery = contract.get("delivery", {}) if isinstance(contract.get("delivery"), dict) else {}

    repo_snapshot = RepoSnapshot.capture(args.root)
    normalized_checks = _normalize_github_checks(snapshot.get("statusCheckRollup", []))
    snapshot.update(
        {
            "schema_version": GITHUB_SCHEMA,
            "work_unit_id": work_unit_id,
            "synced_at": now_iso(),
            "local_head_at_sync": repo_snapshot.head_commit,
            "required_checks": list(delivery.get("required_checks", [])) if isinstance(delivery.get("required_checks", []), list) else [],
            "normalized_checks": normalized_checks,
        }
    )
    output = github_snapshot_path(wu_path)
    write_json(output, snapshot)
    decision, blocking, warnings = check_delivery(args.root, wu_path)
    print(json.dumps({"snapshot": snapshot, "decision": decision, "blocking_reasons": blocking, "warnings": warnings, "output": output.relative_to(args.root).as_posix()}, ensure_ascii=False, indent=2))
    return 0


def workspace_check(args: argparse.Namespace) -> int:
    work_unit_id, wu_path = resolve_wu(args.root, args.id)
    state = load_json(state_path(wu_path), {})
    snapshot = RepoSnapshot.capture(args.root, str(state.get("base_commit", "")))
    checks = {
        "repository_identity": state.get("bound_repository_identity") == snapshot.repository_id,
        "workspace_id": state.get("bound_workspace_id") == snapshot.workspace_id,
        "worktree": state.get("bound_worktree") == snapshot.worktree,
        "branch": state.get("bound_branch") == snapshot.branch,
    }
    result = {"work_unit_id": work_unit_id, "decision": "PASS" if all(checks.values()) else "BLOCK", "checks": checks}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(checks.values()) else 2


def workspace_create(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id = validate_work_unit_id(args.id)
    if not is_git_repo(root):
        raise HarnessError("workspace-create requires a Git repository.")
    target = Path(args.path).expanduser().resolve()
    if target.exists():
        raise HarnessError(f"Target worktree path already exists: {target}")
    branch = args.branch or f"agent/{work_unit_id.lower()}"
    start = args.start_point or "HEAD"
    proc = subprocess.run(["git", "worktree", "add", "-b", branch, str(target), start], cwd=root, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=60)
    if proc.returncode != 0:
        raise HarnessError("git worktree add failed: " + proc.stderr.strip())
    print(json.dumps({"work_unit_id": work_unit_id, "worktree": str(target), "branch": branch, "start_point": start, "next": f"Run harnessctl reconstruct --id {work_unit_id} in the worktree after the tracked spec is present."}, ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------------------
# Generic checks, validation, skills, CI, archive
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> Dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    result: Dict[str, str] = {}
    for raw in parts[1].splitlines():
        if ":" in raw:
            key, value = raw.split(":", 1)
            result[key.strip()] = clean_scalar(value)
    return result


def check_skills(root: Path) -> Tuple[str, List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    canonical = root / "skills"
    mirrors = [root / ".agents" / "skills", root / ".claude" / "skills"]
    if not canonical.exists():
        canonical = next((path for path in mirrors if path.exists()), canonical)
    skills = sorted(path for path in canonical.glob("harness-*") if (path / "SKILL.md").exists())
    if not skills:
        return "BLOCK", ["No harness skills found."], []
    names = [path.name for path in skills]
    for mirror in mirrors:
        if mirror.exists():
            mirror_names = sorted(path.name for path in mirror.glob("harness-*") if (path / "SKILL.md").exists())
            if mirror_names != names:
                blocking.append(f"Skill mirror mismatch for {mirror.relative_to(root)}.")
    required = {
        "harness-clarify": ["one high-value question", "do not implement"],
        "harness-spec": ["docs/spec", "approve-spec"],
        "harness-plan": ["plan.md", "plan review"],
        "harness-evidence": ["harnessctl verify", "controller"],
        "harness-review": ["same", "session"],
        "harness-tdd": ["RED", "GREEN", "expected"],
    }
    for name, needles in required.items():
        path = canonical / name / "SKILL.md"
        if not path.exists():
            blocking.append(f"Missing required skill {name}.")
            continue
        text = path.read_text(encoding="utf-8")
        lower = text.lower()
        for needle in needles:
            if needle.lower() not in lower:
                blocking.append(f"Skill {name} is missing required concept {needle!r}.")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


CHECKS: Dict[str, Any] = {
    "spec": check_spec,
    "plan": check_plan,
    "plan-review": check_plan_review,
    "scope": check_scope,
    "verification": check_verification,
    "review": check_review,
    "delivery": check_delivery,
    "archive": check_archive,
    "skills": lambda root, _wu: check_skills(root),
}


def check(args: argparse.Namespace) -> int:
    if args.gate == "skills":
        decision, blocking, warnings = check_skills(args.root)
        work_unit_id = None
    else:
        work_unit_id, wu_path = resolve_wu(args.root, args.id)
        decision, blocking, warnings = CHECKS[args.gate](args.root, wu_path)
    print(json.dumps({"work_unit_id": work_unit_id, "check": args.gate, "decision": decision, "blocking_reasons": blocking, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 2 if decision == "BLOCK" and args.strict else 0


def finalize_check(args: argparse.Namespace) -> int:
    work_unit_id, wu_path = resolve_wu(args.root, args.id)
    blocking: List[str] = []
    warnings: List[str] = []
    for label in ("spec", "scope", "verification", "review", "delivery"):
        _decision, reasons, warns = CHECKS[label](args.root, wu_path)
        blocking.extend(f"{label}: {reason}" for reason in reasons)
        warnings.extend(f"{label}: {warning}" for warning in warns)
    decision = "BLOCK" if blocking else "WARN" if warnings else "PASS"
    print(json.dumps({"work_unit_id": work_unit_id, "decision": decision, "blocking_reasons": blocking, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 2 if decision == "BLOCK" and args.strict else 0


def validate_work_unit(root: Path, work_unit_id: str, wu_path: Path) -> Tuple[List[str], List[str]]:
    state = load_json(state_path(wu_path), {})
    blocking: List[str] = []
    warnings: List[str] = []
    if state.get("schema_version") != STATE_SCHEMA:
        blocking.append(f"state schema must be {STATE_SCHEMA}.")
    if state.get("work_unit_id") != work_unit_id:
        blocking.append("state work_unit_id mismatch.")
    if state.get("status") not in VALID_STATUSES:
        blocking.append(f"Invalid status {state.get('status')!r}.")
    spec_blocking, spec_warnings = check_spec_document(spec_path(wu_path), work_unit_id)
    blocking.extend(spec_blocking)
    warnings.extend(spec_warnings)
    for row in evidence_receipts(wu_path):
        if row.get("schema_version") != EVIDENCE_SCHEMA:
            blocking.append(f"Receipt {row.get('receipt_id')} uses unsupported schema.")
        if row.get("result") == "pass" and row.get("observation") != "controller_executed_check":
            blocking.append(f"Receipt {row.get('receipt_id')} claims pass without controller execution.")
    request_ids = {str(row.get("request_id", "")) for row in review_requests(wu_path)}
    for verdict in review_verdicts(wu_path):
        if verdict.get("schema_version") != REVIEW_VERDICT_SCHEMA:
            blocking.append(f"Review {verdict.get('review_id')} uses unsupported schema.")
        if str(verdict.get("request_id", "")) not in request_ids:
            blocking.append(f"Review {verdict.get('review_id')} references missing request.")
        blocking.extend(review_independence_errors(verdict))
    cp = load_json(checkpoint_core.checkpoint_path(wu_path), {})
    if cp.get("work_unit_id") != work_unit_id:
        blocking.append("Recovery checkpoint is missing or belongs to another Work Unit.")
    return blocking, warnings


def validate(args: argparse.Namespace) -> int:
    units: List[Tuple[str, Path]] = []
    if args.all:
        for base in (active_dir(args.root), archive_dir(args.root)):
            if base.exists():
                units.extend((path.name, path) for path in sorted(base.iterdir()) if path.is_dir())
    else:
        units.append(resolve_wu(args.root, args.id))
    blocking: List[str] = []
    warnings: List[str] = []
    for work_unit_id, wu_path in units:
        b, w = validate_work_unit(args.root, work_unit_id, wu_path)
        blocking.extend(f"{work_unit_id}: {value}" for value in b)
        warnings.extend(f"{work_unit_id}: {value}" for value in w)
    decision = "BLOCK" if blocking else "WARN" if warnings else "PASS"
    print(json.dumps({"decision": decision, "checked_work_units": [value[0] for value in units], "blocking_reasons": blocking, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 2 if decision == "BLOCK" and args.strict else 0


def ci(args: argparse.Namespace) -> int:
    blocking: List[str] = []
    warnings: List[str] = []
    skill_decision, skill_blocking, skill_warnings = check_skills(args.root)
    if skill_decision == "BLOCK":
        blocking.extend(skill_blocking)
    warnings.extend(skill_warnings)
    for path in sorted((args.root / "docs" / "spec").glob("*.md")) if (args.root / "docs" / "spec").exists() else []:
        if path.name == "README.md":
            continue
        b, w = check_spec_document(path, path.stem)
        blocking.extend(f"{path.relative_to(args.root)}: {value}" for value in b)
        warnings.extend(f"{path.relative_to(args.root)}: {value}" for value in w)
    if active_dir(args.root).exists():
        for wu_path in sorted(path for path in active_dir(args.root).iterdir() if path.is_dir()):
            b, w = validate_work_unit(args.root, wu_path.name, wu_path)
            blocking.extend(f"{wu_path.name}: {value}" for value in b)
            warnings.extend(f"{wu_path.name}: {value}" for value in w)
    decision = "BLOCK" if blocking else "WARN" if warnings else "PASS"
    print(json.dumps({"decision": decision, "blocking_reasons": blocking, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 2 if decision == "BLOCK" and args.strict else 0


def archive(args: argparse.Namespace) -> int:
    work_unit_id, wu_path = resolve_wu(args.root, args.id)
    if wu_path.parent == archive_dir(args.root):
        raise HarnessError("Work Unit is already archived.")
    if args.no_next_step_reason:
        update_state(args.root, wu_path, checkpoint_reason="archive_reason_recorded", no_next_step_reason=args.no_next_step_reason)
    decision, reasons, warnings = check_archive(args.root, wu_path)
    if decision == "BLOCK" and not args.force:
        raise HarnessError("Archive gate blocks: " + "; ".join(reasons))
    override_ref = ""
    if args.force:
        if not args.reason or not args.approved_by or not args.approval_ref:
            raise HarnessError("Forced archive requires --reason, --approved-by human:<identity>, and --approval-ref.")
        if not str(args.approved_by).startswith("human:"):
            raise HarnessError("Forced archive approval must use human:<identity>.")
        override = {
            "schema_version": "harness.archive_override.v1",
            "work_unit_id": work_unit_id,
            "decision_overridden": decision,
            "blocking_reasons": reasons,
            "warnings": warnings,
            "reason": args.reason,
            "approved_by": args.approved_by,
            "approval_ref": args.approval_ref,
            "created_at": now_iso(),
        }
        override_path = reviews_dir(wu_path) / "archive-override.json"
        write_json(override_path, override)
        override_ref = override_path.relative_to(args.root).as_posix()
    update_state(args.root, wu_path, checkpoint_reason="archived", status="archived", next_safe_action="No local next step; reopen or create a follow-up Work Unit.")
    destination = archive_dir(args.root) / work_unit_id
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise HarnessError(f"Archive destination exists: {destination}")
    shutil.move(str(wu_path), str(destination))
    pointer = current_file(args.root)
    if pointer.exists() and pointer.read_text(encoding="utf-8").strip() == work_unit_id:
        pointer.unlink()
    print(json.dumps({"work_unit_id": work_unit_id, "status": "archived", "warnings": warnings, "forced": bool(args.force), "override_ref": override_ref}, ensure_ascii=False, indent=2))
    return 0


def doctor(args: argparse.Namespace) -> int:
    root = args.root
    checks = {
        "controller_cli": (root / "harness" / "cli" / "harnessctl.py").exists(),
        "tracked_specs_directory": (root / "docs" / "spec").exists(),
        "runtime_ignored": ".harness/" in (root / ".gitignore").read_text(encoding="utf-8") if (root / ".gitignore").exists() else False,
        "runtime_not_tracked": ".harness/config.json" not in run_git(root, ["ls-files"], "").splitlines(),
        "contract_template": contract_core.START in (root / "harness" / "templates" / "feature-spec.md").read_text(encoding="utf-8") if (root / "harness" / "templates" / "feature-spec.md").exists() else False,
        "plan_template": plan_core.START in (root / "harness" / "templates" / "technical-plan.md").read_text(encoding="utf-8") if (root / "harness" / "templates" / "technical-plan.md").exists() else False,
        "skills": check_skills(root)[0] != "BLOCK",
        "git_repository": is_git_repo(root),
    }
    for name, ok in checks.items():
        print(f"{'PASS' if ok else 'WARN'}\t{name}")
    return 0


def hook_dispatch(args: argparse.Namespace) -> int:
    root = args.root
    if args.name == "pre-compact":
        from harness.hooks import pre_compact_handoff_check as hook_module
        return int(hook_module.main())
    if args.name == "post-compact":
        from harness.hooks import context_router as hook_module
        original_argv = sys.argv[:]
        try:
            sys.argv = ["context_router.py", "PostCompact"]
            return int(hook_module.main())
        finally:
            sys.argv = original_argv
    if args.name == "stop":
        from harness.hooks import session_end_handoff_check as hook_module
        return int(hook_module.main())
    raise HarnessError(f"Unsupported hook name: {args.name}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Controller CLI for a coding-agent repository harness")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("--profile", choices=["codex", "claude"], default="codex")
    p.set_defaults(func=init)

    p = sub.add_parser("new")
    p.add_argument("--id", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--type", default="other", choices=["feature", "bugfix", "refactor", "migration", "docs", "test", "release", "security", "research", "other"])
    p.add_argument("--risk", default="low", choices=list(RISK_ORDER))
    p.set_defaults(func=new)

    for name, func, help_text in (
        ("resume-session", resume_session, "Continue from existing local controller state; never reconstruct"),
        ("reconstruct", reconstruct, "Rebuild minimal safe state from tracked spec and Git"),
        ("resume", resume, "Deprecated safe alias for resume-session"),
        ("migrate-spec", migrate_spec, "Migrate one legacy spec to canonical JSON contract"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--id", required=True)
        p.set_defaults(func=func)

    p = sub.add_parser("list")
    p.set_defaults(func=list_wu)
    p = sub.add_parser("status")
    p.add_argument("--id")
    p.set_defaults(func=status)
    p = sub.add_parser("brief")
    p.add_argument("--id")
    p.set_defaults(func=brief)

    p = sub.add_parser("approve-spec")
    p.add_argument("--id")
    p.add_argument("--approved-by", required=True)
    p.add_argument("--approval-ref", required=True)
    p.set_defaults(func=approve_spec)

    p = sub.add_parser("amend")
    p.add_argument("--id")
    p.add_argument("--reason", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--actor", required=True)
    p.add_argument("--approval-ref", required=True)
    p.set_defaults(func=amend)

    p = sub.add_parser("start-work")
    p.add_argument("--id")
    p.add_argument("--builder-id", default="")
    p.add_argument("--builder-session", default="")
    p.set_defaults(func=start_work)
    p = sub.add_parser("resume-work")
    p.add_argument("--id")
    p.add_argument("--builder-id", default="")
    p.add_argument("--builder-session", default="")
    p.set_defaults(func=resume_work)

    p = sub.add_parser("verify")
    p.add_argument("--id")
    p.add_argument("--claim", required=True)
    p.add_argument("--behavior")
    p.add_argument("--type", default="test")
    p.add_argument("--phase", choices=["red", "green", "final"], default="final")
    p.add_argument("--expect", choices=["pass", "fail"], default=None, help="Optional assertion; phase policy remains authoritative")
    p.add_argument("--timeout", type=int, default=None)
    p.add_argument("--verification-scope", default="behavior")
    p.add_argument("--environment-ref")
    p.add_argument("--note")
    p.add_argument("command", nargs=argparse.REMAINDER, help="Optional exact argv assertion after --; no shell parsing")
    p.set_defaults(func=verify)

    p = sub.add_parser("record-skipped")
    p.add_argument("--id")
    p.add_argument("--claim", required=True)
    p.add_argument("--type", default="test")
    p.add_argument("--reason", required=True)
    p.add_argument("--replacement", required=True)
    p.add_argument("--risk-impact", required=True)
    p.add_argument("--owner", required=True)
    p.add_argument("--actor", default="agent")
    p.add_argument("--verification-scope", default="behavior")
    p.add_argument("--environment-ref")
    p.set_defaults(func=record_skipped)

    p = sub.add_parser("request-review")
    p.add_argument("--id")
    p.add_argument("--mode", choices=REVIEW_MODES, required=True)
    p.add_argument("--reviewer-id", default="")
    p.add_argument("--reviewer-session", default="")
    p.add_argument("--planner-id", default="")
    p.add_argument("--planner-session", default="")
    p.set_defaults(func=request_review)

    p = sub.add_parser("submit-review")
    p.add_argument("--id")
    p.add_argument("--request-id")
    p.add_argument("--mode", choices=REVIEW_MODES, required=True)
    p.add_argument("--decision", choices=["PASS", "CHANGES_REQUESTED", "REJECTED", "BLOCKED", "NEEDS_HUMAN_GATE"], required=True)
    p.add_argument("--reviewer-id", default="")
    p.add_argument("--reviewer-session", default="")
    p.add_argument("--independence-level", choices=["self_check", "separate_role", "fresh_context", "human_gate"], default="separate_role")
    p.add_argument("--approval-ref", default="")
    p.add_argument("--evidence-ref", action="append")
    p.add_argument("--finding", action="append")
    p.add_argument("--required-rework", action="append")
    p.set_defaults(func=submit_review)

    p = sub.add_parser("reviewer-takeover")
    p.add_argument("--id")
    p.add_argument("--new-reviewer-id", required=True)
    p.add_argument("--new-reviewer-session", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--approved-by", required=True)
    p.add_argument("--approval-ref", required=True)
    p.set_defaults(func=reviewer_takeover)

    p = sub.add_parser("dispatch-review")
    p.add_argument("--id")
    p.add_argument("--mode", choices=REVIEW_MODES, required=True)
    p.add_argument("--platform", choices=["codex", "claude"], required=True)
    p.add_argument("--reviewer-id", default="")
    p.add_argument("--planner-id", default="")
    p.add_argument("--planner-session", default="")
    p.add_argument("--executable", default="")
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=dispatch_review)

    p = sub.add_parser("dispatch-worker")
    p.add_argument("--id")
    p.add_argument("--platform", choices=["codex", "claude"], required=True)
    p.add_argument("--builder-id", default="")
    p.add_argument("--executable", default="")
    p.add_argument("--timeout", type=int, default=7200)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=dispatch_worker)

    p = sub.add_parser("advance")
    p.add_argument("--id")
    p.add_argument("--platform", choices=["codex", "claude"], default="codex")
    p.add_argument("--reviewer-id", default="")
    p.add_argument("--planner-id", default="")
    p.add_argument("--planner-session", default="")
    p.add_argument("--builder-id", default="")
    p.add_argument("--executable", default="", help="Default executable override for both roles")
    p.add_argument("--reviewer-executable", default="")
    p.add_argument("--worker-executable", default="")
    p.add_argument("--review-timeout", type=int, default=3600)
    p.add_argument("--worker-timeout", type=int, default=7200)
    p.add_argument("--max-steps", type=int, default=4)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.set_defaults(func=advance)

    p = sub.add_parser("adapter-doctor")
    p.add_argument("--platform", choices=["codex", "claude"])
    p.add_argument("--executable", default="")
    p.add_argument("--strict", action="store_true")
    p.set_defaults(func=adapter_doctor)

    p = sub.add_parser("route")
    p.add_argument("--id")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--platform", choices=["codex", "claude"], default="codex")
    p.add_argument("--reviewer-id", default="")
    p.add_argument("--planner-id", default="")
    p.add_argument("--planner-session", default="")
    p.add_argument("--executable", default="")
    p.add_argument("--timeout", type=int, default=3600)
    p.add_argument("--strict", action="store_true")
    p.set_defaults(func=route)

    p = sub.add_parser("checkpoint")
    p.add_argument("--id")
    p.add_argument("--reason", default="manual_checkpoint")
    p.set_defaults(func=checkpoint)

    p = sub.add_parser("bind-session")
    p.add_argument("--id")
    p.add_argument("--role", choices=["conductor", "planner", "reviewer", "worker"], required=True)
    p.add_argument("--platform", choices=["codex", "claude"], required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--agent-id", default="")
    p.add_argument("--agent-type", default="")
    p.set_defaults(func=bind_session)

    p = sub.add_parser("handoff")
    p.add_argument("--id")
    p.add_argument("--next-safe-action", required=True)
    p.set_defaults(func=handoff)

    p = sub.add_parser("goal-export")
    p.add_argument("--id")
    p.add_argument("--thread-ref", default="")
    p.set_defaults(func=goal_export)

    p = sub.add_parser("delivery-link")
    p.add_argument("--id")
    p.add_argument("--issue", default=None)
    p.add_argument("--branch", default=None)
    p.add_argument("--pull-request", default=None)
    p.add_argument("--required-check", action="append", default=None, help="GitHub status/check name required for delivery; repeatable")
    p.set_defaults(func=delivery_link)

    p = sub.add_parser("github-sync")
    p.add_argument("--id")
    p.add_argument("--pull-request", default="")
    p.set_defaults(func=github_sync)

    p = sub.add_parser("workspace-check")
    p.add_argument("--id")
    p.set_defaults(func=workspace_check)

    p = sub.add_parser("workspace-create")
    p.add_argument("--id", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--branch", default="")
    p.add_argument("--start-point", default="HEAD")
    p.set_defaults(func=workspace_create)

    p = sub.add_parser("check")
    p.add_argument("--id")
    p.add_argument("--gate", choices=sorted(CHECKS), required=True)
    p.add_argument("--strict", action="store_true")
    p.set_defaults(func=check)

    p = sub.add_parser("validate")
    p.add_argument("--id")
    p.add_argument("--all", action="store_true")
    p.add_argument("--strict", action="store_true")
    p.set_defaults(func=validate)

    p = sub.add_parser("finalize-check")
    p.add_argument("--id")
    p.add_argument("--strict", action="store_true")
    p.set_defaults(func=finalize_check)

    p = sub.add_parser("ci")
    p.add_argument("--strict", action="store_true")
    p.set_defaults(func=ci)

    p = sub.add_parser("archive")
    p.add_argument("--id")
    p.add_argument("--force", action="store_true")
    p.add_argument("--reason", default="")
    p.add_argument("--approved-by", default="")
    p.add_argument("--approval-ref", default="")
    p.add_argument("--no-next-step-reason")
    p.set_defaults(func=archive)

    p = sub.add_parser("doctor")
    p.set_defaults(func=doctor)

    p = sub.add_parser("hook")
    p.add_argument("name", choices=["pre-compact", "post-compact", "stop"])
    p.set_defaults(func=hook_dispatch)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.root = find_root(args.root)
    try:
        return int(args.func(args))
    except (HarnessError, StorageError, contract_core.ContractError, plan_core.PlanError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
