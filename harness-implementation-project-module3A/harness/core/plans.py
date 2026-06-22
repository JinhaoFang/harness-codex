"""Canonical local technical plan and TDD behavior-slice contract."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

SCHEMA_VERSION = "harness.execution_plan.v2"
START = "<!-- harness:execution-plan:start -->"
END = "<!-- harness:execution-plan:end -->"
_BLOCK_RE = re.compile(rf"{re.escape(START)}\s*```json\s*(.*?)\s*```\s*{re.escape(END)}", re.DOTALL | re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"\bTBD\b|\{\{[^}]+\}\}|TODO:", re.IGNORECASE)


class PlanError(RuntimeError):
    pass


def default_plan(work_unit_id: str, title: str) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "work_unit_id": work_unit_id,
        "title": title,
        "repository_grounding": ["TBD: Code, tests, runtime behavior, and local rules inspected."],
        "architecture_and_tradeoffs": "TBD: Chosen design, rejected alternatives, and why this is the smallest appropriate change.",
        "change_map": [{"path": "TBD", "change": "TBD", "reason": "TBD"}],
        "behavior_slices": [
            {
                "id": "B1",
                "claim_ref": "EV1",
                "behavior": "TBD",
                "test_paths": ["TBD"],
                "oracle": "TBD: Explain why this assertion fails on old behavior and passes only on the required behavior.",
                "red": {
                    "check_id": "check.ev1",
                    "expected_failure": {"kind": "exit_nonzero", "combined_regex": ["TBD"]},
                },
                "green": {"check_id": "check.ev1"},
                "allowed_paths": ["TBD"],
            }
        ],
        "acceptance_evidence": [
            {
                "claim_ref": "EV1",
                "check_id": "check.ev1",
                "level": "functional",
                "justification": "TBD: Explain why this check level is needed to prove the final user-visible outcome."
            }
        ],
        "verification_notes": ["TBD"],
        "risks_and_replan_conditions": ["TBD"],
        "reviewer_focus": ["TBD"],
    }


def render_block(plan: Mapping[str, Any]) -> str:
    return f"{START}\n```json\n{json.dumps(dict(plan), ensure_ascii=False, indent=2)}\n```\n{END}"


def render_plan(plan: Mapping[str, Any]) -> str:
    return (
        f"# Technical Plan: {plan.get('work_unit_id', '')} — {plan.get('title', '')}\n\n"
        "> Local, ignored intermediate artifact. The marked JSON block is controller-readable; reviewer notes outside it are optional context.\n\n"
        f"{render_block(plan)}\n\n"
        "## Reviewer notes\n\nAdd code anchors, rejected alternatives, and implementation discoveries here.\n"
    )


def load_plan(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise PlanError(f"Missing local technical plan: {path}")
    text = path.read_text(encoding="utf-8")
    match = _BLOCK_RE.search(text)
    if not match:
        raise PlanError("Technical plan has no canonical execution-plan JSON block.")
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise PlanError(f"Invalid execution-plan JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise PlanError("Execution-plan JSON must be an object.")
    return value


def write_plan(path: Path, plan: Mapping[str, Any]) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else render_plan(plan)
    if START not in text:
        path.write_text(render_plan(plan), encoding="utf-8")
        return
    match = _BLOCK_RE.search(text)
    if not match:
        raise PlanError("Technical plan has malformed canonical block.")
    replacement = json.dumps(dict(plan), ensure_ascii=False, indent=2)
    path.write_text(text[: match.start(1)] + replacement + text[match.end(1) :], encoding="utf-8")


def behavior_slice(plan: Mapping[str, Any], behavior_id: str) -> Dict[str, Any]:
    rows = plan.get("behavior_slices", [])
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and str(row.get("id", "")) == behavior_id:
                return dict(row)
    raise PlanError(f"Behavior slice {behavior_id!r} is not declared by the plan.")


def behavior_for_claim(plan: Mapping[str, Any], claim_id: str) -> Optional[Dict[str, Any]]:
    rows = plan.get("behavior_slices", [])
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and str(row.get("claim_ref", "")) == claim_id:
                return dict(row)
    return None


def _has_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return not value.strip() or bool(PLACEHOLDER_RE.search(value))
    if isinstance(value, list):
        return not value or any(_has_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(_has_placeholder(item) for item in value.values())
    return value is None


def validate_plan(plan: Mapping[str, Any], expected_id: str, risk_rank: int = 1) -> Tuple[List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    if plan.get("schema_version") != SCHEMA_VERSION:
        blocking.append(f"Plan schema_version must be {SCHEMA_VERSION}.")
    if plan.get("work_unit_id") != expected_id:
        blocking.append("Plan work_unit_id does not match the active Work Unit.")
    if _has_placeholder(plan):
        blocking.append("Plan contains unresolved placeholder or empty required content.")
    if not isinstance(plan.get("repository_grounding"), list) or not plan.get("repository_grounding"):
        blocking.append("Plan must record repository_grounding.")
    if not isinstance(plan.get("change_map"), list) or not plan.get("change_map"):
        blocking.append("Plan must contain a change_map.")
    rows = plan.get("behavior_slices", [])
    if risk_rank >= 2 and (not isinstance(rows, list) or not rows):
        blocking.append("Medium+ plan must define at least one TDD behavior slice.")
    seen: set[str] = set()
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            blocking.append("Each behavior slice must be an object.")
            continue
        behavior_id = str(row.get("id", ""))
        if not behavior_id:
            blocking.append("Behavior slice is missing id.")
        elif behavior_id in seen:
            blocking.append(f"Duplicate behavior slice id: {behavior_id}")
        seen.add(behavior_id)
        for key in ("claim_ref", "behavior", "oracle"):
            if not str(row.get(key, "")).strip():
                blocking.append(f"Behavior {behavior_id or '<unknown>'} is missing {key}.")
        if not isinstance(row.get("test_paths"), list) or not row.get("test_paths"):
            blocking.append(f"Behavior {behavior_id or '<unknown>'} must declare test_paths.")
        red = row.get("red", {})
        green = row.get("green", {})
        if not isinstance(red, dict) or not str(red.get("check_id", "")).strip():
            blocking.append(f"Behavior {behavior_id or '<unknown>'} is missing red.check_id.")
        expected_failure = red.get("expected_failure", {}) if isinstance(red, dict) else {}
        if risk_rank >= 2 and (not isinstance(expected_failure, dict) or not any(expected_failure.get(key) for key in ("exit_codes", "stdout_contains", "stderr_contains", "combined_contains", "stdout_regex", "stderr_regex", "combined_regex"))):
            blocking.append(f"Medium+ behavior {behavior_id or '<unknown>'} must identify the expected RED failure reason.")
        if isinstance(expected_failure, dict):
            for key in ("stdout_regex", "stderr_regex", "combined_regex"):
                values = expected_failure.get(key, [])
                if values and not isinstance(values, list):
                    blocking.append(f"Behavior {behavior_id or '<unknown>'} {key} must be an array.")
                for pattern in values if isinstance(values, list) else []:
                    try:
                        re.compile(str(pattern))
                    except re.error as exc:
                        blocking.append(f"Behavior {behavior_id or '<unknown>'} has invalid {key}: {exc}")
        if not isinstance(green, dict) or not str(green.get("check_id", "")).strip():
            blocking.append(f"Behavior {behavior_id or '<unknown>'} is missing green.check_id.")
        if not isinstance(row.get("allowed_paths"), list) or not row.get("allowed_paths"):
            blocking.append(f"Behavior {behavior_id or '<unknown>'} must declare allowed_paths.")
    evidence_rows = plan.get("acceptance_evidence", [])
    if not isinstance(evidence_rows, list) or not evidence_rows:
        blocking.append("Plan must define acceptance_evidence for final claim validation.")
    else:
        for index, row in enumerate(evidence_rows, start=1):
            if not isinstance(row, dict):
                blocking.append(f"acceptance_evidence[{index}] must be an object.")
                continue
            if not str(row.get("claim_ref", "")).strip():
                blocking.append(f"acceptance_evidence[{index}] is missing claim_ref.")
            if not str(row.get("check_id", "")).strip():
                blocking.append(f"acceptance_evidence[{index}] is missing check_id.")
            level = str(row.get("level", "")).strip()
            if level not in {"unit", "integration", "functional", "e2e", "acceptance", "smoke", "build", "lint", "typecheck", "runtime"}:
                blocking.append(f"acceptance_evidence[{index}] has invalid level {level!r}.")
            if not str(row.get("justification", "")).strip():
                blocking.append(f"acceptance_evidence[{index}] is missing justification.")
        static_only = {
            str(row.get("level", "")).strip()
            for row in evidence_rows
            if isinstance(row, dict) and str(row.get("level", "")).strip()
        }
        if static_only and static_only.issubset({"build", "lint", "typecheck"}):
            warnings.append("Acceptance evidence relies only on static/build-style checks; reviewer should verify user-observable coverage.")
    for key in ("verification_notes", "risks_and_replan_conditions", "reviewer_focus"):
        if not isinstance(plan.get(key), list) or not plan.get(key):
            blocking.append(f"Plan must contain {key}.")
    return blocking, warnings
