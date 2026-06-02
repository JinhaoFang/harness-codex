#!/usr/bin/env python3
"""Small controller CLI for a coding-agent harness.

This controller owns deterministic lifecycle checks only. It does not judge product
quality and it does not replace human/product review.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import fnmatch
import hashlib
import json
import os
import re
import time
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT_MARKERS = (".git", "pyproject.toml", "AGENTS.md", "CLAUDE.md")
STATE_SCHEMA = "harness.work_unit_state.v1"
EVIDENCE_SCHEMA = "harness.evidence_receipt.v2.1"
REVIEW_SCHEMA = "harness.review_verdict.v1"
WAIVER_SCHEMA = "harness.waiver.v1"
VALID_STATUSES = ["draft", "specified", "ready", "running", "verifying", "reviewing", "integrating", "handoff", "archived", "blocked"]
RISK_ORDER = {"trivial": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
PASS_DECISIONS = {"PASS", "PASS_WITH_RISK_ACCEPTED"}
LIFECYCLE_PATH_PREFIXES = (".harness/",)
REVIEW_MODES = ["plan", "close", "close-addendum", "publication", "risk", "security", "architecture", "evaluator"]
AMENDMENT_IMPACTS = {
    "context_only": {"plan_review_required": False, "affects_implementation": False, "affects_acceptance": False, "recommended_review": "none"},
    "collaboration_only": {"plan_review_required": False, "affects_implementation": False, "affects_acceptance": True, "recommended_review": "publication"},
    "evidence_only": {"plan_review_required": False, "affects_implementation": False, "affects_acceptance": True, "recommended_review": "close-addendum"},
    "success_criteria": {"plan_review_required": True, "affects_implementation": False, "affects_acceptance": True, "recommended_review": "close-addendum_or_close"},
    "scope_or_risk": {"plan_review_required": True, "affects_implementation": True, "affects_acceptance": True, "recommended_review": "close"},
    "implementation": {"plan_review_required": True, "affects_implementation": True, "affects_acceptance": True, "recommended_review": "close"},
}


class HarnessError(Exception):
    pass


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def find_root(start: Path) -> Path:
    cur = start.resolve()
    while True:
        if any((cur / marker).exists() for marker in ROOT_MARKERS):
            return cur
        if cur.parent == cur:
            return start.resolve()
        cur = cur.parent


def run_git(root: Path, args: List[str], default: str = "") -> str:
    try:
        proc = subprocess.run(["git", "--no-pager", *args], cwd=root, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False, timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return default
    if proc.returncode != 0:
        return default
    return proc.stdout.strip()


def current_branch(root: Path) -> str:
    return run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"], "no-git")


def head_commit(root: Path) -> str:
    return run_git(root, ["rev-parse", "HEAD"], "no-git")


def changed_files(root: Path) -> List[str]:
    out = run_git(root, ["status", "--short"], "")
    files: List[str] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        files.append(path)
    return sorted(set(files))


def work_unit_changed_files(root: Path, base_commit: str = "") -> List[str]:
    """Return files changed for the Work Unit, including committed and uncommitted changes.

    `git status` only sees the working tree. A Work Unit can also contain local commits
    created after the Work Unit started, so scope and evidence gates must compare the
    current tree against the Work Unit base commit when one is known.
    """
    files = set(changed_files(root))
    if base_commit and base_commit not in {"no-git", ""} and run_git(root, ["rev-parse", "--is-inside-work-tree"], "false") == "true":
        out = run_git(root, ["diff", "--name-only", "--diff-filter=ACMRTUXB", f"{base_commit}..HEAD"], "")
        files.update(x.strip() for x in out.splitlines() if x.strip())
    return sorted(files)


def lifecycle_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in LIFECYCLE_PATH_PREFIXES)


def diff_hash(root: Path, base_commit: str = "", include_lifecycle: bool = True) -> str:
    if run_git(root, ["rev-parse", "--is-inside-work-tree"], "false") != "true":
        return "no-git"
    h = hashlib.sha256()
    h.update((base_commit or "").encode("utf-8"))
    queries: List[List[str]] = []
    if base_commit and base_commit not in {"no-git", ""}:
        queries.append(["diff", "--no-ext-diff", "--name-status", f"{base_commit}..HEAD"])
    queries.extend((["diff", "--no-ext-diff", "--name-status"], ["diff", "--cached", "--no-ext-diff", "--name-status"], ["status", "--short"]))
    for args in queries:
        out = run_git(root, args, "")
        if not include_lifecycle:
            out = "\n".join(line for line in out.splitlines() if not line_touches_lifecycle_path(line))
        h.update("\0".join(args).encode("utf-8"))
        h.update(out.encode("utf-8"))
    return h.hexdigest()


def line_touches_lifecycle_path(line: str) -> bool:
    parts = line.split()
    paths = parts[1:] if len(parts) > 1 else parts
    if "->" in line:
        paths = [p.strip() for p in line.split("->")]
    return bool(paths) and all(lifecycle_path(p.strip()) for p in paths)


def implementation_diff_hash(root: Path, base_commit: str = "") -> str:
    h = hashlib.sha256()
    h.update((base_commit or "").encode("utf-8"))
    for rel in implementation_changed_files(root, base_commit):
        h.update(rel.encode("utf-8"))
        path = root / rel
        if path.is_file():
            h.update(path.read_bytes())
        else:
            h.update(b"<missing>")
    return h.hexdigest()


def implementation_changed_files(root: Path, base_commit: str = "") -> List[str]:
    expanded: set[str] = set()
    for rel in work_unit_changed_files(root, base_commit):
        if lifecycle_path(rel):
            continue
        path = root / rel
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and ".git" not in child.parts:
                    expanded.add(child.relative_to(root).as_posix())
            continue
        expanded.add(rel.rstrip("/"))
    return sorted(expanded)


def harness_dir(root: Path) -> Path:
    return root / ".harness"


def work_units_dir(root: Path) -> Path:
    return harness_dir(root) / "work-units"


def active_dir(root: Path) -> Path:
    return work_units_dir(root) / "active"


def archive_dir(root: Path) -> Path:
    return work_units_dir(root) / "archive"


def current_file(root: Path) -> Path:
    return harness_dir(root) / "current"


def resolve_wu(root: Path, work_unit_id: Optional[str]) -> Tuple[str, Path]:
    if not work_unit_id:
        cur = current_file(root)
        if cur.exists():
            work_unit_id = cur.read_text(encoding="utf-8").strip()
    if not work_unit_id:
        candidates = sorted(p.name for p in active_dir(root).glob("*") if p.is_dir()) if active_dir(root).exists() else []
        if len(candidates) == 1:
            work_unit_id = candidates[0]
    if not work_unit_id:
        raise HarnessError("No Work Unit id supplied and no current Work Unit is set.")
    path = active_dir(root) / work_unit_id
    if not path.exists():
        archived = archive_dir(root) / work_unit_id
        if archived.exists():
            return work_unit_id, archived
        raise HarnessError(f"Work Unit not found: {work_unit_id}")
    return work_unit_id, path


@contextlib.contextmanager
def exclusive_file_lock(lock_path: Path):
    """Process-level advisory lock for controller-owned files.

    This prevents read-modify-write lifecycle operations from racing when an
    agent, hook, or human runs multiple harnessctl commands at the same time.
    It is intentionally local and small; it is not a distributed lock.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.time() + 5.0
    with lock_path.open("a+", encoding="utf-8") as lock_fh:
        while True:
            try:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() >= deadline:
                    raise HarnessError(f"Timed out waiting for controller lock: {lock_path}")
                time.sleep(0.02)
        try:
            yield
        finally:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise HarnessError(f"Missing JSON file: {path}")
    last_exc: Optional[json.JSONDecodeError] = None
    for _ in range(3):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            last_exc = exc
            time.sleep(0.02)
    raise HarnessError(f"Invalid JSON in {path}: {last_exc}")


def write_json(path: Path, obj: Any) -> None:
    atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n"
    with exclusive_file_lock(path.with_suffix(path.suffix + ".lock")):
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise HarnessError(f"Invalid JSONL in {path}:{n}: {exc}") from exc
    return rows


def contract_path(wu_path: Path) -> Path:
    return wu_path / "contract.md"


def state_path(wu_path: Path) -> Path:
    return wu_path / "state.json"


def receipts_path(wu_path: Path) -> Path:
    return wu_path / "evidence" / "receipts.jsonl"


def reviews_dir(wu_path: Path) -> Path:
    return wu_path / "reviews"


def amendments_path(wu_path: Path) -> Path:
    return wu_path / "amendments.jsonl"


def waivers_dir(wu_path: Path) -> Path:
    return wu_path / "waivers"


def contract_hash(wu_path: Path) -> str:
    path = contract_path(wu_path)
    if not path.exists():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lock_mismatch(state: Dict[str, Any], wu_path: Path) -> str:
    if not state.get("contract_locked"):
        return ""
    expected = str(state.get("contract_lock_hash", ""))
    actual = contract_hash(wu_path)
    if expected and expected != actual:
        return f"contract.md changed after lock without amendment: expected {expected[:12]}, got {actual[:12]}"
    return ""


def update_state(root: Path, wu_path: Path, **patch: Any) -> Dict[str, Any]:
    spath = state_path(wu_path)
    with exclusive_file_lock(wu_path / ".state.lock"):
        state = load_json(spath)
        state.update({k: v for k, v in patch.items() if v is not None})
        state["branch"] = current_branch(root)
        state["head_commit"] = head_commit(root)
        base_commit = str(state.get("base_commit", ""))
        state["diff_hash"] = diff_hash(root, base_commit)
        state["implementation_diff_hash"] = implementation_diff_hash(root, base_commit)
        state["changed_files"] = work_unit_changed_files(root, base_commit)
        state["updated_at"] = now_iso()
        write_json(spath, state)
        return state


def clean_scalar(value: str) -> str:
    value = value.strip()
    if value.startswith("- "):
        value = value[2:].strip()
    return value.strip().strip('"').strip("'")


def append_field_value(values: Dict[str, str], key: str, value: str) -> None:
    cleaned = clean_scalar(value)
    if not cleaned:
        return
    current = values.get(key, "").strip()
    values[key] = f"{current}; {cleaned}" if current else cleaned


def parse_yaml_header(text: str) -> Dict[str, str]:
    if "```yaml" not in text:
        return {}
    block = text.split("```yaml", 1)[1].split("```", 1)[0]
    out: Dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = clean_scalar(value)
    return out


def get_section_lines(text: str, heading: str) -> List[str]:
    lines = text.splitlines()
    start = None
    target = normalize_heading(heading)
    for i, line in enumerate(lines):
        if normalize_heading(line) == target:
            start = i + 1
            break
    if start is None:
        return []
    out = []
    for line in lines[start:]:
        if line.startswith("#") and line.strip().lower() != target:
            break
        out.append(line)
    return out


def normalize_heading(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"^#+\s*", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def has_heading(text: str, heading: str) -> bool:
    target = normalize_heading(heading)
    return any(normalize_heading(line) == target for line in text.splitlines())


def bullets_after_subheading(text: str, subheading: str) -> List[str]:
    lines = text.splitlines()
    start = None
    target = subheading.strip().lower()
    for i, line in enumerate(lines):
        if line.strip().lower() == target:
            start = i + 1
            break
    if start is None:
        return []
    values: List[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("### ") or stripped.startswith("## "):
            break
        if stripped.startswith("- "):
            value = stripped[2:].strip()
            if value and value.upper() != "TBD":
                values.append(value)
    return values


def contract_meta(wu_path: Path) -> Dict[str, str]:
    text = contract_path(wu_path).read_text(encoding="utf-8") if contract_path(wu_path).exists() else ""
    header = parse_yaml_header(text)
    if not header:
        header = {"risk": load_json(state_path(wu_path), {}).get("risk", "low")}
    return header


def contract_summary(wu_path: Path, max_chars: int = 700) -> str:
    path = contract_path(wu_path)
    if not path.exists():
        return "Missing contract.md"
    text = path.read_text(encoding="utf-8")
    summary = []
    for heading in ("## Intent", "## Expected Outcome", "## Scope", "## Required evidence", "## Clarification record", "## Open questions"):
        section = "\n".join(get_section_lines(text, heading)).strip()
        if section:
            summary.append(f"{heading}\n{section}")
    joined = "\n\n".join(summary).strip()
    if not joined:
        joined = text[:max_chars]
    if len(joined) > max_chars:
        joined = joined[:max_chars].rstrip() + "..."
    return joined


def has_placeholder(text: str) -> bool:
    lowered = text.lower()
    return "tbd" in lowered or "todo" in lowered or "{{" in text


def is_empty_marker(value: str) -> bool:
    normalized = value.strip().strip(".。；;").lower()
    return normalized in {"", "tbd", "todo", "none", "n/a", "na", "not applicable", "resolved", "no open questions"}


def meaningful_bullets_after_subheading(text: str, subheading: str) -> List[str]:
    return [x for x in bullets_after_subheading(text, subheading) if not is_empty_marker(x)]


def meaningful_section_lines(text: str, heading: str) -> List[str]:
    out: List[str] = []
    for line in get_section_lines(text, heading):
        stripped = line.strip()
        if not stripped or stripped.startswith("### "):
            continue
        if stripped.startswith("-"):
            stripped = stripped[1:].strip()
        if not is_empty_marker(stripped):
            out.append(stripped)
    return out


def glob_matches(path: str, patterns: Iterable[str]) -> bool:
    for pattern in patterns:
        pattern = pattern.strip()
        if not pattern or pattern.upper() == "TBD":
            continue
        if fnmatch.fnmatch(path, pattern) or path.startswith(pattern.rstrip("/") + "/") or path == pattern.rstrip("/"):
            return True
    return False


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "yes", "1", "required", "confirmed"}:
        return True
    first = re.split(r"[\s,;:.]+", text, 1)[0]
    return first in {"true", "yes", "1", "required", "confirmed"}


def parse_percent(value: Any) -> Optional[float]:
    text = str(value).strip().rstrip("%")
    try:
        return float(text)
    except ValueError:
        return None


def section_key_values(text: str, heading: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    key_re = re.compile(r"^-?\s*([A-Za-z][A-Za-z0-9 _-]*)\s*:\s*(.*)$")
    current_key = ""
    current_indent = 0
    for raw in get_section_lines(text, heading):
        stripped = raw.strip()
        if not stripped or stripped.startswith("### "):
            continue
        indent = len(raw) - len(raw.lstrip())
        if current_key and indent > current_indent:
            append_field_value(values, current_key, stripped)
            continue
        match = key_re.match(stripped)
        if not match:
            if current_key and (raw.startswith(" ") or raw.startswith("\t") or stripped.startswith("- ")):
                append_field_value(values, current_key, stripped)
            continue
        key = match.group(1).strip().lower().replace("-", "_").replace(" ", "_")
        values[key] = clean_scalar(match.group(2))
        current_key = key
        current_indent = indent
    return values


def check_clarification_record(text: str, non_trivial: bool) -> Tuple[List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    if not has_heading(text, "## Clarification record"):
        msg = "Missing heading: ## Clarification record. Open questions alone do not prove clarify happened."
        if non_trivial:
            blocking.append(msg)
        else:
            warnings.append(msg)
        return blocking, warnings

    values = section_key_values(text, "## Clarification record")
    requirements = {
        "user_confirmed": "Clarification record must set user_confirmed: yes before locking non-trivial work.",
        "repo_grounded": "Clarification record must set repo_grounded: yes after inspecting relevant project truth.",
    }
    for key, message in requirements.items():
        if not parse_bool(values.get(key, "")):
            if non_trivial:
                blocking.append(message)
            else:
                warnings.append(message)

    confidence_requirements = {
        "user_intent_confidence": "user_intent_confidence is below 95; record unresolved intent risk if this matters.",
        "project_reality_confidence": "project_reality_confidence is below 95; record unresolved repo-grounding risk if this matters.",
    }
    for key, message in confidence_requirements.items():
        score = parse_percent(values.get(key, ""))
        if score is None or score < 95:
            warnings.append(message)

    assumptions = values.get("remaining_assumptions", "")
    if not assumptions:
        msg = "Clarification record must include remaining_assumptions; use none only when no material assumptions remain."
        if non_trivial:
            blocking.append(msg)
        else:
            warnings.append(msg)
    elif not assumption_value_resolved(assumptions):
        msg = "remaining_assumptions must be none/resolved or explicitly accepted; unresolved assumptions block spec lock."
        if non_trivial:
            blocking.append(msg)
        else:
            warnings.append(msg)

    if not values.get("key_decisions") or is_empty_marker(values.get("key_decisions", "")):
        warnings.append("Clarification record has no key_decisions. Record at least one decision or why none were needed.")
    return blocking, warnings


def assumption_value_resolved(value: str) -> bool:
    text = value.strip().lower()
    if is_empty_marker(text):
        return True
    return text.startswith(("none", "resolved", "accepted:", "accepted ", "no material", "no remaining"))


def required_evidence_items(wu_path: Path) -> List[Dict[str, Any]]:
    """Parse required evidence from contract.md.

    This intentionally supports the compact Markdown shape used by the template:

    - id: EV1
      claim: ...
      command: ...
      required_for_completion: true

    It also accepts simple bullets such as `- EV1: run unit tests`. The parser is
    deliberately small and strict enough for controller checks without making the
    contract depend on a full YAML document.
    """
    path = contract_path(wu_path)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    lines = get_section_lines(text, "## Required evidence")
    items: List[Dict[str, Any]] = []
    cur: Optional[Dict[str, Any]] = None
    current_field = ""
    current_field_indent = 0
    simple_id_re = re.compile(r"^-\s*([A-Za-z][A-Za-z0-9_.:-]*)\s*:?(.*)$")
    key_re = re.compile(r"^(id|claim|command|required_for_completion|type|scope|covers)\s*:\s*(.*)$")
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        m = key_re.match(stripped)
        if m and cur is not None:
            key, value = m.group(1), m.group(2).strip()
            cur[key] = clean_scalar(value)
            current_field = key
            current_field_indent = indent
            continue
        if cur is not None and current_field and indent > current_field_indent:
            append_field_value(cur, current_field, stripped)
            continue
        if stripped.startswith("- "):
            body = stripped[2:].strip()
            if body.upper() == "TBD":
                continue
            if body.startswith("id:"):
                if cur:
                    items.append(cur)
                cur = {"id": clean_scalar(body.split(":", 1)[1])}
                current_field = "id"
                current_field_indent = indent
                continue
            m = simple_id_re.match(stripped)
            if m:
                if cur:
                    items.append(cur)
                ev_id, rest = m.group(1).strip(), m.group(2).strip()
                cur = {"id": ev_id}
                if rest:
                    cur["claim"] = clean_scalar(rest)
                    current_field = "claim"
                else:
                    current_field = "id"
                current_field_indent = indent
                continue
    if cur:
        items.append(cur)

    # Deduplicate by id while preserving order. Only explicit completion evidence
    # is checked; missing flag defaults to required because this section is named
    # Required evidence.
    out: List[Dict[str, Any]] = []
    seen = set()
    for item in items:
        ev_id = str(item.get("id", "")).strip()
        if not ev_id or ev_id.upper() == "TBD" or ev_id in seen:
            continue
        if item.get("required_for_completion") not in (None, "") and not parse_bool(item.get("required_for_completion")):
            continue
        item["id"] = ev_id
        out.append(item)
        seen.add(ev_id)
    return out


def waivers_by_requirement(wu_path: Path, work_unit_id: str) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for path in sorted(waivers_dir(wu_path).glob("*.json")):
        obj = load_json(path, {})
        if obj.get("work_unit_id") != work_unit_id:
            continue
        req = str(obj.get("waived_requirement", "")).strip()
        if not req:
            continue
        out.setdefault(req, []).append(obj)
    return out


def waiver_is_current(obj: Dict[str, Any]) -> Tuple[bool, str]:
    if not str(obj.get("approved_by", "")).startswith("human:"):
        return False, "waiver is not approved by a human owner"
    expires = str(obj.get("expires_at", "")).strip()
    if expires:
        try:
            # Accept YYYY-MM-DD or full ISO. Date-only expiry is end-of-day UTC.
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", expires):
                expiry = dt.datetime.fromisoformat(expires + "T23:59:59+00:00")
            else:
                expiry = dt.datetime.fromisoformat(expires.replace("Z", "+00:00"))
            if dt.datetime.now(dt.timezone.utc) > expiry:
                return False, f"waiver expired at {expires}"
        except ValueError:
            return False, f"waiver has invalid expires_at: {expires}"
    return True, ""


def evidence_receipts(wu_path: Path, work_unit_id: str) -> List[Dict[str, Any]]:
    return [r for r in read_jsonl(receipts_path(wu_path)) if r.get("work_unit_id") == work_unit_id]


def latest_pass_for_claim(wu_path: Path, work_unit_id: str, claim_ref: str) -> Optional[Dict[str, Any]]:
    passes = [r for r in evidence_receipts(wu_path, work_unit_id) if r.get("result") == "pass" and str(r.get("claim_ref", "")).strip() == claim_ref]
    if not passes:
        return None
    return sorted(passes, key=lambda r: r.get("ended_at", ""))[-1]


def receipts_by_id(wu_path: Path, work_unit_id: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for receipt in evidence_receipts(wu_path, work_unit_id):
        rid = str(receipt.get("receipt_id", "")).strip()
        if rid:
            out[rid] = receipt
    return out


def cited_receipts_by_claim(wu_path: Path, work_unit_id: str, evidence_refs: set[str]) -> Dict[str, List[Dict[str, Any]]]:
    by_id = receipts_by_id(wu_path, work_unit_id)
    out: Dict[str, List[Dict[str, Any]]] = {}
    for rid in evidence_refs:
        receipt = by_id.get(rid)
        if not receipt or receipt.get("result") != "pass":
            continue
        claim = str(receipt.get("claim_ref", "")).strip()
        if claim:
            out.setdefault(claim, []).append(receipt)
    return out


def receipt_has_reviewable_support(receipt: Dict[str, Any]) -> bool:
    if receipt.get("artifact_uri") or receipt.get("command_log_ref") or receipt.get("manual_artifact_ref"):
        return True
    command = str(receipt.get("command", "")).strip()
    return bool(command)


def receipt_review_surface(receipt: Dict[str, Any]) -> str:
    """Classify the review surface a receipt belongs to.

    This is intentionally conservative and local. Publication/collaboration evidence
    is not implementation evidence, and refreshing an implementation receipt does
    not by itself create a new review judgment.
    """
    text = " ".join(
        str(receipt.get(key, ""))
        for key in ("type", "command", "artifact_uri", "manual_artifact_ref", "note", "verification_scope")
    ).lower()
    if any(token in text for token in ("gh issue", "gh pr", "github", "pull request", "issue view", "pr view")):
        return "publication"
    if "publication" in text or "collaboration" in text:
        return "publication"
    if str(receipt.get("type", "")).strip().lower() == "manual" and str(receipt.get("artifact_uri", "")).startswith("http"):
        return "publication"
    return "implementation"


def amendment_impacts_after(wu_path: Path, timestamp: str = "") -> List[Dict[str, Any]]:
    amendments = read_jsonl(amendments_path(wu_path))
    if not timestamp:
        return amendments
    return [a for a in amendments if str(a.get("created_at", "")) >= timestamp]


def amendment_affects_judgment(amendment: Dict[str, Any]) -> bool:
    """Return true when an amendment invalidates an existing close judgment.

    Evidence refreshes, publication/collaboration metadata, context pointers,
    state/handoff, and harness runtime changes should not make a close review
    stale. Success criteria, scope, risk, or implementation changes should.
    """
    impact = str(amendment.get("impact") or "").strip()
    if impact in {"implementation", "scope_or_risk", "success_criteria"}:
        return True
    if amendment_affects_implementation(amendment):
        return True
    field = str(amendment.get("field", "")).strip()
    if field in {"intent", "scope", "risk", "success", "stop_conditions"}:
        return True
    return False


def review_implementation_hash(verdict: Dict[str, Any], wu_path: Path, work_unit_id: str) -> str:
    explicit = str(verdict.get("reviewed_implementation_diff_hash", "")).strip()
    if explicit:
        return explicit
    by_id = receipts_by_id(wu_path, work_unit_id)
    hashes = []
    for rid in verdict.get("evidence_refs", []) or []:
        receipt = by_id.get(str(rid).strip())
        if not receipt:
            continue
        value = str(receipt.get("implementation_diff_hash", "")).strip()
        if value:
            hashes.append(value)
    unique = sorted(set(hashes))
    return unique[0] if len(unique) == 1 else ""


def review_verdicts(wu_path: Path) -> List[Dict[str, Any]]:
    out = []
    for path in sorted(reviews_dir(wu_path).glob("verdict-*.json")):
        out.append(load_json(path))
    return out


def ensure_gitignore_entry(root: Path, entry: str) -> None:
    path = root / ".gitignore"
    if path.exists():
        text = path.read_text(encoding="utf-8")
        lines = [line.strip() for line in text.splitlines()]
        if entry.rstrip("/") in lines or entry in lines:
            return
        prefix = "" if text.endswith("\n") or not text else "\n"
        path.write_text(text + prefix + entry + "\n", encoding="utf-8")
        return
    path.write_text(entry + "\n", encoding="utf-8")


def init(args: argparse.Namespace) -> int:
    root = args.root
    for p in [active_dir(root), archive_dir(root), harness_dir(root) / "tmp"]:
        p.mkdir(parents=True, exist_ok=True)
    ensure_gitignore_entry(root, ".harness/")
    config = harness_dir(root) / "config.json"
    if not config.exists():
        write_json(config, {
            "schema_version": "harness.config.v1",
            "profile": "controlled",
            "created_at": now_iso(),
            "work_units_dir": ".harness/work-units",
            "default_required_gates": ["spec", "verification"],
            "high_risk_requires": ["independent_review_or_human_gate", "rollback_or_reopen_path"]
        })
    print(f"Initialized harness at {harness_dir(root)}")
    return 0


def new(args: argparse.Namespace) -> int:
    root = args.root
    init(argparse.Namespace(root=root))
    wu_path = active_dir(root) / args.id
    if wu_path.exists():
        raise HarnessError(f"Work Unit already exists: {args.id}")
    for p in [wu_path / "evidence" / "artifacts", wu_path / "reviews", wu_path / "waivers"]:
        p.mkdir(parents=True, exist_ok=True)
    template = (root / "harness" / "templates" / "work-unit-contract.md")
    if template.exists():
        text = template.read_text(encoding="utf-8")
    else:
        text = "# Work Unit Contract: {{id}}\n"
    text = text.replace("{{id}}", args.id).replace("{{title}}", args.title).replace("{{type}}", args.type).replace("{{risk}}", args.risk)
    contract_path(wu_path).write_text(text, encoding="utf-8")
    state = {
        "schema_version": STATE_SCHEMA,
        "work_unit_id": args.id,
        "status": "draft",
        "risk": args.risk,
        "branch": current_branch(root),
        "worktree": str(root),
        "base_commit": head_commit(root),
        "started_at_head": head_commit(root),
        "head_commit": head_commit(root),
        "diff_hash": diff_hash(root, head_commit(root)),
        "implementation_diff_hash": implementation_diff_hash(root, head_commit(root)),
        "contract_locked": False,
        "contract_lock_hash": "",
        "locked_at": "",
        "last_amendment_at": "",
        "changed_files": work_unit_changed_files(root, head_commit(root)),
        "latest_evidence_refs": [],
        "known_failures": [],
        "blockers": [],
        "next_safe_action": "Fill contract.md and run spec gate.",
        "rollback_or_reopen_path": "Reopen this Work Unit or revert the branch before integration.",
        "updated_at": now_iso()
    }
    write_json(state_path(wu_path), state)
    receipts_path(wu_path).touch()
    amendments_path(wu_path).touch()
    (wu_path / "handoff.md").write_text("# Handoff\n\nNot generated yet. Run `harnessctl handoff`.\n", encoding="utf-8")
    current_file(root).write_text(args.id + "\n", encoding="utf-8")
    print(f"Created Work Unit {args.id}: {wu_path}")
    return 0


def list_wu(args: argparse.Namespace) -> int:
    root = args.root
    for label, base in (("active", active_dir(root)), ("archive", archive_dir(root))):
        if not base.exists():
            continue
        for p in sorted(base.iterdir()):
            if p.is_dir():
                status = load_json(state_path(p), {}).get("status", "unknown") if state_path(p).exists() else "unknown"
                print(f"{label}\t{p.name}\t{status}")
    return 0


def status(args: argparse.Namespace) -> int:
    root = args.root
    _, wu_path = resolve_wu(root, args.id)
    print(json.dumps(load_json(state_path(wu_path)), ensure_ascii=False, indent=2))
    return 0


def brief(args: argparse.Namespace) -> int:
    root = args.root
    try:
        work_unit_id, wu_path = resolve_wu(root, args.id)
    except HarnessError:
        print("No active Work Unit. For non-trivial work, create one with `harnessctl new --id ...`.")
        return 0
    state = load_json(state_path(wu_path))
    rows = read_jsonl(receipts_path(wu_path))[-5:]
    verdicts = review_verdicts(wu_path)[-3:]
    print(f"# Harness Brief: {work_unit_id}")
    print("\n## Contract summary\n")
    print(contract_summary(wu_path))
    print("\n## State\n")
    print(json.dumps({
        "status": state.get("status"),
        "risk": state.get("risk"),
        "branch": state.get("branch"),
        "head_commit": state.get("head_commit"),
        "diff_hash": state.get("diff_hash"),
        "changed_files": state.get("changed_files"),
        "known_failures": state.get("known_failures"),
        "blockers": state.get("blockers"),
        "next_safe_action": state.get("next_safe_action"),
    }, ensure_ascii=False, indent=2))
    print("\n## Latest evidence\n")
    if rows:
        for r in rows:
            print(f"- {r.get('receipt_id')} {r.get('result')} {r.get('claim_ref')} {r.get('type')} {r.get('command')}")
    else:
        print("- none")
    print("\n## Latest review verdicts\n")
    if verdicts:
        for v in verdicts:
            print(f"- {v.get('review_id')} {v.get('mode')} {v.get('decision')} independent={v.get('is_independent')}")
    else:
        print("- none")
    return 0


def infer_amendment_impact(field: str, review_impact: str = "plan", explicit_impact: str = "") -> str:
    if explicit_impact:
        return explicit_impact
    if review_impact == "none":
        return "context_only"
    if field in {"risk", "scope"}:
        return "scope_or_risk"
    if field == "success":
        return "success_criteria"
    if field == "required_evidence":
        return "evidence_only"
    if field == "context":
        return "context_only"
    return "implementation"


def validate_amendment_impact(field: str, impact: str, review_impact: str = "plan") -> None:
    if impact not in AMENDMENT_IMPACTS:
        raise HarnessError(f"Invalid amendment impact: {impact}")
    if review_impact == "none" and impact != "context_only":
        raise HarnessError("--review-impact none is only allowed for context-only amendments; use --impact evidence_only or collaboration_only for lightweight non-context amendments.")
    if impact == "context_only" and field not in {"context", "other"}:
        raise HarnessError("--review-impact none is only allowed for context-only amendments; context_only amendments are only allowed for context/other fields.")
    if impact == "collaboration_only" and field in {"intent", "scope", "risk"}:
        raise HarnessError("collaboration_only amendments cannot change intent, scope, or risk.")
    if impact == "evidence_only" and field not in {"required_evidence", "context", "other"}:
        raise HarnessError("evidence_only amendments are only allowed for required_evidence/context/other fields.")


def amendment_requires_plan_review(amendment: Dict[str, Any]) -> bool:
    if "plan_review_required" in amendment:
        return parse_bool(amendment.get("plan_review_required"))
    impact = str(amendment.get("impact") or "").strip()
    if impact in AMENDMENT_IMPACTS:
        return bool(AMENDMENT_IMPACTS[impact]["plan_review_required"])
    return str(amendment.get("review_impact", "plan")) != "none"


def amendment_affects_implementation(amendment: Dict[str, Any]) -> bool:
    if "affects_implementation" in amendment:
        return parse_bool(amendment.get("affects_implementation"))
    impact = str(amendment.get("impact") or "").strip()
    if impact in AMENDMENT_IMPACTS:
        return bool(AMENDMENT_IMPACTS[impact]["affects_implementation"])
    return str(amendment.get("review_impact", "plan")) != "none"


def latest_amendment_for_contract(wu_path: Path, current_hash: str) -> Optional[Dict[str, Any]]:
    matches = [a for a in read_jsonl(amendments_path(wu_path)) if a.get("contract_hash") == current_hash]
    return matches[-1] if matches else None


def plan_review_passes(root: Path, wu_path: Path) -> Tuple[bool, List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    state = load_json(state_path(wu_path), {})
    risk = str(state.get("risk") or contract_meta(wu_path).get("risk", "low"))
    passes = [v for v in review_verdicts(wu_path) if v.get("mode") == "plan" and v.get("decision") in PASS_DECISIONS]
    if RISK_ORDER.get(risk, 1) <= 1:
        if not passes:
            warnings.append("Low/trivial risk has no plan review. Self-check may be acceptable.")
            return True, blocking, warnings
    if not passes:
        blocking.append(f"{risk} risk requires a passing plan review before running.")
        return False, blocking, warnings
    latest = sorted(passes, key=lambda v: (v.get("created_at", ""), v.get("review_id", "")))[-1]
    reviewed_hash = str(latest.get("reviewed_contract_hash", ""))
    current_hash = contract_hash(wu_path)
    if reviewed_hash and reviewed_hash != current_hash:
        amendment = latest_amendment_for_contract(wu_path, current_hash)
        if amendment and not amendment_requires_plan_review(amendment):
            impact = str(amendment.get("impact") or amendment.get("review_impact") or "lightweight")
            warnings.append(f"Latest passing plan review was for an older contract, but latest amendment declares no plan/review impact ({impact}); plan re-review is not required.")
        else:
            blocking.append("Latest passing plan review was for an older contract; re-run plan review after amendment.")
    if RISK_ORDER.get(risk, 1) >= 3 and not (latest.get("is_independent") or latest.get("independence_level") == "human_gate"):
        blocking.append(f"{risk} risk requires independent plan review or human gate before running.")
    elif latest.get("independence_level") == "self_check":
        warnings.append("Plan review is a self-check, not independent review.")
    return not blocking, blocking, warnings


def ensure_transition_allowed(root: Path, wu_path: Path, target_status: Optional[str]) -> None:
    if not target_status:
        return
    if target_status in {"specified", "ready"}:
        raise HarnessError("Use `harnessctl lock --status specified|ready` instead of set-state for readiness transitions.")
    if target_status in {"running", "verifying", "reviewing", "integrating", "handoff", "archived"}:
        state = load_json(state_path(wu_path), {})
        if not state.get("contract_locked"):
            raise HarnessError("Work Unit contract is not locked. Run spec gate and `harnessctl lock` before execution.")
        mismatch = lock_mismatch(state, wu_path)
        if mismatch:
            raise HarnessError(mismatch + "; run `harnessctl amend` after intentional contract changes.")
        spec_decision, spec_blocking, _ = check_spec(root, wu_path)
        if spec_decision == "BLOCK":
            raise HarnessError("Spec gate blocks transition: " + "; ".join(spec_blocking))
    if target_status == "running":
        state = load_json(state_path(wu_path), {})
        if state.get("status") != "ready":
            raise HarnessError("Work Unit must be ready before running. Run `harnessctl lock --status ready` after spec changes.")
        ok, blocking, _warnings = plan_review_passes(root, wu_path)
        if not ok:
            raise HarnessError("Plan review gate blocks running: " + "; ".join(blocking))


def lock(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    decision, blocking, warnings = check_spec(root, wu_path)
    if decision == "BLOCK":
        raise HarnessError("Cannot lock Work Unit while spec gate blocks: " + "; ".join(blocking))
    state = update_state(
        root,
        wu_path,
        status=args.status,
        contract_locked=True,
        contract_lock_hash=contract_hash(wu_path),
        locked_at=now_iso(),
        next_safe_action="Request plan review before running." if args.status == "ready" else "Resolve readiness and lock as ready."
    )
    print(json.dumps({
        "schema_version": "harness.lock.v1",
        "work_unit_id": work_unit_id,
        "decision": "LOCKED",
        "status": state.get("status"),
        "contract_lock_hash": state.get("contract_lock_hash"),
        "warnings": warnings,
        "created_at": state.get("locked_at"),
    }, ensure_ascii=False, indent=2))
    return 0


def amend(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    impact = infer_amendment_impact(args.field, args.review_impact, getattr(args, "impact", "") or "")
    validate_amendment_impact(args.field, impact, args.review_impact)
    impact_policy = AMENDMENT_IMPACTS[impact]
    decision, blocking, warnings = check_spec(root, wu_path)
    if decision == "BLOCK" and not args.allow_draft:
        raise HarnessError("Cannot record a locked amendment while spec gate blocks: " + "; ".join(blocking))
    amendment = {
        "schema_version": "harness.contract_amendment.v1",
        "amendment_id": "amend-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6],
        "work_unit_id": work_unit_id,
        "field": args.field,
        "reason": args.reason,
        "summary": args.summary,
        "actor": args.actor,
        "impact": impact,
        "review_impact": args.review_impact,
        "plan_review_required": bool(impact_policy["plan_review_required"]),
        "affects_implementation": bool(impact_policy["affects_implementation"]),
        "affects_acceptance": bool(impact_policy["affects_acceptance"]),
        "recommended_review": impact_policy["recommended_review"],
        "contract_hash": contract_hash(wu_path),
        "created_at": now_iso(),
    }
    append_jsonl(amendments_path(wu_path), amendment)
    if decision == "BLOCK" and args.allow_draft:
        state = update_state(root, wu_path, status="draft", contract_locked=False, contract_lock_hash="", last_amendment_at=amendment["created_at"], next_safe_action="Finish contract amendment and run spec gate before locking.")
    else:
        if amendment_requires_plan_review(amendment):
            next_action = "Re-request plan review before running because the amendment changes planning, implementation, scope, risk, or success criteria."
        elif impact == "collaboration_only":
            next_action = "Record collaboration/publication evidence; plan re-review is not required unless implementation scope changed."
        elif impact == "evidence_only":
            next_action = "Record only the new or stale evidence claims. Do not request close-addendum unless the amendment changes acceptance judgment."
        else:
            next_action = "Lock and continue; latest amendment declares no plan/review impact."
        state = update_state(root, wu_path, status="specified", contract_locked=True, contract_lock_hash=contract_hash(wu_path), last_amendment_at=amendment["created_at"], next_safe_action=next_action)
    print(json.dumps({
        "schema_version": "harness.amendment_recorded.v1",
        "work_unit_id": work_unit_id,
        "amendment": amendment,
        "status": state.get("status"),
        "contract_locked": state.get("contract_locked"),
        "warnings": warnings,
    }, ensure_ascii=False, indent=2))
    return 0

def set_state(args: argparse.Namespace) -> int:
    root = args.root
    _, wu_path = resolve_wu(root, args.id)
    if args.status and args.status not in VALID_STATUSES:
        raise HarnessError(f"Invalid status: {args.status}")
    ensure_transition_allowed(root, wu_path, args.status)
    state = update_state(root, wu_path, status=args.status, next_safe_action=args.next_safe_action)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def evidence(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    if args.result == "skipped" and not args.note:
        raise HarnessError("Skipped evidence requires --note with skipped reason, replacement evidence, and risk impact.")
    receipt_id = "ev-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
    ts = now_iso()
    state = load_json(state_path(wu_path), {})
    base_commit = args.base_commit or str(state.get("base_commit", ""))
    receipt = {
        "schema_version": EVIDENCE_SCHEMA,
        "receipt_id": receipt_id,
        "work_unit_id": work_unit_id,
        "claim_ref": args.claim,
        "actor": args.actor,
        "type": args.type,
        "command": args.command or "",
        "result": args.result,
        "started_at": args.started_at or ts,
        "ended_at": args.ended_at or ts,
        "exit_code": args.exit_code,
        "base_commit": base_commit,
        "head_commit": head_commit(root),
        "diff_hash": diff_hash(root, base_commit),
        "implementation_diff_hash": implementation_diff_hash(root, base_commit),
        "last_relevant_change_at": args.last_relevant_change_at or ts,
        "changed_files": work_unit_changed_files(root, base_commit),
        "covers": args.covers or [],
        "verification_scope": args.verification_scope,
        "freshness_basis": args.freshness_basis or "diff_hash",
        "artifact_uri": args.artifact_uri or "",
        "artifact_hash": args.artifact_hash or "",
        "command_log_ref": args.command_log_ref or "",
        "manual_artifact_ref": args.manual_artifact_ref or "",
        "environment_ref": args.environment_ref or "",
        "waiver_ref": args.waiver_ref or "",
        "note": args.note or ""
    }
    append_jsonl(receipts_path(wu_path), receipt)
    state = load_json(state_path(wu_path))
    refs = state.get("latest_evidence_refs", [])
    refs.append(receipt_id)
    update_state(root, wu_path, latest_evidence_refs=refs[-10:], next_safe_action="Run verification gate or request review.")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


def waiver(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    if not args.approved_by.startswith("human:"):
        raise HarnessError("Waiver requires --approved-by human:<owner>.")
    waiver_id = "waiver-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
    obj = {
        "schema_version": WAIVER_SCHEMA,
        "waiver_id": waiver_id,
        "work_unit_id": work_unit_id,
        "waiver_type": args.waiver_type,
        "requested_by": args.requested_by,
        "approved_by": args.approved_by,
        "reason": args.reason,
        "waived_requirement": args.requirement,
        "replacement_evidence": args.replacement_evidence or [],
        "risk_accepted": args.risk_accepted,
        "expires_at": args.expires_at or "",
        "created_at": now_iso()
    }
    write_json(waivers_dir(wu_path) / f"{waiver_id}.json", obj)
    update_state(root, wu_path, next_safe_action="Run verification gate; waiver can satisfy the skipped requirement only within its risk scope.")
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    return 0


def request_review(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    if args.mode == "close-addendum":
        decision, blocking, warnings = check_review(root, wu_path)
        if decision != "BLOCK":
            raise HarnessError("Close-addendum is not required: review validity gate is not blocking. Receipt refresh, commit materialization, lifecycle updates, and publication metadata do not justify addendum by themselves.")
        if not any("amendment" in x.lower() or "claim" in x.lower() or "contract" in x.lower() for x in blocking):
            raise HarnessError("Close-addendum is not the correct next review. Use full close review, publication check, risk review, waiver, or fresh evidence according to review gate blocking reasons: " + "; ".join(blocking[:3]))
    request_id = "review-request-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
    if args.mode == "plan":
        required_inputs = ["contract.md", "scope boundary", "risk notes", "context pointers", "proposed execution plan"]
    elif args.mode == "publication":
        required_inputs = ["contract.md", "GitHub issue/PR/branch references", "publication evidence receipts", "scope boundary"]
    elif args.mode == "close-addendum":
        required_inputs = ["contract.md", "latest amendment", "previous close review", "new or affected evidence receipts", "git diff hash"]
    else:
        required_inputs = ["contract.md", "git diff", "evidence/receipts.jsonl", "scope boundary", "risk notes"]
    obj = {
        "schema_version": "harness.review_request.v1",
        "request_id": request_id,
        "work_unit_id": work_unit_id,
        "mode": args.mode,
        "reviewer_role": args.reviewer_role,
        "required_inputs": required_inputs,
        "disallowed_primary_inputs": ["builder narrative only", "chat transcript only", "unverified summary only"],
        "created_at": now_iso()
    }
    write_json(reviews_dir(wu_path) / f"request-{request_id}.json", obj)
    update_state(root, wu_path, status="reviewing", next_safe_action=f"Reviewer should submit verdict for {request_id}.")
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    return 0


def submit_review(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    if args.mode in {"close", "close-addendum"} and args.reviewer_role == args.builder_role:
        raise HarnessError("Close review or close-addendum cannot be written by the builder role.")
    is_independent = args.independence_level in {"separate_role", "fresh_context", "human_gate"} and args.reviewer_role != args.builder_role
    review_id = "review-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
    obj = {
        "schema_version": REVIEW_SCHEMA,
        "review_id": review_id,
        "request_id": args.request_id or "",
        "work_unit_id": work_unit_id,
        "mode": args.mode,
        "reviewer_role": args.reviewer_role,
        "builder_role": args.builder_role,
        "independence_level": args.independence_level,
        "is_independent": is_independent,
        "decision": args.decision,
        "reviewed_contract_ref": "contract.md",
        "reviewed_contract_hash": contract_hash(wu_path),
        "reviewed_diff_ref": "git diff",
        "reviewed_head_commit": head_commit(root),
        "reviewed_diff_hash": diff_hash(root, str(load_json(state_path(wu_path), {}).get("base_commit", ""))),
        "reviewed_implementation_diff_hash": implementation_diff_hash(root, str(load_json(state_path(wu_path), {}).get("base_commit", ""))),
        "reviewed_changed_files": work_unit_changed_files(root, str(load_json(state_path(wu_path), {}).get("base_commit", ""))),
        "evidence_refs": args.evidence_ref or [],
        "scope_check": {},
        "risk_check": {},
        "findings": args.finding or [],
        "required_rework": args.required_rework or [],
        "created_at": now_iso()
    }
    write_json(reviews_dir(wu_path) / f"verdict-{review_id}.json", obj)
    next_action = "Archive locally if remaining gates pass; reopen or create a follow-up Work Unit if PR review/merge requires more changes." if args.decision in PASS_DECISIONS else "Address review findings and resubmit."
    update_state(root, wu_path, next_safe_action=next_action)
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    return 0


def check_spec(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    warnings: List[str] = []
    blocking: List[str] = []
    path = contract_path(wu_path)
    if not path.exists():
        return "BLOCK", ["Missing contract.md"], []
    text = path.read_text(encoding="utf-8")
    meta = parse_yaml_header(text)
    state = load_json(state_path(wu_path), {})
    risk = str(meta.get("risk") or state.get("risk") or "low")
    non_trivial = RISK_ORDER.get(risk, 1) >= 1

    required = ["## Intent", "## Expected Outcome", "## Non-goals", "## Scope", "## Required evidence", "## Stop conditions", "## Clarification record", "## Open questions"]
    for heading in required:
        section = get_section_lines(text, heading)
        if not section:
            blocking.append(f"Missing heading: {heading}")
    if meta.get("risk") not in RISK_ORDER:
        blocking.append("Contract risk must be one of trivial, low, medium, high, critical.")
    if "status" in meta:
        blocking.append("Contract header must not contain lifecycle status; state.json is the lifecycle authority.")

    if has_placeholder(text):
        msg = "Contract still contains TBD/TODO placeholders. Replace them before the Work Unit is locked or run."
        if non_trivial:
            blocking.append(msg)
        else:
            warnings.append(msg)

    intent = meaningful_section_lines(text, "## Intent")
    expected = meaningful_section_lines(text, "## Expected Outcome")
    non_goals = meaningful_section_lines(text, "## Non-goals")
    write_boundary = meaningful_bullets_after_subheading(text, "### Write boundary")
    out_of_bounds = meaningful_bullets_after_subheading(text, "### Out of bounds")
    success_conditions = meaningful_bullets_after_subheading(text, "### Success")
    blocked_conditions = meaningful_bullets_after_subheading(text, "### Blocked")
    open_questions = meaningful_section_lines(text, "## Open questions")
    evidence_items = required_evidence_items(wu_path)

    clarify_blocking, clarify_warnings = check_clarification_record(text, non_trivial)
    blocking.extend(clarify_blocking)
    warnings.extend(clarify_warnings)

    required_fields = [
        (intent, "Intent is empty."),
        (expected, "Expected outcome is empty."),
        (non_goals, "Non-goals are empty; use '- none' only for trivial work."),
        (write_boundary, "No concrete write boundary found under Scope."),
        (out_of_bounds, "No concrete out-of-bounds list found under Scope."),
        (success_conditions, "No concrete success stop condition found."),
        (blocked_conditions, "No concrete blocked stop condition found."),
        (evidence_items, "No required evidence IDs found in contract.md."),
    ]
    for values, message in required_fields:
        if not values:
            if non_trivial:
                blocking.append(message)
            else:
                warnings.append(message)

    if open_questions:
        msg = "Open questions must be resolved before the Work Unit can be locked or run: " + "; ".join(open_questions[:3])
        if non_trivial:
            blocking.append(msg)
        else:
            warnings.append(msg)

    context_lines = meaningful_section_lines(text, "## Context pointers")
    if not context_lines:
        warnings.append("No concrete context pointers found. Agent should still read contract.md directly before implementation.")

    if RISK_ORDER.get(risk, 1) >= 3 and not meaningful_section_lines(text, "## Risk notes"):
        blocking.append(f"{risk} risk requires concrete risk notes.")

    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def check_scope(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    text = contract_path(wu_path).read_text(encoding="utf-8") if contract_path(wu_path).exists() else ""
    write_boundary = bullets_after_subheading(text, "### Write boundary")
    out_of_bounds = bullets_after_subheading(text, "### Out of bounds")
    state = load_json(state_path(wu_path), {})
    base_commit = str(state.get("base_commit", ""))
    files = [f for f in work_unit_changed_files(root, base_commit) if not f.startswith(".harness/")]
    blocking: List[str] = []
    warnings: List[str] = []
    for f in files:
        if glob_matches(f, out_of_bounds):
            blocking.append(f"Changed out-of-bounds path: {f}")
        if write_boundary and not glob_matches(f, write_boundary):
            warnings.append(f"Changed path outside write boundary: {f}")
    if not files:
        warnings.append("No Work Unit changed files detected since base commit or in working tree.")
    if warnings and not blocking:
        return "WARN", blocking, warnings
    return ("BLOCK" if blocking else "PASS"), blocking, warnings


def verification_detail_report(root: Path, wu_path: Path) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    details: List[Dict[str, Any]] = []
    state = load_json(state_path(wu_path), {})
    work_unit_id = str(state.get("work_unit_id") or wu_path.name)
    required = required_evidence_items(wu_path)
    if not required:
        blocking.append("No required evidence IDs found in contract.md. Add claim-relative evidence under ## Required evidence.")
        return details, blocking, warnings

    cur_head = head_commit(root)
    risk = str(state.get("risk") or contract_meta(wu_path).get("risk", "low"))
    base_commit = str(state.get("base_commit", ""))
    cur_diff = diff_hash(root, base_commit)
    cur_impl_diff = implementation_diff_hash(root, base_commit)
    scoped_waivers = waivers_by_requirement(wu_path, work_unit_id)

    for item in required:
        ev_id = str(item.get("id", "")).strip()
        detail: Dict[str, Any] = {
            "claim": ev_id,
            "status": "unknown",
            "reason": "",
            "latest_receipt_id": "",
            "requires_rerun": False,
            "equivalence_possible": False,
            "minimal_next_action": "",
        }
        receipt = latest_pass_for_claim(wu_path, work_unit_id, ev_id)
        if receipt is None:
            waivers = scoped_waivers.get(ev_id, [])
            valid_waiver = None
            invalid_reasons: List[str] = []
            for waiver_obj in waivers:
                ok, reason = waiver_is_current(waiver_obj)
                if ok:
                    valid_waiver = waiver_obj
                    break
                invalid_reasons.append(reason)
            if valid_waiver:
                detail.update({
                    "status": "waived",
                    "reason": f"Satisfied by scoped waiver {valid_waiver.get('waiver_id')}",
                    "minimal_next_action": "Confirm waiver risk acceptance remains appropriate before review or archive.",
                })
                warnings.append(f"Required evidence {ev_id} is satisfied by scoped waiver {valid_waiver.get('waiver_id')}; ensure risk acceptance remains appropriate.")
            else:
                reason = f"Required evidence {ev_id} has only invalid waiver(s): {', '.join(invalid_reasons)}." if invalid_reasons else f"Missing fresh pass evidence for required claim {ev_id}."
                detail.update({
                    "status": "missing",
                    "reason": reason,
                    "requires_rerun": True,
                    "minimal_next_action": f"Produce and record a fresh pass receipt for {ev_id}, or create a scoped human-approved waiver if evidence cannot be produced.",
                })
                blocking.append(reason)
            details.append(detail)
            continue

        detail["latest_receipt_id"] = str(receipt.get("receipt_id", ""))
        claim_blocking: List[str] = []
        claim_warnings: List[str] = []
        if receipt.get("result") == "skipped":
            claim_blocking.append(f"Required evidence {ev_id} is skipped; skipped receipts cannot satisfy verification.")

        receipt_impl_diff = str(receipt.get("implementation_diff_hash") or "")
        implementation_equivalent = bool(receipt_impl_diff and receipt_impl_diff == cur_impl_diff)
        context_drift = receipt.get("head_commit") != cur_head or receipt.get("diff_hash") != cur_diff
        # Commit materialization, receipt refresh, and lifecycle-only changes can move
        # HEAD/full diff without changing the implementation surface. In that case,
        # verification should accept documented implementation equivalence as a PASS,
        # not a warning that nudges the agent to rerun evidence.
        lifecycle_only_drift = context_drift and implementation_equivalent
        if context_drift and not implementation_equivalent:
            if receipt.get("head_commit") != cur_head:
                claim_warnings.append(f"Evidence {ev_id} was recorded on a different HEAD. Confirm documented equivalence or rerun.")
            if receipt.get("diff_hash") != cur_diff:
                claim_blocking.append(f"Evidence {ev_id} is stale: current diff hash differs from receipt diff_hash.")

        if not receipt_has_reviewable_support(receipt):
            claim_blocking.append(f"Evidence {ev_id} lacks command, command log, artifact, or manual artifact reference.")
        if RISK_ORDER.get(risk, 1) >= 2 and not (receipt.get("artifact_uri") or receipt.get("command_log_ref") or receipt.get("manual_artifact_ref")):
            claim_blocking.append(f"Evidence {ev_id} for {risk} risk needs command_log_ref, artifact_uri, or manual_artifact_ref; command text alone is not enough.")

        blocking.extend(claim_blocking)
        warnings.extend(claim_warnings)
        if claim_blocking:
            detail.update({
                "status": "stale" if any("stale" in x for x in claim_blocking) else "unsupported",
                "reason": "; ".join(claim_blocking),
                "requires_rerun": any("stale" in x or "skipped" in x for x in claim_blocking),
                "equivalence_possible": lifecycle_only_drift,
                "minimal_next_action": f"Refresh or replace the receipt for {ev_id}; if evidence is impossible, create a scoped human-approved waiver.",
            })
        elif lifecycle_only_drift:
            detail.update({
                "status": "equivalent_pass",
                "reason": "Accepted by implementation-diff equivalence: HEAD/full diff changed, but implementation content for this Work Unit is unchanged.",
                "requires_rerun": False,
                "equivalence_possible": True,
                "minimal_next_action": "No action for this claim; do not rerun evidence solely because HEAD or lifecycle artifacts changed.",
            })
        elif claim_warnings:
            detail.update({
                "status": "warn",
                "reason": "; ".join(claim_warnings),
                "requires_rerun": False,
                "equivalence_possible": False,
                "minimal_next_action": "No automatic rerun required if documented equivalence is available; otherwise rerun targeted evidence.",
            })
        else:
            detail.update({
                "status": "satisfied",
                "reason": "Fresh pass evidence is present and reviewable.",
                "minimal_next_action": "No action for this claim.",
            })
        details.append(detail)

    required_ids = {str(x.get("id", "")).strip() for x in required}
    for receipt in evidence_receipts(wu_path, work_unit_id):
        claim = str(receipt.get("claim_ref", "")).strip()
        if claim and claim not in required_ids:
            warnings.append(f"Receipt {receipt.get('receipt_id')} references non-contract claim {claim}; it does not satisfy completion.")

    return details, blocking, warnings


def check_verification(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    _details, blocking, warnings = verification_detail_report(root, wu_path)
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings

def check_plan_review(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    ok, blocking, warnings = plan_review_passes(root, wu_path)
    state = load_json(state_path(wu_path), {})
    mismatch = lock_mismatch(state, wu_path)
    if mismatch:
        blocking.append(mismatch + "; run harnessctl amend after intentionally changing the locked contract.")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def check_review(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    state = load_json(state_path(wu_path))
    work_unit_id = str(state.get("work_unit_id") or wu_path.name)
    risk = state.get("risk") or contract_meta(wu_path).get("risk", "low")
    all_passes = [v for v in review_verdicts(wu_path) if v.get("decision") in PASS_DECISIONS]
    close_passes = [v for v in all_passes if v.get("mode") == "close"]
    close_verdicts = sorted(close_passes, key=lambda v: (v.get("created_at", ""), v.get("review_id", "")))[-1:]
    latest_close = close_verdicts[-1] if close_verdicts else None

    if RISK_ORDER.get(risk, 1) <= 1:
        if not latest_close:
            warnings.append("Low/trivial risk has no close review. Self-check may be acceptable.")
            return "WARN", [], warnings
    if RISK_ORDER.get(risk, 1) >= 2 and not latest_close:
        blocking.append(f"{risk} risk requires a passing close review verdict.")
        return "BLOCK", blocking, warnings

    base_commit = str(state.get("base_commit", ""))
    cur_head = head_commit(root)
    cur_diff = diff_hash(root, base_commit)
    cur_impl_diff = implementation_diff_hash(root, base_commit)
    current_contract_hash = contract_hash(wu_path)

    close_time = str(latest_close.get("created_at", "")) if latest_close else ""
    supplemental = []
    if latest_close:
        supplemental = [
            v for v in all_passes
            if v.get("mode") in {"close-addendum", "publication"}
            and str(v.get("created_at", "")) >= close_time
        ]
    verdicts = close_verdicts + sorted(supplemental, key=lambda v: (v.get("created_at", ""), v.get("review_id", "")))

    # Review validity is about the judgment surface, not latest receipt ids.
    # The implementation judgment is still valid when the reviewed implementation
    # diff is unchanged and no implementation/scope/risk/success amendment happened.
    reviewed_impl_diff = review_implementation_hash(latest_close, wu_path, work_unit_id) if latest_close else ""
    implementation_changed_since_review = bool(reviewed_impl_diff and reviewed_impl_diff != cur_impl_diff)
    if implementation_changed_since_review:
        blocking.append("Current implementation diff differs from the latest passing close review; run a full close review.")

    amendments_after_close = amendment_impacts_after(wu_path, close_time) if latest_close else []
    judgment_amendments = [a for a in amendments_after_close if amendment_affects_judgment(a)]
    if judgment_amendments:
        impacts = sorted(set(str(a.get("impact") or a.get("field") or "unknown") for a in judgment_amendments))
        blocking.append("Judgment-affecting amendment after latest close review requires renewed review: " + ", ".join(impacts))

    if latest_close and str(latest_close.get("reviewed_contract_hash", "")) != current_contract_hash:
        current_amendments = [a for a in read_jsonl(amendments_path(wu_path)) if a.get("contract_hash") == current_contract_hash]
        if not current_amendments:
            blocking.append("Latest close review was for an older contract and no matching amendment record explains the current contract hash.")
        elif any(amendment_affects_judgment(a) for a in current_amendments):
            impacts = sorted(set(str(a.get("impact") or "judgment") for a in current_amendments if amendment_affects_judgment(a)))
            blocking.append("Latest close review predates judgment-affecting contract amendment(s): " + ", ".join(impacts))
        # Non-judgment amendments are handled by their own surface gates. They do
        # not make the implementation close review stale and should not produce a
        # warning that encourages a redundant addendum.

    if RISK_ORDER.get(risk, 1) >= 3:
        independent = [v for v in verdicts if v.get("mode") == "close" and (v.get("is_independent") or v.get("independence_level") == "human_gate")]
        if not independent:
            blocking.append(f"{risk} risk requires independent close review or human gate.")
    for v in verdicts:
        if v.get("mode") in {"close", "close-addendum"} and v.get("reviewer_role") == v.get("builder_role"):
            blocking.append("Builder-authored close review or close-addendum detected.")

    required = required_evidence_items(wu_path)
    combined_refs: set[str] = set()
    publication_refs: set[str] = set()
    for v in verdicts:
        refs = {str(x).strip() for x in v.get("evidence_refs", []) if str(x).strip()}
        combined_refs.update(refs)
        if v.get("mode") == "publication":
            publication_refs.update(refs)
    if RISK_ORDER.get(risk, 1) >= 2 and not combined_refs:
        blocking.append("Passing close review or supplemental review for medium+ risk must cite an evidence snapshot or receipt ID at least once.")

    current_verification_details, verification_blocking, verification_warnings = verification_detail_report(root, wu_path)
    current_verification = {str(x.get("claim", "")): x for x in current_verification_details}
    if verification_blocking:
        blocking.append("Verification gate is not satisfied; review gate cannot pass until evidence is fresh, equivalent, waived, or explicitly handled.")
        for reason in verification_blocking:
            blocking.append(reason)
    elif verification_warnings:
        for warning in verification_warnings:
            warnings.append(warning)

    cited_by_claim = cited_receipts_by_claim(wu_path, work_unit_id, combined_refs)
    publication_cited_by_claim = cited_receipts_by_claim(wu_path, work_unit_id, publication_refs)

    for item in required:
        ev_id = str(item.get("id", "")).strip()
        receipt = latest_pass_for_claim(wu_path, work_unit_id, ev_id)
        current_status = str(current_verification.get(ev_id, {}).get("status", ""))
        current_satisfied = current_status in {"satisfied", "equivalent_pass", "equivalent_warn", "warn", "waived"}
        if receipt is None:
            if RISK_ORDER.get(risk, 1) >= 2:
                blocking.append(f"No pass receipt exists for required claim {ev_id}.")
            else:
                warnings.append(f"No pass receipt exists for required claim {ev_id}.")
            continue

        if cited_by_claim.get(ev_id):
            # Review validity is surface-based. A close review may cite an earlier
            # receipt for the same claim; current freshness/equivalence is owned by
            # verification_detail_report, not by receipt-id chasing in review gate.
            continue

        # If a claim is publication/collaboration evidence, the publication surface
        # owns it. It should not force implementation close review/addendum.
        surface = receipt_review_surface(receipt)
        if surface == "publication":
            if publication_cited_by_claim.get(ev_id):
                continue
            blocking.append(f"Publication claim {ev_id} has pass evidence but no passing publication review/check cites it.")
            continue

        if current_satisfied:
            # Medium+ close reviews must cite evidence at least once, but they do
            # not need to cite every refreshed receipt or every verification claim.
            # Missing per-claim citations are audit gaps, not judgment invalidation,
            # when implementation/scope/risk/acceptance surfaces are unchanged.
            continue

        if RISK_ORDER.get(risk, 1) >= 2:
            blocking.append(f"Required claim {ev_id} is not currently satisfied by verification.")
        else:
            warnings.append(f"Required claim {ev_id} is not currently satisfied by verification.")

    if not blocking and latest_close and not reviewed_impl_diff:
        warnings.append("Latest close review has no reviewed_implementation_diff_hash; falling back to evidence refs and contract checks.")

    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings

def git_changed_paths(root: Path, base_commit: str = "") -> set[str]:
    paths: set[str] = set()
    queries: List[List[str]] = []
    if base_commit and base_commit not in {"no-git", ""}:
        queries.append(["diff", "--name-only", "--diff-filter=ACDMRTUXB", f"{base_commit}..HEAD"])
    queries.extend((["diff", "--name-only", "--diff-filter=ACDMRTUXB"], ["diff", "--cached", "--name-only", "--diff-filter=ACDMRTUXB"]))
    for args in queries:
        out = run_git(root, args, "")
        paths.update(x.strip() for x in out.splitlines() if x.strip())
    for line in run_git(root, ["status", "--short"], "").splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            old, new = path.split(" -> ", 1)
            paths.add(old.strip())
            paths.add(new.strip())
        else:
            paths.add(path)
    return paths


def changed_file_ref_is_supported(root: Path, ref: str, diff_paths: set[str]) -> bool:
    ref = ref.strip()
    if not ref:
        return True
    if ref.startswith(".harness/work-units/") or ref == ".harness/current":
        return True
    rel = ref.rstrip("/")
    path = root / rel
    if path.exists():
        return True
    if ref.endswith("/"):
        prefix = rel + "/"
        return any(p.startswith(prefix) for p in diff_paths)
    return rel in diff_paths


def handoff_is_generated(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if "Not generated yet" in text or "{{" in text:
        return False
    return bool(text.strip())


def check_archive(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    state = load_json(state_path(wu_path), {})
    risk = str(state.get("risk") or contract_meta(wu_path).get("risk", "low"))
    spec_decision, spec_blocking, spec_warnings = check_spec(root, wu_path)
    blocking.extend([f"spec: {x}" for x in spec_blocking])
    warnings.extend([f"spec: {x}" for x in spec_warnings])
    mismatch = lock_mismatch(state, wu_path)
    if mismatch:
        blocking.append(mismatch + "; archive requires the locked contract hash to match contract.md.")
    for name, func in (("scope", check_scope), ("verification", check_verification), ("review", check_review)):
        decision, b, w = func(root, wu_path)
        blocking.extend([f"{name}: {x}" for x in b])
        warnings.extend([f"{name}: {x}" for x in w])
    handoff = wu_path / "handoff.md"
    no_next_step_reason = str(state.get("no_next_step_reason", "")).strip()
    if not handoff_is_generated(handoff) and not no_next_step_reason:
        msg = "Handoff is missing or not generated. Archive should include handoff or no-next-step reason."
        if RISK_ORDER.get(risk, 1) >= 2:
            blocking.append(msg)
        else:
            warnings.append(msg)

    base_commit = str(state.get("base_commit", ""))
    diff_paths = git_changed_paths(root, base_commit)
    for ref in state.get("changed_files", []):
        ref_s = str(ref).strip()
        if not changed_file_ref_is_supported(root, ref_s, diff_paths):
            blocking.append(f"state.changed_files references an unsupported path: {ref_s}")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


SCHEMA_FILES = {
    "state": "work-unit.schema.json",
    "evidence": "evidence-receipt.schema.json",
    "review": "review-verdict.schema.json",
    "waiver": "waiver.schema.json",
}


def artifact_label(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def schema_for(root: Path, key: str, blocking: List[str]) -> Dict[str, Any]:
    path = root / "harness" / "schemas" / SCHEMA_FILES[key]
    try:
        return load_json(path)
    except HarnessError as exc:
        blocking.append(str(exc))
        return {}


def json_for_validation(path: Path, label: str, blocking: List[str]) -> Optional[Dict[str, Any]]:
    if not path.exists():
        blocking.append(f"{label}: missing JSON artifact")
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        blocking.append(f"{label}: invalid JSON: {exc}")
        return None
    if not isinstance(obj, dict):
        blocking.append(f"{label}: expected JSON object")
        return None
    return obj


def json_type_matches(value: Any, expected: Any) -> bool:
    types = expected if isinstance(expected, list) else [expected]
    for typ in types:
        if typ == "string" and isinstance(value, str):
            return True
        if typ == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if typ == "boolean" and isinstance(value, bool):
            return True
        if typ == "array" and isinstance(value, list):
            return True
        if typ == "object" and isinstance(value, dict):
            return True
        if typ == "null" and value is None:
            return True
    return False


def validate_against_schema(obj: Dict[str, Any], schema: Dict[str, Any], label: str) -> List[str]:
    errors: List[str] = []
    for field in schema.get("required", []):
        if field not in obj:
            errors.append(f"{label}: missing required field {field}")
    properties = schema.get("properties", {})
    for field, spec in properties.items():
        if field not in obj:
            continue
        value = obj[field]
        if "const" in spec and value != spec["const"]:
            errors.append(f"{label}: {field} must be {spec['const']!r}")
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"{label}: {field} must be one of {', '.join(str(x) for x in spec['enum'])}")
        if "type" in spec and not json_type_matches(value, spec["type"]):
            expected = spec["type"] if isinstance(spec["type"], str) else "|".join(spec["type"])
            errors.append(f"{label}: {field} must be {expected}")
    return errors


def read_receipts_for_validation(path: Path, label: str, blocking: List[str]) -> List[Dict[str, Any]]:
    if not path.exists():
        blocking.append(f"{label}: missing receipts.jsonl")
        return []
    rows: List[Dict[str, Any]] = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            blocking.append(f"{label}:{n}: invalid JSONL row: {exc}")
            continue
        if not isinstance(obj, dict):
            blocking.append(f"{label}:{n}: expected JSON object")
            continue
        rows.append(obj)
    return rows


def validate_harness_config(root: Path, blocking: List[str], warnings: List[str]) -> None:
    path = harness_dir(root) / "config.json"
    if not path.exists():
        warnings.append(".harness/config.json is missing. Run `harnessctl init` if this repository uses the harness.")
        return
    obj = json_for_validation(path, ".harness/config.json", blocking)
    if obj is None:
        return
    if obj.get("schema_version") != "harness.config.v1":
        blocking.append(".harness/config.json: schema_version must be 'harness.config.v1'")
    if not isinstance(obj.get("profile"), str) or not obj.get("profile"):
        blocking.append(".harness/config.json: profile must be a non-empty string")


def validate_work_unit(root: Path, work_unit_id: str, wu_path: Path) -> Tuple[List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    if not contract_path(wu_path).exists():
        blocking.append(f"{work_unit_id}/contract.md: missing Work Unit Contract")
    else:
        meta = parse_yaml_header(contract_path(wu_path).read_text(encoding="utf-8"))
        if "status" in meta:
            blocking.append(f"{work_unit_id}/contract.md: contract header must not contain lifecycle status; state.json is the lifecycle authority")

    state_schema = schema_for(root, "state", blocking)
    state_label = artifact_label(root, state_path(wu_path))
    state = json_for_validation(state_path(wu_path), state_label, blocking)
    if state is not None and state_schema:
        blocking.extend(validate_against_schema(state, state_schema, state_label))
        if state.get("work_unit_id") != work_unit_id:
            blocking.append(f"{state_label}: work_unit_id must match directory name {work_unit_id}")

    evidence_schema = schema_for(root, "evidence", blocking)
    receipt_label = artifact_label(root, receipts_path(wu_path))
    receipts = read_receipts_for_validation(receipts_path(wu_path), receipt_label, blocking)
    receipt_ids: set[str] = set()
    for idx, receipt in enumerate(receipts, start=1):
        label = f"{receipt_label}:{idx}"
        if evidence_schema:
            blocking.extend(validate_against_schema(receipt, evidence_schema, label))
        if receipt.get("work_unit_id") != work_unit_id:
            blocking.append(f"{label}: work_unit_id must match {work_unit_id}")
        receipt_id = str(receipt.get("receipt_id", "")).strip()
        if not receipt_id:
            blocking.append(f"{label}: receipt_id must be non-empty")
        elif receipt_id in receipt_ids:
            blocking.append(f"{label}: duplicate receipt_id {receipt_id}")
        else:
            receipt_ids.add(receipt_id)
        if receipt.get("result") == "skipped" and not str(receipt.get("note", "")).strip():
            blocking.append(f"{label}: skipped evidence requires note")

    review_schema = schema_for(root, "review", blocking)
    for path in sorted(reviews_dir(wu_path).glob("verdict-*.json")):
        label = artifact_label(root, path)
        verdict = json_for_validation(path, label, blocking)
        if verdict is None:
            continue
        if review_schema:
            blocking.extend(validate_against_schema(verdict, review_schema, label))
        if verdict.get("work_unit_id") != work_unit_id:
            blocking.append(f"{label}: work_unit_id must match {work_unit_id}")
        for receipt_ref in verdict.get("evidence_refs", []):
            ref = str(receipt_ref).strip()
            if ref and ref not in receipt_ids:
                blocking.append(f"{label}: references missing evidence receipt {ref}")

    waiver_schema = schema_for(root, "waiver", blocking)
    for path in sorted(waivers_dir(wu_path).glob("*.json")):
        label = artifact_label(root, path)
        waiver_obj = json_for_validation(path, label, blocking)
        if waiver_obj is None:
            continue
        if waiver_schema:
            blocking.extend(validate_against_schema(waiver_obj, waiver_schema, label))
        if waiver_obj.get("work_unit_id") != work_unit_id:
            blocking.append(f"{label}: work_unit_id must match {work_unit_id}")
        if not str(waiver_obj.get("approved_by", "")).startswith("human:"):
            blocking.append(f"{label}: approved_by must start with human:")

    return blocking, warnings


def all_work_units(root: Path) -> List[Tuple[str, Path]]:
    out: List[Tuple[str, Path]] = []
    for base in (active_dir(root), archive_dir(root)):
        if not base.exists():
            continue
        for path in sorted(base.iterdir()):
            if path.is_dir():
                out.append((path.name, path))
    return out


def validate(args: argparse.Namespace) -> int:
    root = args.root
    blocking: List[str] = []
    warnings: List[str] = []
    validate_harness_config(root, blocking, warnings)
    if args.all:
        work_units = all_work_units(root)
    else:
        work_unit_id, wu_path = resolve_wu(root, args.id)
        work_units = [(work_unit_id, wu_path)]

    for work_unit_id, wu_path in work_units:
        b, w = validate_work_unit(root, work_unit_id, wu_path)
        blocking.extend(b)
        warnings.extend(w)

    current = current_file(root)
    if args.all and current.exists():
        current_id = current.read_text(encoding="utf-8").strip()
        if current_id and current_id not in {wu_id for wu_id, _ in work_units}:
            blocking.append(f".harness/current references missing Work Unit {current_id}")

    decision = "BLOCK" if blocking else "WARN" if warnings else "PASS"
    out = {
        "schema_version": "harness.validation.v1",
        "scope": "all" if args.all else work_units[0][0],
        "decision": decision,
        "validated_work_units": [wu_id for wu_id, _ in work_units],
        "blocking_reasons": blocking,
        "warnings": warnings,
        "required_next_action": "Fix invalid harness artifacts." if blocking else "Proceed with caution." if warnings else "Validation passed.",
        "created_at": now_iso(),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 2 if decision == "BLOCK" and args.strict else 0


def has_non_harness_work_changes(root: Path, wu_path: Path) -> bool:
    state = load_json(state_path(wu_path), {})
    base_commit = str(state.get("base_commit", ""))
    return bool(implementation_changed_files(root, base_commit))


def ci(args: argparse.Namespace) -> int:
    root = args.root
    blocking: List[str] = []
    warnings: List[str] = []
    validate_harness_config(root, blocking, warnings)
    active_units = [(p.name, p) for p in sorted(active_dir(root).iterdir()) if p.is_dir()] if active_dir(root).exists() else []
    if args.require_active and not active_units:
        blocking.append("CI requires at least one active Work Unit.")

    for work_unit_id, wu_path in active_units:
        b, w = validate_work_unit(root, work_unit_id, wu_path)
        blocking.extend([f"{work_unit_id} validate: {x}" for x in b])
        warnings.extend([f"{work_unit_id} validate: {x}" for x in w])
        if not has_non_harness_work_changes(root, wu_path):
            warnings.append(f"{work_unit_id}: no non-harness repository changes detected; lifecycle gates skipped.")
            continue
        for gate_name, gate_func in (("spec", check_spec), ("scope", check_scope), ("verification", check_verification), ("review", check_review)):
            decision, gate_blocking, gate_warnings = gate_func(root, wu_path)
            blocking.extend([f"{work_unit_id} {gate_name}: {x}" for x in gate_blocking])
            warnings.extend([f"{work_unit_id} {gate_name}: {x}" for x in gate_warnings])

    current = current_file(root)
    if current.exists():
        current_id = current.read_text(encoding="utf-8").strip()
        if current_id and current_id not in {wu_id for wu_id, _ in active_units}:
            blocking.append(f".harness/current references missing active Work Unit {current_id}")

    decision = "BLOCK" if blocking else "WARN" if warnings else "PASS"
    out = {
        "schema_version": "harness.ci_check.v1",
        "decision": decision,
        "checked_work_units": [wu_id for wu_id, _ in active_units],
        "blocking_reasons": blocking,
        "warnings": warnings,
        "required_next_action": "Fix blocking harness lifecycle gates." if blocking else "Proceed with caution." if warnings else "CI harness gate passed.",
        "created_at": now_iso(),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 2 if decision == "BLOCK" and args.strict else 0


def parse_frontmatter(text: str) -> Dict[str, str]:
    if not text.startswith("---"):
        return {}
    try:
        block = text.split("---", 2)[1]
    except IndexError:
        return {}
    out: Dict[str, str] = {}
    for raw in block.splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def check_skills(root: Path) -> Tuple[str, List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    canonical = root / "skills"
    platform_dirs = [root / ".agents" / "skills", root / ".claude" / "skills"]
    skill_dirs = sorted(p for p in canonical.glob("harness-*") if (p / "SKILL.md").exists())
    if not skill_dirs:
        blocking.append("No canonical harness skills found under skills/harness-*/SKILL.md.")
        return "BLOCK", blocking, warnings
    canonical_names = [p.name for p in skill_dirs]
    for platform_dir in platform_dirs:
        names = sorted(p.name for p in platform_dir.glob("harness-*") if (p / "SKILL.md").exists()) if platform_dir.exists() else []
        if names != canonical_names:
            blocking.append(f"Skill mirror mismatch for {platform_dir.relative_to(root)}: expected {canonical_names}, got {names}.")
    required_phrases = {
        "harness-github": ["## Issue body", "## Commit body", "## PR body", "Refs: #", "Closes #"],
        "harness-evidence": ["command_log_ref", "Skipped evidence is never pass evidence", "verification gate"],
        "harness-review": ["Primary inputs", "Builder narrative", "evidence-ref"],
        "harness-tdd": ["RED", "GREEN", "public interface", "One test"],
        "harness-spec": ["write boundary", "required evidence", "stop conditions"],
        "harness-handoff": ["next safe action", "rollback or reopen path"],
    }
    for skill_dir in skill_dirs:
        text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if not fm.get("name") or not fm.get("description"):
            blocking.append(f"{skill_dir.name} missing frontmatter name or description.")
        if fm.get("name") != skill_dir.name:
            blocking.append(f"{skill_dir.name} frontmatter name must match directory name.")
        if len(fm.get("description", "")) > 700:
            warnings.append(f"{skill_dir.name} description is long; broad descriptions increase accidental skill loading.")
        lowered = text.lower()
        for phrase in required_phrases.get(skill_dir.name, []):
            if phrase.lower() not in lowered:
                blocking.append(f"{skill_dir.name} missing required skill content phrase: {phrase}")
        risky_phrases = ["mark complete without", "review is evidence", "skip tests as pass"]
        for phrase in risky_phrases:
            if phrase in lowered:
                blocking.append(f"{skill_dir.name} contains unsafe wording: {phrase}")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def workspace_clean(root: Path) -> bool:
    return run_git(root, ["status", "--short"], "") == ""


def review_required_from_blocking(review_blocking: List[str]) -> Tuple[bool, List[str]]:
    review_reasons: List[str] = []
    for reason in review_blocking:
        lowered = reason.lower()
        if any(token in lowered for token in (
            "current implementation diff differs",
            "judgment-affecting amendment",
            "older contract",
            "requires a passing close review",
            "independent close review",
            "human gate",
            "builder-authored close review",
        )):
            review_reasons.append(reason)
    return bool(review_reasons), review_reasons


def finalize_surfaces(root: Path, wu_path: Path, gate_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    state = load_json(state_path(wu_path), {})
    work_unit_id = str(state.get("work_unit_id") or wu_path.name)
    verdicts = [v for v in review_verdicts(wu_path) if v.get("mode") == "close" and v.get("decision") in PASS_DECISIONS]
    latest_close = sorted(verdicts, key=lambda v: (v.get("created_at", ""), v.get("review_id", "")))[-1] if verdicts else None
    base_commit = str(state.get("base_commit", ""))
    cur_impl = implementation_diff_hash(root, base_commit)
    reviewed_impl = review_implementation_hash(latest_close, wu_path, work_unit_id) if latest_close else ""
    verification_details, _b, _w = verification_detail_report(root, wu_path)
    statuses = [str(d.get("status", "")) for d in verification_details]
    equivalent_claims = [d.get("claim") for d in verification_details if d.get("status") == "equivalent_pass"]
    review_required, review_reasons = review_required_from_blocking(gate_results.get("review", {}).get("blocking_reasons", []))
    publication_required = any("publication claim" in x.lower() for x in gate_results.get("review", {}).get("blocking_reasons", []))
    rerun_evidence_required = any(bool(d.get("requires_rerun")) for d in verification_details)
    if gate_results.get("verification", {}).get("decision") == "PASS" and equivalent_claims:
        evidence_state = "accepted_by_implementation_equivalence"
    elif gate_results.get("verification", {}).get("decision") == "PASS":
        evidence_state = "fresh_pass"
    elif rerun_evidence_required:
        evidence_state = "rerun_required"
    else:
        evidence_state = "blocked_or_warn"
    if latest_close and reviewed_impl and reviewed_impl == cur_impl:
        implementation_state = "unchanged_since_close_review"
    elif latest_close and reviewed_impl:
        implementation_state = "changed_since_close_review"
    elif latest_close:
        implementation_state = "unknown_legacy_review_hash"
    else:
        implementation_state = "no_close_review"
    return {
        "implementation": implementation_state,
        "evidence": evidence_state,
        "review": "review_required" if review_required else "valid_or_not_required",
        "publication": "required" if publication_required else "not_required_or_satisfied",
        "equivalent_evidence_claims": equivalent_claims,
        "review_required": review_required,
        "review_required_reasons": review_reasons,
        "rerun_evidence_required": rerun_evidence_required,
        "statuses": statuses,
    }


def finalize_check(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    validate_blocking, validate_warnings = validate_work_unit(root, work_unit_id, wu_path)
    gate_results: Dict[str, Dict[str, Any]] = {}
    for name, func in (("spec", check_spec), ("scope", check_scope), ("verification", check_verification), ("review", check_review)):
        decision, blocking, warnings = func(root, wu_path)
        gate_results[name] = {"decision": decision, "blocking_reasons": blocking, "warnings": warnings}
    surfaces = finalize_surfaces(root, wu_path, gate_results)
    clean = workspace_clean(root)
    blocking = [f"validate: {x}" for x in validate_blocking]
    warnings = [f"validate: {x}" for x in validate_warnings]
    for name, result in gate_results.items():
        blocking.extend([f"{name}: {x}" for x in result["blocking_reasons"]])
        warnings.extend([f"{name}: {x}" for x in result["warnings"]])
    if not clean:
        warnings.append("workspace has uncommitted changes; archive/integration may still be inappropriate.")
    decision = "BLOCK" if blocking else "WARN" if warnings else "PASS"
    review_required = bool(surfaces["review_required"])
    rerun_evidence_required = bool(surfaces["rerun_evidence_required"])
    do_not_request_review = not review_required
    forbidden_next_actions: List[str] = []
    if do_not_request_review:
        forbidden_next_actions.extend([
            "request close review solely because HEAD changed",
            "request close-addendum solely because evidence receipts were refreshed",
            "request close-addendum for commit materialization when implementation_diff_hash is unchanged",
        ])
    if not rerun_evidence_required:
        forbidden_next_actions.append("rerun evidence solely because HEAD/full diff changed while implementation_diff_hash is unchanged")
    required_next_action = "Fix blocking reasons."
    if not blocking:
        if not clean:
            required_next_action = "Resolve workspace changes, then archive or handoff."
        else:
            required_next_action = "Archive locally or hand off to PR/CI integration surface."
    elif rerun_evidence_required:
        required_next_action = "Refresh only the evidence claims marked requires_rerun=true, then rerun finalize-check."
    elif review_required:
        required_next_action = "Request the minimal review type required by review_required_reasons; do not use review to refresh receipt IDs."
    out = {
        "schema_version": "harness.finalize_check.v1",
        "work_unit_id": work_unit_id,
        "decision": decision,
        "gates": gate_results,
        "surfaces": surfaces,
        "workspace_clean": clean,
        "archive_ready": decision in {"PASS", "WARN"} and clean,
        "review_required": review_required,
        "rerun_evidence_required": rerun_evidence_required,
        "do_not_request_review": do_not_request_review,
        "forbidden_next_actions": forbidden_next_actions,
        "review_guidance": "Do not request close review or close-addendum unless review_required=true and review_required_reasons name a judgment-affecting change." if do_not_request_review else "Review is required because the judgment surface changed; inspect review_required_reasons before selecting full close, addendum, publication, risk, or human gate.",
        "blocking_reasons": blocking,
        "warnings": warnings,
        "required_next_action": required_next_action,
        "created_at": now_iso(),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 2 if decision == "BLOCK" and args.strict else 0


CHECKS = {
    "spec": check_spec,
    "scope": check_scope,
    "verification": check_verification,
    "plan-review": check_plan_review,
    "review": check_review,
    "archive": check_archive,
    "skills": check_skills,
}


def check(args: argparse.Namespace) -> int:
    root = args.root
    func = CHECKS[args.gate]
    if args.gate == "skills":
        work_unit_id = "repo"
        decision, blocking, warnings = check_skills(root)
    else:
        work_unit_id, wu_path = resolve_wu(root, args.id)
        decision, blocking, warnings = func(root, wu_path)
    out = {
        "schema_version": "harness.controller_check.v1",
        "work_unit_id": work_unit_id,
        "check": args.gate,
        "decision": decision,
        "blocking_reasons": blocking,
        "warnings": warnings,
        "missing_evidence": blocking if args.gate == "verification" else [],
        "required_next_action": "Fix blocking reasons." if blocking else "Proceed with caution." if warnings else "Gate passed.",
        "created_at": now_iso()
    }
    if args.gate == "verification":
        details, _b, _w = verification_detail_report(root, wu_path)
        out["evidence_status"] = details
        out["minimal_evidence_plan"] = [d for d in details if d.get("status") not in {"satisfied", "equivalent_pass", "waived"}]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 2 if decision == "BLOCK" and args.strict else 0


def render_list(items: Iterable[str]) -> str:
    vals = list(items)
    if not vals:
        return "- none"
    return "\n".join(f"- {x}" for x in vals)


def handoff(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    state = update_state(root, wu_path, status="handoff", next_safe_action=args.next_safe_action)
    receipts = read_jsonl(receipts_path(wu_path))[-5:]
    evidence_lines = [f"{r.get('receipt_id')} {r.get('result')} {r.get('claim_ref')} {r.get('type')} {r.get('command')}" for r in receipts]
    contract = contract_path(wu_path).read_text(encoding="utf-8") if contract_path(wu_path).exists() else ""
    open_questions = [line.strip("- ") for line in get_section_lines(contract, "## Open questions") if line.strip().startswith("-") and "TBD" not in line]
    template_path = root / "harness" / "templates" / "handoff.md"
    template = template_path.read_text(encoding="utf-8") if template_path.exists() else "# Handoff: {{id}}\n"
    replacements = {
        "{{id}}": work_unit_id,
        "{{objective}}": contract_summary(wu_path, 500),
        "{{status}}": state.get("status", ""),
        "{{branch}}": state.get("branch", ""),
        "{{head_commit}}": state.get("head_commit", ""),
        "{{diff_hash}}": state.get("diff_hash", ""),
        "{{changed_files}}": render_list(state.get("changed_files", [])),
        "{{latest_evidence}}": render_list(evidence_lines),
        "{{known_failures}}": render_list(state.get("known_failures", [])),
        "{{blockers}}": render_list(state.get("blockers", [])),
        "{{open_questions}}": render_list(open_questions),
        "{{next_safe_action}}": args.next_safe_action,
        "{{rollback_or_reopen_path}}": state.get("rollback_or_reopen_path", "")
    }
    text = template
    for key, value in replacements.items():
        text = text.replace(key, str(value))
    (wu_path / "handoff.md").write_text(text, encoding="utf-8")
    print(f"Generated handoff: {wu_path / 'handoff.md'}")
    return 0


def write_archive_closure_handoff(wu_path: Path, work_unit_id: str, reason: str) -> None:
    state = load_json(state_path(wu_path), {})
    receipts = read_jsonl(receipts_path(wu_path))[-5:]
    evidence_lines = [f"{r.get('receipt_id')} {r.get('result')} {r.get('claim_ref')} {r.get('type')} {r.get('command')}" for r in receipts]
    text = f"""# Handoff: {work_unit_id}

## Status

archived

## Closure reason

{reason}

## Objective

{contract_summary(wu_path, 500)}

## Changed files

{render_list(state.get('changed_files', []))}

## Latest evidence

{render_list(evidence_lines)}

## Known failures

{render_list(state.get('known_failures', []))}

## Blockers

{render_list(state.get('blockers', []))}

## Next safe action

No task-local next step. Reopen the Work Unit or create a follow-up Work Unit if further changes are required.

## Rollback or reopen path

{state.get('rollback_or_reopen_path', '')}
"""
    (wu_path / "handoff.md").write_text(text, encoding="utf-8")


def archive(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    if args.no_next_step_reason:
        update_state(root, wu_path, no_next_step_reason=args.no_next_step_reason)
        if not handoff_is_generated(wu_path / "handoff.md"):
            write_archive_closure_handoff(wu_path, work_unit_id, args.no_next_step_reason)
    decision, blocking, warnings = check_archive(root, wu_path)
    if decision == "BLOCK" and not args.force:
        print(json.dumps({"decision": decision, "blocking_reasons": blocking, "warnings": warnings}, ensure_ascii=False, indent=2))
        return 2
    dest = archive_dir(root) / work_unit_id
    if dest.exists():
        raise HarnessError(f"Archive destination exists: {dest}")
    archive_note = "No next step; archived."
    if args.no_next_step_reason:
        archive_note += " " + args.no_next_step_reason
    update_state(root, wu_path, status="archived", next_safe_action=archive_note)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(wu_path), str(dest))
    if current_file(root).exists() and current_file(root).read_text(encoding="utf-8").strip() == work_unit_id:
        current_file(root).unlink()
    print(f"Archived {work_unit_id}: {dest}")
    return 0
    return 0


def doctor(args: argparse.Namespace) -> int:
    root = args.root
    checks = []
    checks.append(("harness directory", harness_dir(root).exists()))
    checks.append(("controller cli", (root / "harness" / "cli" / "harnessctl.py").exists()))
    checks.append(("schemas", (root / "harness" / "schemas" / "evidence-receipt.schema.json").exists()))
    checks.append(("templates", (root / "harness" / "templates" / "work-unit-contract.md").exists()))
    checks.append(("skills", check_skills(root)[0] != "BLOCK"))
    checks.append(("git repository", run_git(root, ["rev-parse", "--is-inside-work-tree"], "false") == "true"))
    for name, ok in checks:
        print(f"{'PASS' if ok else 'WARN'}\t{name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Controller CLI for a coding-agent harness")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root. Defaults to current directory.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.set_defaults(func=init)

    p = sub.add_parser("new")
    p.add_argument("--id", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--type", default="other", choices=["feature", "bugfix", "refactor", "migration", "docs", "test", "release", "security", "research", "other"])
    p.add_argument("--risk", default="low", choices=list(RISK_ORDER.keys()))
    p.set_defaults(func=new)

    p = sub.add_parser("lock")
    p.add_argument("--id")
    p.add_argument("--status", default="ready", choices=["specified", "ready"], help="Lifecycle state to set after spec gate passes.")
    p.set_defaults(func=lock)

    p = sub.add_parser("amend")
    p.add_argument("--id")
    p.add_argument("--field", required=True, choices=["intent", "scope", "required_evidence", "risk", "success", "stop_conditions", "context", "other"])
    p.add_argument("--reason", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--actor", default="human")
    p.add_argument("--review-impact", default="plan", choices=["plan", "none"], help="Backward-compatible flag. Prefer --impact for precise amendment classification.")
    p.add_argument("--impact", choices=sorted(AMENDMENT_IMPACTS.keys()), help="Classify amendment impact so controller can avoid unnecessary plan/evidence/review churn.")
    p.add_argument("--allow-draft", action="store_true", help="Record amendment even when spec gate blocks; leaves Work Unit unlocked in draft.")
    p.set_defaults(func=amend)

    p = sub.add_parser("list")
    p.set_defaults(func=list_wu)

    p = sub.add_parser("status")
    p.add_argument("--id")
    p.set_defaults(func=status)

    p = sub.add_parser("brief")
    p.add_argument("--id")
    p.set_defaults(func=brief)

    p = sub.add_parser("set-state")
    p.add_argument("--id")
    p.add_argument("--status", choices=VALID_STATUSES)
    p.add_argument("--next-safe-action")
    p.set_defaults(func=set_state)

    p = sub.add_parser("evidence")
    p.add_argument("--id")
    p.add_argument("--claim", required=True)
    p.add_argument("--type", default="test")
    p.add_argument("--result", required=True, choices=["pass", "fail", "skipped"])
    p.add_argument("--command", default="")
    p.add_argument("--actor", default="agent", choices=["agent", "controller", "ci", "human", "reviewer"])
    p.add_argument("--exit-code", type=int)
    p.add_argument("--started-at")
    p.add_argument("--ended-at")
    p.add_argument("--base-commit")
    p.add_argument("--last-relevant-change-at")
    p.add_argument("--covers", action="append")
    p.add_argument("--verification-scope", default="files")
    p.add_argument("--freshness-basis")
    p.add_argument("--artifact-uri")
    p.add_argument("--artifact-hash")
    p.add_argument("--command-log-ref")
    p.add_argument("--manual-artifact-ref")
    p.add_argument("--environment-ref")
    p.add_argument("--waiver-ref")
    p.add_argument("--note")
    p.set_defaults(func=evidence)

    p = sub.add_parser("waiver")
    p.add_argument("--id")
    p.add_argument("--waiver-type", default="evidence", choices=["evidence", "risk", "scope", "deadline"])
    p.add_argument("--requested-by", default="agent")
    p.add_argument("--approved-by", required=True)
    p.add_argument("--requirement", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--replacement-evidence", action="append")
    p.add_argument("--risk-accepted", required=True)
    p.add_argument("--expires-at", default="")
    p.set_defaults(func=waiver)

    p = sub.add_parser("request-review")
    p.add_argument("--id")
    p.add_argument("--mode", default="close", choices=REVIEW_MODES)
    p.add_argument("--reviewer-role", default="reviewer-agent")
    p.set_defaults(func=request_review)

    p = sub.add_parser("submit-review")
    p.add_argument("--id")
    p.add_argument("--request-id")
    p.add_argument("--mode", default="close", choices=REVIEW_MODES)
    p.add_argument("--decision", required=True, choices=["PASS", "PASS_WITH_RISK_ACCEPTED", "CHANGES_REQUESTED", "REJECTED", "BLOCKED", "NEEDS_HUMAN_GATE"])
    p.add_argument("--reviewer-role", default="reviewer-agent")
    p.add_argument("--builder-role", default="agent")
    p.add_argument("--independence-level", default="fresh_context", choices=["self_check", "separate_role", "fresh_context", "human_gate"])
    p.add_argument("--evidence-ref", action="append")
    p.add_argument("--finding", action="append")
    p.add_argument("--required-rework", action="append")
    p.set_defaults(func=submit_review)

    p = sub.add_parser("check")
    p.add_argument("--id")
    p.add_argument("--gate", required=True, choices=sorted(CHECKS.keys()))
    p.add_argument("--strict", action="store_true", help="Return exit 2 on BLOCK.")
    p.set_defaults(func=check)

    p = sub.add_parser("validate")
    p.add_argument("--id")
    p.add_argument("--all", action="store_true", help="Validate every active and archived Work Unit.")
    p.add_argument("--strict", action="store_true", help="Return exit 2 on BLOCK.")
    p.set_defaults(func=validate)

    p = sub.add_parser("finalize-check")
    p.add_argument("--id")
    p.add_argument("--strict", action="store_true", help="Return exit 2 on BLOCK.")
    p.set_defaults(func=finalize_check)

    p = sub.add_parser("ci")
    p.add_argument("--strict", action="store_true", help="Return exit 2 on BLOCK.")
    p.add_argument("--require-active", action="store_true", help="Block if no active Work Unit exists.")
    p.set_defaults(func=ci)

    p = sub.add_parser("handoff")
    p.add_argument("--id")
    p.add_argument("--next-safe-action", required=True)
    p.set_defaults(func=handoff)

    p = sub.add_parser("archive")
    p.add_argument("--id")
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-next-step-reason", help="Explicit reason why no handoff is needed before archive.")
    p.set_defaults(func=archive)

    p = sub.add_parser("doctor")
    p.set_defaults(func=doctor)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.root = find_root(args.root)
    try:
        return args.func(args)
    except HarnessError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
