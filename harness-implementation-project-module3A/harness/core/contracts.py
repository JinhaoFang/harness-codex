"""Canonical Work Unit contract embedded in the tracked Markdown spec.

The Markdown remains pleasant to review, while the controller reads one explicit
JSON block. Legacy Markdown/YAML specs can be migrated once; normal operation
never reparses prose as pseudo-YAML.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import shlex
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

SCHEMA_VERSION = "harness.work_unit_contract.v3"
START = "<!-- harness:work-unit-contract:start -->"
END = "<!-- harness:work-unit-contract:end -->"
_BLOCK_RE = re.compile(
    rf"{re.escape(START)}\s*```json\s*(.*?)\s*```\s*{re.escape(END)}",
    flags=re.DOTALL | re.IGNORECASE,
)
PLACEHOLDER_RE = re.compile(r"\bTBD\b|\{\{[^}]+\}\}|TODO:|\[在此处", flags=re.IGNORECASE)


class ContractError(RuntimeError):
    """Raised when a tracked contract cannot be parsed or validated safely."""


def unquote_pair(value: str) -> str:
    """Remove only a complete matching outer quote pair.

    This deliberately does *not* use ``str.strip('"')``. The latter corrupts a
    valid command such as ``npm test -- --test-name-pattern="name"`` by deleting
    only its final quote.
    """
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        return text[1:-1].strip()
    return text


def _match(text: str) -> re.Match[str]:
    match = _BLOCK_RE.search(text)
    if not match:
        raise ContractError("Tracked spec has no canonical harness contract JSON block.")
    return match


def parse_contract(text: str) -> Dict[str, Any]:
    match = _match(text)
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ContractError(f"Invalid harness contract JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError("Harness contract JSON must be an object.")
    return value


def load_contract(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise ContractError(f"Missing tracked spec: {path}")
    return parse_contract(path.read_text(encoding="utf-8"))


def render_block(contract: Mapping[str, Any]) -> str:
    return f"{START}\n```json\n{json.dumps(dict(contract), ensure_ascii=False, indent=2)}\n```\n{END}"


def render_spec(contract: Mapping[str, Any], product_notes: str = "") -> str:
    notes = product_notes.strip() or "Add walkthrough notes, examples, rejected alternatives, and rationale here. The contract block above remains authoritative."
    return (
        f"# Feature Spec: {contract.get('id', '')} — {contract.get('title', '')}\n\n"
        "> Tracked product specification. The marked JSON block is the machine-readable Work Unit contract.\n\n"
        f"{render_block(contract)}\n\n"
        "## Product notes\n\n"
        f"{notes}\n"
    )


def write_contract(path: Path, contract: Mapping[str, Any]) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else render_spec(contract)
    if START not in text:
        path.write_text(render_spec(contract), encoding="utf-8")
        return
    match = _match(text)
    replacement = json.dumps(dict(contract), ensure_ascii=False, indent=2)
    path.write_text(text[: match.start(1)] + replacement + text[match.end(1) :], encoding="utf-8")


def default_contract(work_unit_id: str, title: str, task_type: str, risk: str) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "id": work_unit_id,
        "title": title,
        "type": task_type,
        "risk": risk,
        "approval": {
            "status": "draft",
            "approved_by": "",
            "approved_at": "",
            "approval_ref": "",
            "approved_content_hash": "",
        },
        "intent": "TBD: Describe the user or product problem without assuming the implementation.",
        "expected_outcomes": ["TBD: State the externally observable result."],
        "non_goals": ["TBD: State what this Work Unit deliberately will not do."],
        "scope": {
            "likely_changed_areas": ["TBD"],
            "write_boundary": ["TBD"],
            "out_of_bounds": ["TBD"],
        },
        "required_evidence": [
            {"id": "EV1", "claim": "TBD: State what must be proven.", "check_id": "check.ev1"}
        ],
        "verification": {
            "checks": {
                "check.ev1": {
                    "runner": "exec",
                    "argv": ["TBD"],
                    "cwd": ".",
                    "timeout_seconds": 1800,
                }
            }
        },
        "stop_conditions": {
            "success": ["TBD"],
            "blocked": [
                "Material product intent remains ambiguous.",
                "Implementation must cross an out-of-bounds path.",
                "Required evidence cannot be produced without changing the approved spec.",
            ],
        },
        "clarification": {
            "user_confirmed": False,
            "repo_grounded": False,
            "key_decisions": [],
            "remaining_assumptions": ["TBD"],
        },
        "open_questions": ["TBD"],
        "context_pointers": ["TBD"],
        "delivery": {"issue": "", "branch": "", "pull_request": "", "required_checks": []},
        "risk_notes": ["TBD"],
    }


def _semantic_contract(contract: Mapping[str, Any]) -> Dict[str, Any]:
    value = copy.deepcopy(dict(contract))
    value.pop("approval", None)
    # Delivery references describe integration state, not product intent. Updating
    # an issue/PR link must not force product reapproval.
    value.pop("delivery", None)
    return value


def content_hash(path: Path) -> str:
    if not path.exists():
        return ""
    contract = load_contract(path)
    payload = json.dumps(_semantic_contract(contract), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def object_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def update_approval(path: Path, values: Mapping[str, str]) -> None:
    contract = load_contract(path)
    approval = contract.get("approval")
    if not isinstance(approval, dict):
        approval = {}
        contract["approval"] = approval
    for key in ("status", "approved_by", "approved_at", "approval_ref", "approved_content_hash"):
        if key in values:
            approval[key] = str(values[key])
    write_contract(path, contract)


def update_delivery(path: Path, **patch: Any) -> Dict[str, Any]:
    contract = load_contract(path)
    delivery = contract.get("delivery")
    if not isinstance(delivery, dict):
        delivery = {}
        contract["delivery"] = delivery
    for key in ("issue", "branch", "pull_request"):
        if key in patch and patch[key] is not None:
            delivery[key] = str(patch[key])
    if "required_checks" in patch and patch["required_checks"] is not None:
        raw = patch["required_checks"]
        if not isinstance(raw, (list, tuple)):
            raise ContractError("delivery.required_checks must be a list of GitHub check names.")
        delivery["required_checks"] = list(dict.fromkeys(str(value).strip() for value in raw if str(value).strip()))
    write_contract(path, contract)
    return contract


def evidence_items(contract: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = contract.get("required_evidence", [])
    return [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def evidence_by_id(contract: Mapping[str, Any], claim_id: str) -> Optional[Dict[str, Any]]:
    return next((row for row in evidence_items(contract) if str(row.get("id", "")) == claim_id), None)




def check_for_claim(contract: Mapping[str, Any], claim_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    claim = evidence_by_id(contract, claim_id)
    if claim is None:
        known = sorted(str(row.get("id", "")) for row in evidence_items(contract))
        raise ContractError(f"Unknown required evidence claim {claim_id!r}; expected one of {known}.")
    check_id = str(claim.get("check_id", ""))
    return claim, check_definition(contract, check_id)


def required_evidence(contract: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Compatibility alias for platform projections."""
    return evidence_items(contract)

def check_definitions(contract: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    verification = contract.get("verification", {})
    checks = verification.get("checks", {}) if isinstance(verification, dict) else {}
    if not isinstance(checks, dict):
        return {}
    return {str(key): dict(value) for key, value in checks.items() if isinstance(key, str) and isinstance(value, dict)}


def check_definition(contract: Mapping[str, Any], check_id: str) -> Dict[str, Any]:
    value = check_definitions(contract).get(check_id)
    if value is None:
        raise ContractError(f"Check {check_id!r} is not declared by the approved spec.")
    return value


def check_definition_hash(check_id: str, definition: Mapping[str, Any]) -> str:
    return object_hash({"check_id": check_id, "definition": dict(definition)})


def argv_for_check(definition: Mapping[str, Any]) -> List[str]:
    if str(definition.get("runner", "exec")) != "exec":
        raise ContractError("argv_for_check is only valid for exec checks.")
    argv = definition.get("argv", [])
    if not isinstance(argv, list) or not argv or any(not isinstance(arg, str) or not arg for arg in argv):
        raise ContractError("Structured exec check requires a non-empty string argv array.")
    return list(argv)


def scope_patterns(contract: Mapping[str, Any]) -> Tuple[List[str], List[str]]:
    scope = contract.get("scope", {})
    if not isinstance(scope, dict):
        return [], []
    return _strings(scope.get("write_boundary")), _strings(scope.get("out_of_bounds"))


def _strings(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _contains_placeholder(value: Any, *, path: Tuple[str, ...] = ()) -> bool:
    # Empty delivery and approval values are intentionally allowed while drafting.
    if path and path[0] in {"approval", "delivery"}:
        return False
    if isinstance(value, str):
        return bool(PLACEHOLDER_RE.search(value)) or not value.strip()
    if isinstance(value, list):
        return not value or any(_contains_placeholder(item, path=path) for item in value)
    if isinstance(value, dict):
        return any(_contains_placeholder(item, path=(*path, str(key))) for key, item in value.items())
    return value is None


def validate_check(check_id: str, definition: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    runner = str(definition.get("runner", "exec"))
    if runner not in {"exec", "shell"}:
        errors.append(f"Check {check_id} runner must be exec or shell.")
        return errors
    cwd = definition.get("cwd", ".")
    if not isinstance(cwd, str) or not cwd.strip():
        errors.append(f"Check {check_id} cwd must be a non-empty repository-relative path.")
    timeout = definition.get("timeout_seconds", 1800)
    if not isinstance(timeout, int) or not 1 <= timeout <= 7200:
        errors.append(f"Check {check_id} timeout_seconds must be an integer from 1 to 7200.")
    env = definition.get("env", {})
    if env and (not isinstance(env, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in env.items())):
        errors.append(f"Check {check_id} env must be a string-to-string object.")
    if runner == "exec":
        argv = definition.get("argv", [])
        if not isinstance(argv, list) or not argv or any(not isinstance(arg, str) or not arg for arg in argv):
            errors.append(f"Check {check_id} exec runner requires a non-empty string argv array.")
        if "script" in definition:
            errors.append(f"Check {check_id} exec runner must not define script.")
    else:
        if definition.get("allow_shell") is not True:
            errors.append(f"Check {check_id} shell runner requires explicit allow_shell: true.")
        if not isinstance(definition.get("script"), str) or not str(definition.get("script", "")).strip():
            errors.append(f"Check {check_id} shell runner requires a non-empty script.")
        if "argv" in definition:
            errors.append(f"Check {check_id} shell runner must not define argv.")
    return errors


def validate_contract(contract: Mapping[str, Any], expected_id: Optional[str] = None) -> Tuple[List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    if contract.get("schema_version") != SCHEMA_VERSION:
        blocking.append(f"Contract schema_version must be {SCHEMA_VERSION}.")
    if expected_id and contract.get("id") != expected_id:
        blocking.append("Contract id does not match the active Work Unit.")
    if str(contract.get("type", "")) not in {"feature", "bugfix", "refactor", "migration", "docs", "test", "release", "security", "research", "other"}:
        blocking.append("Contract type is invalid.")
    if str(contract.get("risk", "")) not in {"trivial", "low", "medium", "high", "critical"}:
        blocking.append("Contract risk is invalid.")
    for key in ("intent", "expected_outcomes", "non_goals", "scope", "required_evidence", "stop_conditions", "clarification", "context_pointers", "risk_notes"):
        if key not in contract:
            blocking.append(f"Contract is missing {key}.")
    if _contains_placeholder(_semantic_contract(contract)):
        blocking.append("Contract contains unresolved placeholder or empty required content.")
    clarification = contract.get("clarification", {})
    if not isinstance(clarification, dict) or clarification.get("user_confirmed") is not True:
        blocking.append("Clarification must record user_confirmed: true.")
    if not isinstance(clarification, dict) or clarification.get("repo_grounded") is not True:
        blocking.append("Clarification must record repo_grounded: true.")
    if isinstance(clarification, dict):
        assumptions = [x for x in _strings(clarification.get("remaining_assumptions")) if x.lower() not in {"none", "n/a", "无"}]
        if assumptions:
            warnings.append("Contract retains explicit assumptions; reviewer should verify them.")
    questions = [x for x in _strings(contract.get("open_questions")) if x.lower() not in {"none", "n/a", "无"}]
    if questions:
        blocking.append("Contract still contains open questions.")
    required = evidence_items(contract)
    if not required:
        blocking.append("Contract must define at least one required evidence claim.")
    checks = check_definitions(contract)
    seen: set[str] = set()
    for row in required:
        claim_id = str(row.get("id", "")).strip()
        claim = str(row.get("claim", "")).strip()
        check_id = str(row.get("check_id", "")).strip()
        if not claim_id:
            blocking.append("Required evidence item is missing id.")
        elif claim_id in seen:
            blocking.append(f"Duplicate required evidence id: {claim_id}")
        seen.add(claim_id)
        if not claim:
            blocking.append(f"Required evidence {claim_id or '<unknown>'} is missing claim.")
        if not check_id:
            blocking.append(f"Required evidence {claim_id or '<unknown>'} is missing check_id.")
        elif check_id not in checks:
            blocking.append(f"Required evidence {claim_id or '<unknown>'} references undefined check {check_id!r}.")
    for check_id, definition in checks.items():
        blocking.extend(validate_check(check_id, definition))
    return blocking, warnings


# --------------------------- legacy migration ---------------------------

def _section_lines(text: str, heading: str) -> List[str]:
    lines = text.splitlines()
    target = heading.strip().lower()
    start: Optional[int] = None
    level = len(heading) - len(heading.lstrip("#"))
    for index, line in enumerate(lines):
        if line.strip().lower() == target:
            start = index + 1
            break
    if start is None:
        return []
    out: List[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("#"):
            next_level = len(stripped) - len(stripped.lstrip("#"))
            if next_level <= level:
                break
        out.append(line)
    return out


def _bullets(text: str, heading: str) -> List[str]:
    return [unquote_pair(line.strip()[2:]) for line in _section_lines(text, heading) if line.strip().startswith("- ")]


def _legacy_meta(text: str) -> Dict[str, str]:
    match = re.search(r"```ya?ml\s*\n(.*?)\n```", text, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        return {}
    out: Dict[str, str] = {}
    for raw in match.group(1).splitlines():
        if ":" in raw:
            key, value = raw.split(":", 1)
            out[key.strip()] = unquote_pair(value)
    return out


def _legacy_text(text: str, heading: str) -> str:
    return "\n".join(line.strip() for line in _section_lines(text, heading) if line.strip() and not line.strip().startswith("#")).strip()


def _legacy_evidence(text: str) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    rows: List[Dict[str, str]] = []
    current: Optional[Dict[str, str]] = None
    for raw in _section_lines(text, "## Required evidence"):
        stripped = raw.strip()
        if stripped.startswith("- id:"):
            if current:
                rows.append(current)
            current = {"id": unquote_pair(stripped.split(":", 1)[1])}
        elif current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = unquote_pair(value)
    if current:
        rows.append(current)
    evidence: List[Dict[str, Any]] = []
    checks: Dict[str, Dict[str, Any]] = {}
    for index, row in enumerate(rows, start=1):
        claim_id = row.get("id") or f"EV{index}"
        check_id = f"check.{claim_id.lower()}"
        command = row.get("command", "")
        definition: Dict[str, Any]
        if re.search(r"(^|\s)(\||&&|;|>|<)(\s|$)", command):
            definition = {"runner": "shell", "shell": "bash", "script": command, "allow_shell": True, "cwd": ".", "timeout_seconds": 1800}
        else:
            try:
                argv = shlex.split(command)
            except ValueError as exc:
                raise ContractError(f"Cannot migrate evidence command for {claim_id}: {exc}") from exc
            definition = {"runner": "exec", "argv": argv, "cwd": ".", "timeout_seconds": 1800}
        evidence.append({"id": claim_id, "claim": row.get("claim", claim_id), "check_id": check_id})
        checks[check_id] = definition
    return evidence, checks


def migrate_legacy(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if START in text:
        return load_contract(path)
    meta = _legacy_meta(text)
    evidence, checks = _legacy_evidence(text)
    work_unit_id = meta.get("id") or path.stem
    title = meta.get("title") or work_unit_id
    clarification = {}
    for raw in _section_lines(text, "## Clarification record"):
        stripped = raw.strip().lstrip("-").strip()
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            clarification[key.strip().replace("-", "_")] = unquote_pair(value)
    contract = default_contract(work_unit_id, title, meta.get("type", "other"), meta.get("risk", "low"))
    contract.update(
        {
            "intent": _legacy_text(text, "## Intent"),
            "expected_outcomes": _bullets(text, "## Expected Outcome"),
            "non_goals": _bullets(text, "## Non-goals"),
            "scope": {
                "likely_changed_areas": _bullets(text, "### Likely changed areas"),
                "write_boundary": _bullets(text, "### Write boundary"),
                "out_of_bounds": _bullets(text, "### Out of bounds"),
            },
            "required_evidence": evidence,
            "verification": {"checks": checks},
            "stop_conditions": {
                "success": _bullets(text, "### Success"),
                "blocked": _bullets(text, "### Blocked"),
            },
            "clarification": {
                "user_confirmed": str(clarification.get("user_confirmed", "")).lower() in {"yes", "true", "1"},
                "repo_grounded": str(clarification.get("repo_grounded", "")).lower() in {"yes", "true", "1"},
                "key_decisions": [clarification.get("key_decisions", "none")],
                "remaining_assumptions": [clarification.get("remaining_assumptions", "none")],
            },
            "open_questions": _bullets(text, "## Open questions") or ["none"],
            "context_pointers": _bullets(text, "## Context pointers") or ["none"],
            "risk_notes": _bullets(text, "## Risk notes") or ["none"],
        }
    )
    approval = contract["approval"]
    approval.update(
        {
            "status": meta.get("status", "draft"),
            "approved_by": meta.get("approved_by", ""),
            "approved_at": meta.get("approved_at", ""),
            "approval_ref": meta.get("approval_ref", ""),
            # Old hash semantics are intentionally not trusted after migration.
            "approved_content_hash": "",
        }
    )
    path.write_text(render_spec(contract, "Migrated from the repository's previous Markdown/YAML spec format. Review and reapprove before execution."), encoding="utf-8")
    return contract


def validate_check_definition(check_id: str, definition: Mapping[str, Any]) -> List[str]:
    """Compatibility name used by structured check execution."""
    return validate_check(check_id, definition)
