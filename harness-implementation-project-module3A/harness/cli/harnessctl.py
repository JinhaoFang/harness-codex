#!/usr/bin/env python3
"""Deterministic controller for a lightweight coding-agent repository harness.

The controller owns lifecycle transitions, scoped command execution, evidence
freshness, and review lineage. Product judgment remains with users and reviewers.
Tracked intent lives in ``docs/spec``; transient plans and runtime state live in
ignored ``.harness`` storage.
"""
from __future__ import annotations

import argparse
import contextlib
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
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

try:  # POSIX
    import fcntl  # type: ignore
except ImportError:  # pragma: no cover - exercised on Windows
    fcntl = None  # type: ignore

try:  # Windows
    import msvcrt  # type: ignore
except ImportError:  # pragma: no cover - exercised on POSIX
    msvcrt = None  # type: ignore


ROOT_MARKERS = (".git", "pyproject.toml", "AGENTS.md", "CLAUDE.md")
STATE_SCHEMA = "harness.work_unit_state.v2"
EVIDENCE_SCHEMA = "harness.evidence_receipt.v3"
REVIEW_REQUEST_SCHEMA = "harness.review_request.v3"
REVIEW_VERDICT_SCHEMA = "harness.review_verdict.v3"
REVIEW_TRACK_SCHEMA = "harness.review_track.v1"
SPEC_APPROVAL_SCHEMA = "harness.spec_approval.v2"
SPEC_APPROVAL_FIELDS = {"status", "approved_by", "approved_at", "approval_ref", "approved_content_hash"}

VALID_STATUSES = [
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
]
RISK_ORDER = {"trivial": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
PASS_DECISIONS = {"PASS"}
REVIEW_MODES = ("plan", "close")
NON_IMPLEMENTATION_PREFIXES = (".harness/", "docs/spec/")
NON_IMPLEMENTATION_EXACT = {".gitignore"}
WORK_UNIT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class HarnessError(Exception):
    """Expected user-facing controller error."""


def validate_work_unit_id(work_unit_id: str) -> str:
    value = work_unit_id.strip()
    if not WORK_UNIT_ID_RE.fullmatch(value) or value in {".", ".."}:
        raise HarnessError(
            "Work Unit id must be 1-128 characters using only letters, numbers, '.', '_', or '-', "
            "and must not contain path separators."
        )
    return value


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


def run_git(root: Path, args: Sequence[str], default: str = "") -> str:
    try:
        proc = subprocess.run(
            ["git", "--no-pager", *args],
            cwd=root,
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return default
    return proc.stdout.rstrip("\r\n") if proc.returncode == 0 else default


def is_git_repo(root: Path) -> bool:
    return run_git(root, ["rev-parse", "--is-inside-work-tree"], "false") == "true"


def current_branch(root: Path) -> str:
    return run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"], "no-git")


def head_commit(root: Path) -> str:
    return run_git(root, ["rev-parse", "HEAD"], "no-git")


def workspace_id(root: Path) -> str:
    common = run_git(root, ["rev-parse", "--git-common-dir"], "")
    raw = f"{root.resolve()}\0{common}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _status_paths(root: Path) -> List[str]:
    try:
        proc = subprocess.run(
            ["git", "--no-pager", "status", "--short", "--untracked-files=all"],
            cwd=root,
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=15,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    paths: List[str] = []
    for line in proc.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            old, new_path = path.split(" -> ", 1)
            paths.extend([old.strip(), new_path.strip()])
        elif path:
            paths.append(path)
    return paths


def work_unit_changed_files(root: Path, base_commit: str = "") -> List[str]:
    files = set(_status_paths(root))
    if base_commit and base_commit not in {"", "no-git"} and is_git_repo(root):
        out = run_git(root, ["diff", "--name-only", "--diff-filter=ACDMRTUXB", f"{base_commit}..HEAD"], "")
        files.update(line.strip() for line in out.splitlines() if line.strip())
    return sorted(files)


def is_non_implementation_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    return normalized in NON_IMPLEMENTATION_EXACT or any(normalized.startswith(prefix) for prefix in NON_IMPLEMENTATION_PREFIXES)


def implementation_changed_files(root: Path, base_commit: str = "") -> List[str]:
    return [path for path in work_unit_changed_files(root, base_commit) if not is_non_implementation_path(path)]


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


def full_diff_hash(root: Path, base_commit: str = "") -> str:
    h = hashlib.sha256()
    h.update((base_commit or "").encode("utf-8"))
    for rel in work_unit_changed_files(root, base_commit):
        h.update(rel.encode("utf-8"))
        path = root / rel
        h.update(path.read_bytes() if path.is_file() else b"<missing>")
    return h.hexdigest()


def harness_dir(root: Path) -> Path:
    return root / ".harness"


def work_units_dir(root: Path) -> Path:
    return harness_dir(root) / "work-units"


def active_dir(root: Path) -> Path:
    return work_units_dir(root) / "active"


def archive_dir(root: Path) -> Path:
    return work_units_dir(root) / "archive"


def session_id() -> str:
    """Best-effort session namespace for current Work Unit pointers.

    Lifecycle artifacts remain addressable by explicit Work Unit id. The pointer is
    only a convenience and must not let two independent sessions overwrite one
    another when the platform exposes a stable session/thread id.
    """
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


def spec_path_for_id(root: Path, work_unit_id: str) -> Path:
    return root / "docs" / "spec" / f"{validate_work_unit_id(work_unit_id)}.md"


def root_from_wu_path(wu_path: Path) -> Path:
    cur = wu_path.resolve()
    for parent in (cur, *cur.parents):
        if parent.name == ".harness":
            return parent.parent
    raise HarnessError(f"Cannot derive repository root from Work Unit path: {wu_path}")


def spec_path(wu_path: Path) -> Path:
    root = root_from_wu_path(wu_path)
    if state_path(wu_path).exists():
        state = load_json(state_path(wu_path), {})
        rel = str(state.get("spec_path", "")).strip()
        if rel:
            return root / rel
    return spec_path_for_id(root, wu_path.name)


def resolve_wu(root: Path, work_unit_id: Optional[str]) -> Tuple[str, Path]:
    if not work_unit_id:
        cur = current_file(root)
        if cur.exists():
            work_unit_id = cur.read_text(encoding="utf-8").strip()
    if not work_unit_id and active_dir(root).exists():
        candidates = sorted(p.name for p in active_dir(root).iterdir() if p.is_dir())
        if len(candidates) == 1:
            work_unit_id = candidates[0]
    if not work_unit_id:
        raise HarnessError("No Work Unit id supplied and no workspace-local current Work Unit is set.")
    work_unit_id = validate_work_unit_id(work_unit_id)
    active = active_dir(root) / work_unit_id
    if active.exists():
        return work_unit_id, active
    archived = archive_dir(root) / work_unit_id
    if archived.exists():
        return work_unit_id, archived
    raise HarnessError(f"Work Unit not found: {work_unit_id}")


def ensure_gitignore_entry(root: Path, entry: str) -> None:
    path = root / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = [line.strip() for line in text.splitlines()]
    if entry in lines or entry.rstrip("/") in lines:
        return
    prefix = "" if not text or text.endswith("\n") else "\n"
    path.write_text(text + prefix + entry + "\n", encoding="utf-8")


@contextlib.contextmanager
def exclusive_file_lock(lock_path: Path) -> Iterator[None]:
    """Small cross-platform advisory lock for controller-owned local files."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + 5.0
    with lock_path.open("a+b") as fh:
        while True:
            try:
                if fcntl is not None:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                elif msvcrt is not None:  # pragma: no cover - Windows
                    fh.seek(0)
                    if fh.tell() == 0:
                        fh.write(b"0")
                        fh.flush()
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except (BlockingIOError, OSError):
                if time.monotonic() >= deadline:
                    raise HarnessError(f"Timed out waiting for controller lock: {lock_path}")
                time.sleep(0.02)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            elif msvcrt is not None:  # pragma: no cover - Windows
                fh.seek(0)
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        if default is not None:
            return default
        raise HarnessError(f"Missing JSON file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HarnessError(f"Invalid JSON in {path}: {exc}") from exc


def write_json(path: Path, obj: Any) -> None:
    with exclusive_file_lock(path.with_suffix(path.suffix + ".lock")):
        atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with exclusive_file_lock(path.with_suffix(path.suffix + ".lock")):
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise HarnessError(f"Invalid JSONL in {path}:{index}: {exc}") from exc
        if not isinstance(obj, dict):
            raise HarnessError(f"Invalid JSONL object in {path}:{index}")
        rows.append(obj)
    return rows


def file_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _spec_without_approval_metadata(text: str) -> str:
    lines = text.splitlines(keepends=True)
    in_yaml = False
    seen_yaml = False
    output: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not seen_yaml and re.fullmatch(r"```ya?ml", stripped, flags=re.IGNORECASE):
            in_yaml = True
            seen_yaml = True
            output.append(line)
            continue
        if in_yaml and stripped == "```":
            in_yaml = False
            output.append(line)
            continue
        if in_yaml and ":" in line:
            key = line.split(":", 1)[0].strip()
            if key in SPEC_APPROVAL_FIELDS:
                continue
        output.append(line)
    return "".join(output)


def spec_content_hash(path: Path) -> str:
    if not path.exists():
        return ""
    normalized = _spec_without_approval_metadata(path.read_text(encoding="utf-8"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def update_spec_approval_metadata(path: Path, values: Dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```ya?ml\s*\n(.*?)\n```", text, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        raise HarnessError(f"Tracked spec has no YAML metadata block: {path}")
    body_lines: List[str] = []
    for raw in match.group(1).splitlines():
        if ":" in raw and raw.split(":", 1)[0].strip() in SPEC_APPROVAL_FIELDS:
            continue
        body_lines.append(raw)
    for key in ("status", "approved_by", "approved_at", "approval_ref", "approved_content_hash"):
        if key in values:
            escaped = str(values[key]).replace('"', '\\"')
            body_lines.append(f'{key}: "{escaped}"')
    new_body = "\n".join(body_lines)
    atomic_write_text(path, text[: match.start(1)] + new_body + text[match.end(1) :])


def update_state(root: Path, wu_path: Path, **patch: Any) -> Dict[str, Any]:
    path = state_path(wu_path)
    with exclusive_file_lock(path.with_suffix(".json.lock")):
        state = load_json(path, {})
        base = str(state.get("base_commit", ""))
        state.update(patch)
        state.update(
            {
                "branch": current_branch(root),
                "worktree": str(root.resolve()),
                "workspace_id": workspace_id(root),
                "head_commit": head_commit(root),
                "changed_files": work_unit_changed_files(root, base),
                "implementation_changed_files": implementation_changed_files(root, base),
                "diff_hash": full_diff_hash(root, base),
                "implementation_diff_hash": implementation_diff_hash(root, base),
                "updated_at": now_iso(),
            }
        )
        atomic_write_text(path, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    return state


def parse_yaml_header(text: str) -> Dict[str, str]:
    match = re.search(r"```ya?ml\s*\n(.*?)\n```", text, flags=re.DOTALL | re.IGNORECASE)
    if not match:
        return {}
    result: Dict[str, str] = {}
    for raw in match.group(1).splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def section_lines(text: str, heading: str) -> List[str]:
    lines = text.splitlines()
    start = None
    level = len(heading) - len(heading.lstrip("#"))
    normalized = heading.strip().lower()
    for index, line in enumerate(lines):
        if line.strip().lower() == normalized:
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


def has_heading(text: str, heading: str) -> bool:
    return any(line.strip().lower() == heading.lower() for line in text.splitlines())


def clean_scalar(value: str) -> str:
    return value.strip().strip('"').strip("'").strip()


def section_key_values(text: str, heading: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for raw in section_lines(text, heading):
        stripped = raw.strip()
        if stripped.startswith("-"):
            stripped = stripped[1:].strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        values[key.strip().lower().replace("-", "_").replace(" ", "_")] = clean_scalar(value)
    return values


def bullets_after_subheading(text: str, subheading: str) -> List[str]:
    lines = section_lines(text, subheading)
    values: List[str] = []
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("- "):
            value = clean_scalar(stripped[2:])
            if value:
                values.append(value)
    return values


def is_empty_marker(value: str) -> bool:
    return clean_scalar(value).lower() in {"", "none", "n/a", "not applicable", "无", "无。", "- none"}


def has_placeholder(text: str) -> bool:
    return bool(re.search(r"\bTBD\b|\{\{[^}]+\}\}|\[在此处|TODO:", text, flags=re.IGNORECASE))


def required_evidence_items(wu_path: Path) -> List[Dict[str, str]]:
    path = spec_path(wu_path)
    if not path.exists():
        return []
    lines = section_lines(path.read_text(encoding="utf-8"), "## Required evidence")
    items: List[Dict[str, str]] = []
    current: Optional[Dict[str, str]] = None
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("- id:"):
            if current:
                items.append(current)
            current = {"id": clean_scalar(stripped.split(":", 1)[1])}
        elif current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = clean_scalar(value)
    if current:
        items.append(current)
    return [item for item in items if item.get("id") and item.get("id", "").upper() != "TBD"]


def scope_patterns(wu_path: Path) -> Tuple[List[str], List[str]]:
    text = spec_path(wu_path).read_text(encoding="utf-8")
    allowed = [x for x in bullets_after_subheading(text, "### Write boundary") if not is_empty_marker(x)]
    forbidden = [x for x in bullets_after_subheading(text, "### Out of bounds") if not is_empty_marker(x)]
    return allowed, forbidden


def glob_matches(path: str, patterns: Iterable[str]) -> bool:
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        pat = pattern.replace("\\", "/").strip()
        if pat.endswith("/**") and (normalized == pat[:-3] or normalized.startswith(pat[:-2])):
            return True
        if fnmatch.fnmatch(normalized, pat):
            return True
    return False


def spec_summary(wu_path: Path, max_chars: int = 700) -> str:
    path = spec_path(wu_path)
    if not path.exists():
        return "Missing tracked spec."
    text = path.read_text(encoding="utf-8")
    chunks: List[str] = []
    for heading in ("## Intent", "## Expected Outcome", "## Non-goals"):
        body = "\n".join(line for line in section_lines(text, heading) if line.strip()).strip()
        if body:
            chunks.append(f"{heading}\n{body}")
    result = "\n\n".join(chunks)
    return result[:max_chars] + ("…" if len(result) > max_chars else "")


def check_spec_document(path: Path, expected_id: Optional[str] = None, *, allow_approval_mismatch: bool = False) -> Tuple[List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    if not path.exists():
        return [f"Missing tracked spec: {path}"], warnings
    text = path.read_text(encoding="utf-8")
    meta = parse_yaml_header(text)
    for key in ("id", "title", "type", "risk"):
        if not meta.get(key):
            blocking.append(f"Spec YAML header is missing {key}.")
    if expected_id and meta.get("id") != expected_id:
        blocking.append(f"Spec id {meta.get('id')!r} does not match Work Unit {expected_id!r}.")
    if meta.get("risk") not in RISK_ORDER:
        blocking.append(f"Invalid risk: {meta.get('risk')!r}.")
    approval_status = meta.get("status", "draft").lower()
    if approval_status not in {"draft", "approved"}:
        blocking.append(f"Invalid spec status: {approval_status!r}.")
    if approval_status == "approved":
        if not meta.get("approved_by"):
            blocking.append("Approved spec is missing approved_by metadata.")
        elif not meta.get("approved_by", "").startswith("human:"):
            blocking.append("Approved spec approved_by must use a human:<identity> value.")
        if not meta.get("approved_at"):
            blocking.append("Approved spec is missing approved_at metadata.")
        if not meta.get("approval_ref"):
            blocking.append("Approved spec is missing approval_ref metadata.")
        marker = meta.get("approved_content_hash", "")
        if not marker:
            blocking.append("Approved spec is missing approved_content_hash metadata.")
        elif marker != spec_content_hash(path) and not allow_approval_mismatch:
            blocking.append("Approved spec content changed after approval; reapprove or record a material amendment.")
    headings = [
        "## Intent",
        "## Expected Outcome",
        "## Non-goals",
        "## Scope",
        "## Required evidence",
        "## Stop conditions",
        "## Clarification record",
        "## Open questions",
        "## Context pointers",
    ]
    for heading in headings:
        if not has_heading(text, heading):
            blocking.append(f"Missing heading: {heading}")
    if has_placeholder(text):
        blocking.append("Spec contains unresolved placeholder text.")
    for heading in ("## Intent", "## Expected Outcome", "## Non-goals", "## Context pointers"):
        body = [line.strip() for line in section_lines(text, heading) if line.strip() and not line.strip().startswith("#")]
        if not body or all(is_empty_marker(line.lstrip("- ")) for line in body):
            blocking.append(f"{heading} must contain a concrete value.")
    allowed = bullets_after_subheading(text, "### Write boundary")
    forbidden = bullets_after_subheading(text, "### Out of bounds")
    if not allowed or all(is_empty_marker(x) for x in allowed):
        blocking.append("Write boundary must contain at least one concrete pattern.")
    if not forbidden:
        blocking.append("Out of bounds must be explicit; use `- none` only when deliberately empty.")
    items = []
    lines = section_lines(text, "## Required evidence")
    current: Optional[Dict[str, str]] = None
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("- id:"):
            if current:
                items.append(current)
            current = {"id": clean_scalar(stripped.split(":", 1)[1])}
        elif current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key.strip()] = clean_scalar(value)
    if current:
        items.append(current)
    if not items:
        blocking.append("Required evidence must contain at least one claim.")
    seen: set[str] = set()
    for item in items:
        ev_id = item.get("id", "")
        if not ev_id or ev_id.upper() == "TBD":
            blocking.append("Required evidence item is missing a concrete id.")
        elif ev_id in seen:
            blocking.append(f"Duplicate required evidence id: {ev_id}")
        seen.add(ev_id)
        if not item.get("claim"):
            blocking.append(f"Required evidence {ev_id or '<unknown>'} is missing claim.")
        command = item.get("command", "")
        if not command:
            blocking.append(f"Required evidence {ev_id or '<unknown>'} is missing command.")
        else:
            try:
                argv = shlex.split(command)
            except ValueError as exc:
                blocking.append(f"Required evidence {ev_id or '<unknown>'} command is not parseable: {exc}")
            else:
                if not argv:
                    blocking.append(f"Required evidence {ev_id or '<unknown>'} command resolves to an empty argv.")
    values = section_key_values(text, "## Clarification record")
    if values.get("user_confirmed", "").lower() not in {"yes", "true", "confirmed", "是"}:
        blocking.append("Clarification record must set user_confirmed: yes.")
    if values.get("repo_grounded", "").lower() not in {"yes", "true", "confirmed", "是"}:
        blocking.append("Clarification record must set repo_grounded: yes.")
    if not values.get("key_decisions") or is_empty_marker(values.get("key_decisions", "")):
        blocking.append("Clarification record must capture key_decisions.")
    assumptions = values.get("remaining_assumptions", "")
    if not assumptions:
        blocking.append("Clarification record must capture remaining_assumptions.")
    elif not (
        is_empty_marker(assumptions)
        or assumptions.lower().startswith(("resolved", "accepted:", "accepted ", "no material", "no remaining"))
    ):
        blocking.append("Remaining assumptions must be resolved or explicitly accepted before approval.")
    open_questions = bullets_after_subheading(text, "## Open questions")
    if any(not is_empty_marker(x) for x in open_questions):
        blocking.append("Open questions remain; resolve them before approving the spec.")
    success = bullets_after_subheading(text, "### Success")
    blocked = bullets_after_subheading(text, "### Blocked")
    if not success or all(is_empty_marker(x) for x in success):
        blocking.append("Stop conditions must define concrete success conditions.")
    if not blocked:
        blocking.append("Stop conditions must define blocked conditions.")
    return blocking, warnings


def check_spec(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    blocking, warnings = check_spec_document(spec_path(wu_path), wu_path.name)
    state = load_json(state_path(wu_path), {})
    approved_hash = str(state.get("spec_approved_hash", ""))
    if state.get("status") not in {"clarifying", "blocked"} and approved_hash and approved_hash != spec_content_hash(spec_path(wu_path)):
        blocking.append("Tracked spec changed after approval. Run `harnessctl amend` or approve it again before continuing.")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def check_plan(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    path = plan_path(wu_path)
    if not path.exists():
        return "BLOCK", ["Missing local technical plan: plan.md"], warnings
    text = path.read_text(encoding="utf-8")
    for heading in (
        "## Repository grounding",
        "## Architecture and tradeoffs",
        "## Change map",
        "## TDD behavior slices",
        "## Verification",
        "## Risks and replan conditions",
        "## Reviewer focus",
    ):
        if not has_heading(text, heading):
            blocking.append(f"Missing plan heading: {heading}")
    if has_placeholder(text):
        blocking.append("Plan contains unresolved placeholder text.")
    state = load_json(state_path(wu_path), {})
    risk = str(state.get("risk", "low"))
    if RISK_ORDER.get(risk, 1) >= 2:
        behavior_lines = [line.strip() for line in section_lines(text, "## TDD behavior slices")]
        if not any(line.startswith("- id:") for line in behavior_lines):
            blocking.append("Medium+ plan must define at least one TDD behavior slice with `- id:`.")
        lower = "\n".join(behavior_lines).lower()
        for field in ("claim_ref:", "red_command:", "expected_red_reason:", "green_command:"):
            if field not in lower:
                blocking.append(f"Medium+ TDD plan is missing {field}")
    if not any(line.strip() for line in section_lines(text, "## Architecture and tradeoffs")):
        blocking.append("Plan must explain architecture and tradeoffs.")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def check_scope(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    state = load_json(state_path(wu_path), {})
    base = str(state.get("base_commit", ""))
    allowed, forbidden = scope_patterns(wu_path)
    for rel in implementation_changed_files(root, base):
        if forbidden and glob_matches(rel, forbidden):
            blocking.append(f"Out-of-bounds implementation change: {rel}")
        elif allowed and not glob_matches(rel, allowed):
            blocking.append(f"Implementation change is outside write boundary: {rel}")
    if not implementation_changed_files(root, base):
        warnings.append("No implementation changes detected relative to Work Unit base commit.")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def evidence_receipts(wu_path: Path) -> List[Dict[str, Any]]:
    return [row for row in read_jsonl(receipts_path(wu_path)) if row.get("work_unit_id") == wu_path.name]


def latest_final_for_claim(wu_path: Path, claim_ref: str) -> Optional[Dict[str, Any]]:
    """Return the newest final observation for a claim, regardless of result."""
    rows = [
        row
        for row in evidence_receipts(wu_path)
        if row.get("claim_ref") == claim_ref
        and row.get("phase") == "final"
    ]
    return sorted(rows, key=lambda row: (row.get("ended_at", ""), row.get("receipt_id", "")))[-1] if rows else None


def latest_pass_for_claim(wu_path: Path, claim_ref: str) -> Optional[Dict[str, Any]]:
    """Return the newest final observation only when it is an acceptance-grade pass."""
    receipt = latest_final_for_claim(wu_path, claim_ref)
    return receipt if receipt and receipt.get("result") == "pass" else None


def verification_detail_report(root: Path, wu_path: Path) -> Tuple[List[Dict[str, Any]], List[str], List[str]]:
    state = load_json(state_path(wu_path), {})
    current_impl_hash = implementation_diff_hash(root, str(state.get("base_commit", "")))
    current_spec_hash = str(state.get("spec_approved_hash", ""))
    current_plan_hash = str(state.get("plan_approved_hash", ""))
    required = required_evidence_items(wu_path)
    details: List[Dict[str, Any]] = []
    blocking: List[str] = []
    warnings: List[str] = []
    required_ids = {item["id"] for item in required}
    for item in required:
        ev_id = item["id"]
        latest_final = latest_final_for_claim(wu_path, ev_id)
        receipt = latest_final if latest_final and latest_final.get("result") == "pass" else None
        if latest_final is None:
            status = "missing"
            reason = f"Missing controller-observed pass evidence for required claim {ev_id}."
            blocking.append(reason)
        elif latest_final.get("result") == "skipped":
            status = "skipped"
            reason = f"Latest final observation for {ev_id} was skipped and does not satisfy the evidence contract."
            blocking.append(reason)
        elif latest_final.get("result") != "pass":
            status = "failed"
            reason = f"Latest final observation for {ev_id} failed."
            blocking.append(reason)
        elif receipt.get("observation") != "controller_executed_command":
            status = "untrusted"
            reason = f"Latest pass for {ev_id} was not produced by controller execution."
            blocking.append(reason)
        elif receipt.get("spec_hash") != current_spec_hash:
            status = "stale"
            reason = f"Evidence for {ev_id} targets a different approved spec revision."
            blocking.append(reason)
        elif receipt.get("plan_hash") != current_plan_hash:
            status = "stale"
            reason = f"Evidence for {ev_id} targets a different approved technical plan."
            blocking.append(reason)
        elif receipt.get("workspace_id") != workspace_id(root):
            status = "stale"
            reason = f"Evidence for {ev_id} was produced in a different workspace/worktree."
            blocking.append(reason)
        elif receipt.get("implementation_diff_hash") != current_impl_hash:
            status = "stale"
            reason = f"Evidence for {ev_id} is stale because implementation content changed after verification."
            blocking.append(reason)
        elif list(receipt.get("argv", [])) != shlex.split(item.get("command", "")):
            status = "invalid"
            reason = f"Evidence for {ev_id} did not execute the command declared by the approved spec."
            blocking.append(reason)
        elif not receipt.get("command_log_ref") or not (root / str(receipt.get("command_log_ref"))).is_file():
            status = "invalid"
            reason = f"Evidence for {ev_id} has no readable controller command log."
            blocking.append(reason)
        elif receipt.get("command_log_hash") != file_hash(root / str(receipt.get("command_log_ref"))):
            status = "invalid"
            reason = f"Evidence for {ev_id} command log was modified after receipt creation."
            blocking.append(reason)
        else:
            status = "satisfied"
            reason = ""
        details.append(
            {
                "claim": ev_id,
                "status": status,
                "receipt_id": latest_final.get("receipt_id") if latest_final else None,
                "requires_rerun": status != "satisfied",
                "reason": reason,
                "minimal_next_action": f"Run `harnessctl verify --id {wu_path.name} --claim {ev_id}`" if status != "satisfied" else "none",
            }
        )
    for receipt in evidence_receipts(wu_path):
        claim = str(receipt.get("claim_ref", ""))
        if claim and claim not in required_ids and receipt.get("result") == "pass":
            warnings.append(f"Pass receipt {receipt.get('receipt_id')} references non-spec claim {claim}.")
    return details, blocking, warnings


def check_verification(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    _details, blocking, warnings = verification_detail_report(root, wu_path)
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def review_requests(wu_path: Path) -> List[Dict[str, Any]]:
    return [load_json(path, {}) for path in sorted(review_requests_dir(wu_path).glob("*.json"))]


def review_verdicts(wu_path: Path) -> List[Dict[str, Any]]:
    return [load_json(path, {}) for path in sorted(review_verdicts_dir(wu_path).glob("*.json"))]


def latest_review_request(wu_path: Path, mode: str, pending_only: bool = False) -> Optional[Dict[str, Any]]:
    verdict_request_ids = {str(v.get("request_id", "")) for v in review_verdicts(wu_path)}
    rows = [row for row in review_requests(wu_path) if row.get("mode") == mode]
    if pending_only:
        rows = [row for row in rows if row.get("request_id") not in verdict_request_ids]
    return sorted(rows, key=lambda row: (row.get("created_at", ""), row.get("request_id", "")))[-1] if rows else None


def latest_passing_verdict(wu_path: Path, mode: str) -> Optional[Dict[str, Any]]:
    rows = [row for row in review_verdicts(wu_path) if row.get("mode") == mode and row.get("decision") in PASS_DECISIONS]
    return sorted(rows, key=lambda row: (row.get("created_at", ""), row.get("review_id", "")))[-1] if rows else None


def review_independence_errors(verdict: Dict[str, Any]) -> List[str]:
    """Validate the controller-observable part of review independence.

    This does not pretend to prove a person's identity. It makes the recorded
    capability boundary internally consistent and requires an auditable
    reference whenever a verdict claims a human gate.
    """
    errors: List[str] = []
    level = str(verdict.get("independence_level", ""))
    reviewer_id = str(verdict.get("reviewer_id", ""))
    reviewer_session = str(verdict.get("reviewer_session_id", ""))
    mode = str(verdict.get("mode", ""))
    if mode == "plan":
        subject_label = "planner"
        subject_id = str(verdict.get("planner_id", ""))
        subject_session = str(verdict.get("planner_session_id", ""))
    else:
        subject_label = "builder"
        subject_id = str(verdict.get("builder_id", ""))
        subject_session = str(verdict.get("builder_session_id", ""))
    if level == "human_gate":
        if not reviewer_id.startswith("human:"):
            errors.append("Human-gate review does not use a human:<identity> reviewer.")
        if not verdict.get("approval_ref"):
            errors.append("Human-gate review is missing approval_ref.")
    elif verdict.get("is_independent"):
        if not reviewer_id or not subject_id or reviewer_id == subject_id:
            errors.append(f"Independent {mode} review does not have a reviewer identity separate from the {subject_label}.")
        if not reviewer_session or not subject_session or reviewer_session == subject_session:
            errors.append(f"Independent {mode} review does not have an observable session boundary from the {subject_label}.")
    return errors


def check_plan_review(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    state = load_json(state_path(wu_path), {})
    risk = str(state.get("risk", "low"))
    verdict = latest_passing_verdict(wu_path, "plan")
    if verdict is None:
        blocking.append(f"{risk} risk requires a passing plan review before implementation.")
    else:
        blocking.extend(review_independence_errors(verdict))
        if verdict.get("review_track_id") != state.get("review_track_id"):
            blocking.append("Plan review does not belong to the active review track.")
        if verdict.get("reviewed_spec_hash") != state.get("spec_approved_hash"):
            blocking.append("Plan review does not cover the currently approved spec revision.")
        if verdict.get("reviewed_plan_hash") != file_hash(plan_path(wu_path)):
            blocking.append("Plan changed after plan review; request review again.")
        if state.get("plan_approved_hash") != file_hash(plan_path(wu_path)):
            blocking.append("Current plan is not approved in controller state.")
        if RISK_ORDER.get(risk, 1) >= 1 and not verdict.get("is_independent"):
            blocking.append(f"{risk} risk requires a reviewer identity/session separate from the planner or a human gate.")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def check_review(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    state = load_json(state_path(wu_path), {})
    risk = str(state.get("risk", "low"))
    if RISK_ORDER.get(risk, 1) == 0 and not latest_passing_verdict(wu_path, "close"):
        warnings.append("Trivial risk has no close review; self-check may be acceptable.")
        return "WARN", blocking, warnings
    verdict = latest_passing_verdict(wu_path, "close")
    if verdict is None:
        blocking.append(f"{risk} risk requires a passing close review.")
        return "BLOCK", blocking, warnings
    blocking.extend(review_independence_errors(verdict))
    if verdict.get("review_track_id") != state.get("review_track_id"):
        blocking.append("Close review does not belong to the plan review track.")
    track = load_json(review_track_path(wu_path), {})
    if verdict.get("reviewer_id") != track.get("reviewer_id"):
        blocking.append("Close review was not performed by the reviewer identity that owns the plan review track.")
    if verdict.get("reviewed_spec_hash") != state.get("spec_approved_hash"):
        blocking.append("Close review does not cover the currently approved spec revision.")
    if verdict.get("reviewed_plan_hash") != state.get("plan_approved_hash"):
        blocking.append("Close review does not cover the approved technical plan.")
    current_impl = implementation_diff_hash(root, str(state.get("base_commit", "")))
    if verdict.get("reviewed_implementation_diff_hash") != current_impl:
        blocking.append("Implementation changed after close review.")
    verification_decision, verification_blocking, verification_warnings = check_verification(root, wu_path)
    if verification_decision == "BLOCK":
        blocking.append("Verification gate is not satisfied.")
        blocking.extend(verification_blocking)
    warnings.extend(verification_warnings)
    current_receipts = {
        str(latest_pass_for_claim(wu_path, item["id"]).get("receipt_id"))
        for item in required_evidence_items(wu_path)
        if latest_pass_for_claim(wu_path, item["id"])
    }
    cited = {str(x) for x in verdict.get("evidence_refs", [])}
    if RISK_ORDER.get(risk, 1) >= 2 and not current_receipts.intersection(cited):
        blocking.append("Medium+ close review must cite at least one current evidence receipt.")
    if verdict.get("reviewer_id") == state.get("builder_id"):
        blocking.append("Builder cannot author the close review verdict.")
    if state.get("builder_session_id") and verdict.get("reviewer_session_id") == state.get("builder_session_id"):
        blocking.append("Close reviewer used the builder session; review is not independent.")
    if RISK_ORDER.get(risk, 1) >= 1 and not verdict.get("is_independent"):
        blocking.append(f"{risk} risk requires a reviewer identity/session separate from the builder or a human gate.")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def check_archive(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    for name, func in (
        ("spec", check_spec),
        ("scope", check_scope),
        ("verification", check_verification),
        ("review", check_review),
    ):
        _decision, reasons, warns = func(root, wu_path)
        blocking.extend(f"{name}: {reason}" for reason in reasons)
        warnings.extend(f"{name}: {warning}" for warning in warns)
    state = load_json(state_path(wu_path), {})
    handoff = wu_path / "handoff.md"
    if not handoff.exists() and not str(state.get("no_next_step_reason", "")).strip():
        blocking.append("Archive requires a generated handoff or an explicit no-next-step reason.")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def init(args: argparse.Namespace) -> int:
    root = args.root
    for path in (active_dir(root), archive_dir(root), runtime_dir(root), harness_dir(root) / "tmp"):
        path.mkdir(parents=True, exist_ok=True)
    (root / "docs" / "spec").mkdir(parents=True, exist_ok=True)
    ensure_gitignore_entry(root, ".harness/")
    config = harness_dir(root) / "config.json"
    if not config.exists():
        write_json(
            config,
            {
                "schema_version": "harness.config.v2",
                "profile": getattr(args, "profile", "codex"),
                "created_at": now_iso(),
                "tracked_specs_dir": "docs/spec",
                "runtime_dir": ".harness",
                "default_required_gates": ["spec", "plan", "verification"],
            },
        )
    if not getattr(args, "quiet", False):
        print(f"Initialized local harness runtime at {harness_dir(root)}")
    return 0


def _create_runtime_work_unit(
    root: Path,
    work_unit_id: str,
    risk: str,
    *,
    recovered_meta: Optional[Dict[str, str]] = None,
) -> Path:
    wu_path = active_dir(root) / work_unit_id
    if wu_path.exists():
        raise HarnessError(f"Work Unit already exists: {work_unit_id}")
    for path in (evidence_artifacts_dir(wu_path), review_requests_dir(wu_path), review_verdicts_dir(wu_path)):
        path.mkdir(parents=True, exist_ok=True)
    base = head_commit(root)
    spec_rel = spec_path_for_id(root, work_unit_id).relative_to(root).as_posix()
    recovered = recovered_meta is not None
    state = {
        "schema_version": STATE_SCHEMA,
        "work_unit_id": work_unit_id,
        "status": "spec_approved" if recovered else "clarifying",
        "risk": risk,
        "spec_path": spec_rel,
        "plan_path": f".harness/work-units/active/{work_unit_id}/plan.md",
        "spec_approved_hash": spec_content_hash(spec_path_for_id(root, work_unit_id)) if recovered else "",
        "spec_approved_at": str((recovered_meta or {}).get("approved_at", "")),
        "spec_approved_by": str((recovered_meta or {}).get("approved_by", "")),
        "spec_approval_ref": str((recovered_meta or {}).get("approval_ref", "")),
        "plan_approved_hash": "",
        "review_track_id": "",
        "builder_id": "",
        "builder_session_id": "",
        "branch": current_branch(root),
        "worktree": str(root.resolve()),
        "workspace_id": workspace_id(root),
        "base_commit": base,
        "head_commit": base,
        "changed_files": work_unit_changed_files(root, base),
        "implementation_changed_files": implementation_changed_files(root, base),
        "diff_hash": full_diff_hash(root, base),
        "implementation_diff_hash": implementation_diff_hash(root, base),
        "latest_evidence_refs": [],
        "known_failures": [],
        "blockers": [],
        "next_safe_action": "Rebuild and review a technical plan from the tracked spec and current repository." if recovered else "Clarify intent and complete the tracked spec.",
        "rollback_or_reopen_path": "Reopen this Work Unit or revert the branch before integration.",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    write_json(state_path(wu_path), state)
    receipts_path(wu_path).touch()
    amendments_path(wu_path).touch()
    current_file(root).parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(current_file(root), work_unit_id + "\n")
    return wu_path


def new(args: argparse.Namespace) -> int:
    root = args.root
    init(argparse.Namespace(root=root, profile=getattr(args, "profile", "codex"), quiet=True))
    preexisting = [path for path in _status_paths(root) if not is_non_implementation_path(path)]
    if preexisting:
        raise HarnessError(
            "A new Work Unit requires a clean implementation worktree. "
            "Commit or stash existing changes first; after first-time initialization, commit the adoption/.gitignore change. "
            f"Existing paths: {', '.join(preexisting)}"
        )
    tracked_spec = spec_path_for_id(root, args.id)
    if tracked_spec.exists():
        raise HarnessError(f"Tracked spec already exists: {tracked_spec}. Use `harnessctl resume --id {args.id}`.")
    template = root / "harness" / "templates" / "feature-spec.md"
    text = template.read_text(encoding="utf-8") if template.exists() else "# Feature Spec: {{id}}\n"
    text = text.replace("{{id}}", args.id).replace("{{title}}", args.title).replace("{{type}}", args.type).replace("{{risk}}", args.risk)
    tracked_spec.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(tracked_spec, text)
    wu_path = _create_runtime_work_unit(root, args.id, args.risk)
    plan_template = root / "harness" / "templates" / "technical-plan.md"
    plan_text = plan_template.read_text(encoding="utf-8") if plan_template.exists() else "# Technical Plan: {{id}}\n\nTBD\n"
    atomic_write_text(plan_path(wu_path), plan_text.replace("{{id}}", args.id).replace("{{title}}", args.title))
    print(json.dumps({"work_unit_id": args.id, "spec": str(tracked_spec.relative_to(root)), "runtime": str(wu_path.relative_to(root)), "status": "clarifying"}, ensure_ascii=False, indent=2))
    return 0


def resume(args: argparse.Namespace) -> int:
    root = args.root
    init(argparse.Namespace(root=root, profile=getattr(args, "profile", "codex"), quiet=True))
    tracked_spec = spec_path_for_id(root, args.id)
    if not tracked_spec.exists():
        raise HarnessError(f"Tracked spec not found: {tracked_spec}")
    if (active_dir(root) / args.id).exists():
        wu_path = active_dir(root) / args.id
        current_file(root).parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(current_file(root), args.id + "\n")
        state = update_state(root, wu_path)
        next_action = state.get("next_safe_action", "Read the tracked spec and current repository.")
        if state.get("status") in {"handoff", "blocked"}:
            next_action = f"{next_action} Then run `harnessctl resume-work` with a fresh worker session when it is safe to continue."
        print(json.dumps({"work_unit_id": args.id, "status": state.get("status"), "required_next_action": next_action}, ensure_ascii=False, indent=2))
        return 0
    meta = parse_yaml_header(tracked_spec.read_text(encoding="utf-8"))
    risk = str(meta.get("risk", "low"))
    if risk not in RISK_ORDER:
        risk = "low"
    recovered_approved = (
        meta.get("status", "").lower() == "approved"
        and meta.get("approved_by", "").startswith("human:")
        and bool(meta.get("approved_at"))
        and bool(meta.get("approval_ref"))
        and meta.get("approved_content_hash") == spec_content_hash(tracked_spec)
    )
    wu_path = _create_runtime_work_unit(root, args.id, risk, recovered_meta=meta if recovered_approved else None)
    plan_template = root / "harness" / "templates" / "technical-plan.md"
    text = plan_template.read_text(encoding="utf-8") if plan_template.exists() else "# Technical Plan: {{id}}\n\nTBD\n"
    atomic_write_text(plan_path(wu_path), text.replace("{{id}}", args.id).replace("{{title}}", meta.get("title", args.id)))
    recovered_status = "spec_approved" if recovered_approved else "clarifying"
    next_action = "Rebuild and review the technical plan; prior local evidence and review are not assumed." if recovered_approved else "Review and approve the tracked draft spec before planning."
    print(json.dumps({"work_unit_id": args.id, "status": recovered_status, "recovered_from": [str(tracked_spec.relative_to(root)), "git", "current codebase"], "required_next_action": next_action}, ensure_ascii=False, indent=2))
    return 0


def list_wu(args: argparse.Namespace) -> int:
    for label, base in (("active", active_dir(args.root)), ("archive", archive_dir(args.root))):
        if not base.exists():
            continue
        for path in sorted(p for p in base.iterdir() if p.is_dir()):
            state = load_json(state_path(path), {})
            print(f"{label}\t{path.name}\t{state.get('status', 'unknown')}\t{state.get('spec_path', '')}")
    return 0


def status(args: argparse.Namespace) -> int:
    _, wu_path = resolve_wu(args.root, args.id)
    state = update_state(args.root, wu_path)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def brief(args: argparse.Namespace) -> int:
    work_unit_id, wu_path = resolve_wu(args.root, args.id)
    state = update_state(args.root, wu_path)
    print(f"# Harness Brief: {work_unit_id}\n")
    print(f"- tracked spec: {state.get('spec_path')}\n- local plan: {state.get('plan_path')}\n- status: {state.get('status')}\n- branch: {state.get('branch')}\n- head: {state.get('head_commit')}\n- next safe action: {state.get('next_safe_action')}\n")
    print("## Spec summary\n")
    print(spec_summary(wu_path))
    print("\n## Evidence\n")
    rows = evidence_receipts(wu_path)[-5:]
    print("\n".join(f"- {row.get('receipt_id')} {row.get('result')} {row.get('claim_ref')} {row.get('command')}" for row in rows) or "- none")
    track = load_json(review_track_path(wu_path), {}) if review_track_path(wu_path).exists() else {}
    print("\n## Review track\n")
    print(json.dumps(track or {"status": "none"}, ensure_ascii=False, indent=2))
    return 0


def approve_spec(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    state_before = load_json(state_path(wu_path), {})
    if state_before.get("spec_approved_hash"):
        raise HarnessError("Spec already has an approved revision. Use `harnessctl amend` for subsequent changes.")
    if state_before.get("status") not in {"clarifying", "blocked"}:
        raise HarnessError("Initial spec approval is only valid during clarification. Use the amendment flow after approval.")
    if not args.approval_ref:
        raise HarnessError("Spec approval requires --approval-ref so the user decision is recoverable outside chat memory.")
    blocking, warnings = check_spec_document(spec_path(wu_path), work_unit_id, allow_approval_mismatch=True)
    if blocking:
        raise HarnessError("Cannot approve spec: " + "; ".join(blocking))
    approved_by = args.approved_by or os.environ.get("HARNESS_HUMAN_ID", "")
    if not approved_by:
        raise HarnessError("Spec approval requires --approved-by or HARNESS_HUMAN_ID.")
    if not approved_by.startswith("human:"):
        raise HarnessError("Spec approver must use a human:<identity> value.")
    approved_at = now_iso()
    content_hash = spec_content_hash(spec_path(wu_path))
    update_spec_approval_metadata(
        spec_path(wu_path),
        {
            "status": "approved",
            "approved_by": approved_by,
            "approved_at": approved_at,
            "approval_ref": args.approval_ref or "",
            "approved_content_hash": content_hash,
        },
    )
    approval = {
        "schema_version": SPEC_APPROVAL_SCHEMA,
        "work_unit_id": work_unit_id,
        "spec_path": str(spec_path(wu_path).relative_to(root)),
        "spec_hash": content_hash,
        "approved_by": approved_by,
        "approval_ref": args.approval_ref or "",
        "identity_source": "environment" if os.environ.get("HARNESS_HUMAN_ID") == approved_by else "cli_attestation",
        "created_at": approved_at,
    }
    write_json(wu_path / "spec-approval.json", approval)
    state = update_state(
        root,
        wu_path,
        status="spec_approved",
        spec_approved_hash=approval["spec_hash"],
        spec_approved_at=approval["created_at"],
        spec_approved_by=approved_by,
        spec_approval_ref=approval["approval_ref"],
        plan_approved_hash="",
        next_safe_action="Complete the local technical plan, then request plan review.",
    )
    print(json.dumps({"decision": "APPROVED", "approval": approval, "status": state["status"], "warnings": warnings}, ensure_ascii=False, indent=2))
    return 0


def amend(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    if not args.approval_ref:
        raise HarnessError("Spec amendment requires --approval-ref for the approving human decision.")
    blocking, warnings = check_spec_document(spec_path(wu_path), work_unit_id, allow_approval_mismatch=True)
    if blocking:
        raise HarnessError("Cannot record spec amendment while spec is invalid: " + "; ".join(blocking))
    state = load_json(state_path(wu_path), {})
    old_hash = str(state.get("spec_approved_hash", ""))
    new_hash = spec_content_hash(spec_path(wu_path))
    if old_hash == new_hash:
        raise HarnessError("Spec hash did not change; no amendment is needed.")
    actor = args.actor or os.environ.get("HARNESS_HUMAN_ID", "human:unknown")
    if not actor.startswith("human:"):
        raise HarnessError("Spec amendment approval requires a human:<identity> actor.")
    approved_at = now_iso()
    update_spec_approval_metadata(
        spec_path(wu_path),
        {
            "status": "approved",
            "approved_by": actor,
            "approved_at": approved_at,
            "approval_ref": args.approval_ref or "",
            "approved_content_hash": new_hash,
        },
    )
    record = {
        "schema_version": "harness.spec_amendment.v2",
        "amendment_id": "amend-" + uuid.uuid4().hex[:10],
        "work_unit_id": work_unit_id,
        "impact": "material",
        "reason": args.reason,
        "summary": args.summary,
        "actor": actor,
        "previous_spec_hash": old_hash,
        "spec_hash": new_hash,
        "approval_ref": args.approval_ref or "",
        "created_at": approved_at,
    }
    append_jsonl(amendments_path(wu_path), record)
    patch: Dict[str, Any] = {
        "spec_approved_hash": new_hash,
        "spec_approved_at": record["created_at"],
        "spec_approved_by": actor,
        "spec_approval_ref": record["approval_ref"],
        "last_amendment_id": record["amendment_id"],
        "status": "spec_approved",
        "plan_approved_hash": "",
        "plan_review_approved_spec_hash": "",
        "plan_review_id": "",
        "close_review_id": "",
        "latest_evidence_refs": [],
        "next_safe_action": "Update the technical plan and rerun plan review because the approved spec changed.",
    }
    update_state(root, wu_path, **patch)
    print(json.dumps({"decision": "RECORDED", "amendment": record, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 0


def ensure_exclusive_implementation_worktree(root: Path, work_unit_id: str) -> None:
    active_states = {"running", "verifying", "reviewing"}
    this_workspace = workspace_id(root)
    if not active_dir(root).exists():
        return
    for other_state_path in active_dir(root).glob("*/state.json"):
        other = load_json(other_state_path, {})
        if other.get("work_unit_id") == work_unit_id:
            continue
        if other.get("workspace_id") == this_workspace and other.get("status") in active_states:
            raise HarnessError(
                f"Workspace already has active implementation Work Unit {other.get('work_unit_id')}; "
                "use a separate Git worktree for parallel implementation."
            )


def start_work(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    state = load_json(state_path(wu_path), {})
    if state.get("status") != "ready":
        raise HarnessError("Work Unit is not ready. Approve the spec and pass required plan review first.")
    decision, blocking, _warnings = check_plan_review(root, wu_path)
    if decision == "BLOCK":
        raise HarnessError("Plan review gate blocks implementation: " + "; ".join(blocking))
    ensure_exclusive_implementation_worktree(root, work_unit_id)
    builder_id = args.builder_id or os.environ.get("HARNESS_ACTOR_ID", "")
    builder_session = args.builder_session or os.environ.get("HARNESS_SESSION_ID", "")
    if not builder_id:
        raise HarnessError("start-work requires --builder-id or HARNESS_ACTOR_ID.")
    if not builder_session:
        raise HarnessError("start-work requires --builder-session or HARNESS_SESSION_ID for worker/reviewer separation.")
    track = load_json(review_track_path(wu_path), {}) if review_track_path(wu_path).exists() else {}
    if track and builder_id == track.get("reviewer_id"):
        raise HarnessError("Worker identity must differ from the plan/close reviewer identity.")
    if builder_session and builder_session in set(track.get("reviewer_sessions", [])):
        raise HarnessError("Worker session must differ from reviewer sessions.")
    if state.get("planner_id") and builder_id == state.get("planner_id"):
        raise HarnessError("Worker identity must differ from the planner identity.")
    if state.get("planner_session_id") and builder_session == state.get("planner_session_id"):
        raise HarnessError("Worker session must differ from the planner session.")
    state = update_state(
        root,
        wu_path,
        status="running",
        builder_id=builder_id,
        builder_session_id=builder_session,
        next_safe_action="Implement the approved plan inside the spec write boundary using behavior-first TDD.",
    )
    print(json.dumps({"work_unit_id": work_unit_id, "status": state["status"], "builder_id": builder_id, "builder_session_id": builder_session}, ensure_ascii=False, indent=2))
    return 0


def resume_work(args: argparse.Namespace) -> int:
    """Resume implementation after a local handoff or an explicit blocker clears.

    This is intentionally narrower than a generic state setter: the approved spec
    and plan review must still be current, and a new worker session is bound before
    product writes are enabled again.
    """
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    state = load_json(state_path(wu_path), {})
    if state.get("status") not in {"handoff", "blocked"}:
        raise HarnessError("resume-work is only valid from handoff or blocked state.")
    spec_decision, spec_blocking, _spec_warnings = check_spec(root, wu_path)
    if spec_decision == "BLOCK":
        raise HarnessError("Spec gate blocks resumption: " + "; ".join(spec_blocking))
    plan_decision, plan_blocking, _plan_warnings = check_plan_review(root, wu_path)
    if plan_decision == "BLOCK":
        raise HarnessError("Plan review gate blocks resumption: " + "; ".join(plan_blocking))
    ensure_exclusive_implementation_worktree(root, work_unit_id)
    builder_id = args.builder_id or os.environ.get("HARNESS_ACTOR_ID", "") or str(state.get("builder_id", ""))
    builder_session = args.builder_session or os.environ.get("HARNESS_SESSION_ID", "")
    if not builder_id:
        raise HarnessError("resume-work requires --builder-id or HARNESS_ACTOR_ID.")
    if not builder_session:
        raise HarnessError("resume-work requires a fresh --builder-session or HARNESS_SESSION_ID.")
    if builder_session == state.get("builder_session_id"):
        raise HarnessError("resume-work requires a new worker session, not the session recorded before handoff/blocking.")
    track = load_json(review_track_path(wu_path), {}) if review_track_path(wu_path).exists() else {}
    if track and builder_id == track.get("reviewer_id"):
        raise HarnessError("Worker identity must differ from the plan/close reviewer identity.")
    if builder_session in set(track.get("reviewer_sessions", [])):
        raise HarnessError("Worker session must differ from reviewer sessions.")
    if state.get("planner_id") and builder_id == state.get("planner_id"):
        raise HarnessError("Worker identity must differ from the planner identity.")
    if state.get("planner_session_id") and builder_session == state.get("planner_session_id"):
        raise HarnessError("Worker session must differ from the planner session.")
    update_state(
        root,
        wu_path,
        status="running",
        builder_id=builder_id,
        builder_session_id=builder_session,
        blockers=[],
        resume_status="",
        next_safe_action="Continue the approved plan, rerun affected evidence, and request close review when ready.",
    )
    print(json.dumps({"work_unit_id": work_unit_id, "status": "running", "builder_id": builder_id, "builder_session_id": builder_session}, ensure_ascii=False, indent=2))
    return 0



def verify(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    spec_decision, spec_blocking, _spec_warnings = check_spec(root, wu_path)
    if spec_decision == "BLOCK":
        raise HarnessError("Spec gate blocks verification: " + "; ".join(spec_blocking))
    plan_decision, plan_blocking, _plan_warnings = check_plan_review(root, wu_path)
    if plan_decision == "BLOCK":
        raise HarnessError("Plan review gate blocks verification: " + "; ".join(plan_blocking))
    required = {item["id"]: item for item in required_evidence_items(wu_path)}
    if args.claim not in required:
        raise HarnessError(f"Unknown required evidence claim {args.claim!r}; expected one of {sorted(required)}")
    command = list(args.command or [])
    if command and command[0] == "--":
        command = command[1:]
    specified_command = shlex.split(required[args.claim].get("command", ""))
    if args.phase == "final":
        if args.expect != "pass":
            raise HarnessError("Final verification must expect a passing command; expected failures belong to the RED phase.")
        if not specified_command:
            raise HarnessError(f"Required evidence {args.claim} has no executable command in the tracked spec.")
        if not command:
            command = specified_command
        elif command != specified_command:
            raise HarnessError(
                "Final verification command must exactly match the approved spec command. "
                f"Expected: {shlex.join(specified_command)}"
            )
    elif not command:
        raise HarnessError("RED/GREEN verification requires a command after `--`.")
    state = load_json(state_path(wu_path), {})
    if state.get("status") not in {"running", "verifying", "reviewing"}:
        raise HarnessError("Command verification is only available after implementation has started.")
    started = now_iso()
    start_monotonic = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            check=False,
            timeout=args.timeout,
        )
        exit_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except FileNotFoundError as exc:
        exit_code = 127
        stdout = ""
        stderr = str(exc)
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = ((exc.stderr or "") if isinstance(exc.stderr, str) else "") + f"\nTimed out after {args.timeout}s."
    ended = now_iso()
    expected_met = (exit_code == 0) if args.expect == "pass" else (exit_code != 0)
    result = "pass" if expected_met else "fail"
    receipt_id = "ev-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
    base = str(state.get("base_commit", ""))
    log_path = evidence_artifacts_dir(wu_path) / f"{receipt_id}.log"
    header = {
        "receipt_id": receipt_id,
        "work_unit_id": work_unit_id,
        "claim_ref": args.claim,
        "phase": args.phase,
        "expected_outcome": args.expect,
        "exit_code": exit_code,
        "started_at": started,
        "ended_at": ended,
        "duration_seconds": round(time.monotonic() - start_monotonic, 6),
        "command": command,
    }
    atomic_write_text(log_path, json.dumps(header, ensure_ascii=False, indent=2) + "\n\n--- stdout ---\n" + stdout + "\n--- stderr ---\n" + stderr + "\n")
    command_log_hash = file_hash(log_path)
    receipt = {
        "schema_version": EVIDENCE_SCHEMA,
        "receipt_id": receipt_id,
        "work_unit_id": work_unit_id,
        "claim_ref": args.claim,
        "actor": "controller",
        "observation": "controller_executed_command",
        "type": args.type,
        "phase": args.phase,
        "command": shlex.join(command),
        "argv": command,
        "expected_outcome": args.expect,
        "observed_outcome": "exit_zero" if exit_code == 0 else "exit_nonzero",
        "result": result,
        "started_at": started,
        "ended_at": ended,
        "duration_seconds": round(time.monotonic() - start_monotonic, 6),
        "exit_code": exit_code,
        "base_commit": base,
        "head_commit": head_commit(root),
        "branch": current_branch(root),
        "workspace_id": workspace_id(root),
        "spec_hash": str(state.get("spec_approved_hash", "")),
        "plan_hash": str(state.get("plan_approved_hash", "")),
        "diff_hash": full_diff_hash(root, base),
        "implementation_diff_hash": implementation_diff_hash(root, base),
        "changed_files": work_unit_changed_files(root, base),
        "implementation_changed_files": implementation_changed_files(root, base),
        "verification_scope": args.verification_scope,
        "freshness_basis": "controller_executed_command",
        "command_log_ref": log_path.relative_to(root).as_posix(),
        "command_log_hash": command_log_hash,
        "environment_ref": args.environment_ref or "local",
        "note": args.note or "",
    }
    append_jsonl(receipts_path(wu_path), receipt)
    latest = list(load_json(state_path(wu_path), {}).get("latest_evidence_refs", []))
    failures = list(load_json(state_path(wu_path), {}).get("known_failures", []))
    if result == "pass" and args.phase == "final":
        latest = [rid for rid in latest if rid != receipt_id] + [receipt_id]
    else:
        failures.append(f"{args.claim}: {receipt_id} expected {args.expect}, observed exit {exit_code}")
    update_state(root, wu_path, status="verifying", latest_evidence_refs=latest[-20:], known_failures=failures[-20:], next_safe_action="Fix failed verification." if result == "fail" else "Run remaining required evidence, then request close review.")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if expected_met else 2


def record_skipped(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    required_ids = {item["id"] for item in required_evidence_items(wu_path)}
    if args.claim not in required_ids:
        raise HarnessError(f"Unknown required evidence claim {args.claim!r}.")
    state = load_json(state_path(wu_path), {})
    if state.get("status") not in {"running", "verifying", "reviewing"}:
        raise HarnessError("Skipped verification can only be recorded after implementation has started.")
    receipt = {
        "schema_version": EVIDENCE_SCHEMA,
        "receipt_id": "ev-" + uuid.uuid4().hex[:12],
        "work_unit_id": work_unit_id,
        "claim_ref": args.claim,
        "actor": args.actor,
        "observation": "skipped_not_evidence",
        "type": args.type,
        "phase": "final",
        "command": "",
        "argv": [],
        "expected_outcome": "pass",
        "observed_outcome": "not_run",
        "result": "skipped",
        "started_at": now_iso(),
        "ended_at": now_iso(),
        "exit_code": None,
        "base_commit": str(state.get("base_commit", "")),
        "head_commit": head_commit(root),
        "branch": current_branch(root),
        "workspace_id": workspace_id(root),
        "spec_hash": str(state.get("spec_approved_hash", "")),
        "plan_hash": str(state.get("plan_approved_hash", "")),
        "diff_hash": full_diff_hash(root, str(state.get("base_commit", ""))),
        "implementation_diff_hash": implementation_diff_hash(root, str(state.get("base_commit", ""))),
        "changed_files": work_unit_changed_files(root, str(state.get("base_commit", ""))),
        "implementation_changed_files": implementation_changed_files(root, str(state.get("base_commit", ""))),
        "verification_scope": args.verification_scope,
        "freshness_basis": "not_applicable",
        "command_log_ref": "",
        "command_log_hash": "",
        "environment_ref": args.environment_ref or "local",
        "note": f"reason={args.reason}; replacement={args.replacement}; risk_impact={args.risk_impact}; owner={args.owner}",
    }
    append_jsonl(receipts_path(wu_path), receipt)
    update_state(root, wu_path, status="blocked", blockers=[f"Required evidence {args.claim} was skipped: {args.reason}"], next_safe_action="Produce the required evidence, revise and reapprove the spec, or leave the Work Unit blocked.")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


def _identity(explicit: str, env_name: str, fallback: str = "") -> Tuple[str, str]:
    env_value = os.environ.get(env_name, "")
    if env_value:
        return env_value, f"environment:{env_name}"
    if explicit:
        return explicit, "cli_attestation"
    return fallback, "default"


def request_review(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    state = load_json(state_path(wu_path), {})
    mode = args.mode
    if mode == "plan":
        if state.get("status") not in {"spec_approved", "planning", "plan_reviewing"}:
            raise HarnessError("Plan review can only be requested after spec approval and before implementation.")
        decision, blocking, _warnings = check_plan(root, wu_path)
        if decision == "BLOCK":
            raise HarnessError("Plan gate blocks review request: " + "; ".join(blocking))
        reviewer_id, identity_source = _identity(args.reviewer_id, "HARNESS_REVIEWER_ID")
        if not reviewer_id:
            raise HarnessError("First plan review request requires --reviewer-id or HARNESS_REVIEWER_ID.")
        reviewer_session, session_source = _identity(args.reviewer_session, "HARNESS_REVIEWER_SESSION")
        planner_id, planner_identity_source = _identity(args.planner_id, "HARNESS_ACTOR_ID")
        planner_session, planner_session_source = _identity(args.planner_session, "HARNESS_SESSION_ID")
        if (
            RISK_ORDER.get(str(state.get("risk", "low")), 1) >= 1
            and not reviewer_session
            and not reviewer_id.startswith("human:")
        ):
            raise HarnessError("Low+ plan review requires --reviewer-session or HARNESS_REVIEWER_SESSION.")
        if RISK_ORDER.get(str(state.get("risk", "low")), 1) >= 1 and not reviewer_id.startswith("human:"):
            if not planner_id or not planner_session:
                raise HarnessError(
                    "Low+ plan review requires planner identity/session via --planner-id/--planner-session "
                    "or HARNESS_ACTOR_ID/HARNESS_SESSION_ID."
                )
            if reviewer_id == planner_id or reviewer_session == planner_session:
                raise HarnessError("Plan reviewer identity and session must be separate from the planner.")
        track = load_json(review_track_path(wu_path), {}) if review_track_path(wu_path).exists() else {}
        if not track:
            track = {
                "schema_version": REVIEW_TRACK_SCHEMA,
                "review_track_id": "rt-" + uuid.uuid4().hex[:12],
                "work_unit_id": work_unit_id,
                "reviewer_id": reviewer_id,
                "reviewer_identity_source": identity_source,
                "reviewer_sessions": [reviewer_session] if reviewer_session else [],
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
        elif track.get("reviewer_id") != reviewer_id:
            raise HarnessError("Plan review track already belongs to another reviewer identity.")
    else:
        planner_id = str(state.get("planner_id", ""))
        planner_identity_source = str(state.get("planner_identity_source", "state"))
        planner_session = str(state.get("planner_session_id", ""))
        planner_session_source = str(state.get("planner_session_source", "state"))
        plan_verdict = latest_passing_verdict(wu_path, "plan")
        if RISK_ORDER.get(str(state.get("risk", "low")), 1) >= 1 and plan_verdict is None:
            raise HarnessError("Close review requires the existing passing plan review track.")
        if state.get("status") not in {"running", "verifying", "reviewing"}:
            raise HarnessError("Close review can only be requested after implementation has started and before integration.")
        scope_decision, scope_blocking, _scope_warnings = check_scope(root, wu_path)
        if scope_decision == "BLOCK":
            raise HarnessError("Scope gate blocks close review: " + "; ".join(scope_blocking))
        verification_decision, verification_blocking, _verification_warnings = check_verification(root, wu_path)
        if verification_decision == "BLOCK":
            raise HarnessError("Verification gate blocks close review: " + "; ".join(verification_blocking))
        track = load_json(review_track_path(wu_path), {})
        if not track:
            reviewer_id, identity_source = _identity(args.reviewer_id, "HARNESS_REVIEWER_ID")
            if not reviewer_id:
                raise HarnessError("Close review requires --reviewer-id when no plan review track exists.")
            reviewer_session, session_source = _identity(args.reviewer_session, "HARNESS_REVIEWER_SESSION")
            track = {
                "schema_version": REVIEW_TRACK_SCHEMA,
                "review_track_id": "rt-" + uuid.uuid4().hex[:12],
                "work_unit_id": work_unit_id,
                "reviewer_id": reviewer_id,
                "reviewer_identity_source": identity_source,
                "reviewer_sessions": [reviewer_session] if reviewer_session else [],
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
        else:
            supplied, _source = _identity(args.reviewer_id, "HARNESS_REVIEWER_ID", str(track.get("reviewer_id", "")))
            if supplied != track.get("reviewer_id"):
                raise HarnessError("Close review must reuse the reviewer identity from the plan review track.")
            reviewer_id = str(track.get("reviewer_id", ""))
            identity_source = str(track.get("reviewer_identity_source", "track"))
            reviewer_session, session_source = _identity(args.reviewer_session, "HARNESS_REVIEWER_SESSION")
        if (
            RISK_ORDER.get(str(state.get("risk", "low")), 1) >= 1
            and not reviewer_session
            and not reviewer_id.startswith("human:")
        ):
            raise HarnessError("Low+ close review requires --reviewer-session or HARNESS_REVIEWER_SESSION.")
        if reviewer_session and reviewer_session == state.get("builder_session_id"):
            raise HarnessError("Close reviewer session must be separate from the builder session.")
    sessions = list(track.get("reviewer_sessions", []))
    if reviewer_session and reviewer_session not in sessions:
        sessions.append(reviewer_session)
    track["reviewer_sessions"] = sessions
    track["updated_at"] = now_iso()
    write_json(review_track_path(wu_path), track)
    request_id = "rr-" + uuid.uuid4().hex[:12]
    request = {
        "schema_version": REVIEW_REQUEST_SCHEMA,
        "request_id": request_id,
        "review_track_id": track["review_track_id"],
        "work_unit_id": work_unit_id,
        "mode": mode,
        "reviewer_id": track["reviewer_id"],
        "reviewer_identity_source": identity_source,
        "reviewer_session_id": reviewer_session,
        "reviewer_session_source": session_source,
        "planner_id": planner_id,
        "planner_identity_source": planner_identity_source,
        "planner_session_id": planner_session,
        "planner_session_source": planner_session_source,
        "builder_id": state.get("builder_id", ""),
        "builder_session_id": state.get("builder_session_id", ""),
        "spec_path": state.get("spec_path"),
        "reviewed_spec_hash": state.get("spec_approved_hash"),
        "plan_path": state.get("plan_path"),
        "reviewed_plan_hash": file_hash(plan_path(wu_path)),
        "base_commit": state.get("base_commit"),
        "head_commit": head_commit(root),
        "reviewed_implementation_diff_hash": implementation_diff_hash(root, str(state.get("base_commit", ""))),
        "evidence_refs": [
            receipt["receipt_id"]
            for item in required_evidence_items(wu_path)
            for receipt in [latest_pass_for_claim(wu_path, item["id"])]
            if receipt is not None
        ],
        "prior_plan_findings": latest_passing_verdict(wu_path, "plan").get("findings", []) if mode == "close" and latest_passing_verdict(wu_path, "plan") else [],
        "created_at": now_iso(),
    }
    write_json(review_requests_dir(wu_path) / f"{request_id}.json", request)
    state_patch: Dict[str, Any] = {
        "status": "plan_reviewing" if mode == "plan" else "reviewing",
        "review_track_id": track["review_track_id"],
        "next_safe_action": f"Wait for {mode} reviewer verdict on request {request_id}.",
    }
    if mode == "plan":
        state_patch.update(
            {
                "planner_id": planner_id,
                "planner_identity_source": planner_identity_source,
                "planner_session_id": planner_session,
                "planner_session_source": planner_session_source,
            }
        )
    update_state(root, wu_path, **state_patch)
    print(json.dumps(request, ensure_ascii=False, indent=2))
    return 0


def submit_review(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    request = load_json(review_requests_dir(wu_path) / f"{args.request_id}.json", {}) if args.request_id else latest_review_request(wu_path, args.mode, pending_only=True)
    if not request:
        raise HarnessError(f"No pending {args.mode} review request found.")
    if request.get("mode") != args.mode:
        raise HarnessError("Review mode does not match request.")
    track = load_json(review_track_path(wu_path), {})
    reviewer_id, identity_source = _identity(args.reviewer_id, "HARNESS_REVIEWER_ID", str(request.get("reviewer_id", "")))
    reviewer_session, session_source = _identity(args.reviewer_session, "HARNESS_REVIEWER_SESSION", str(request.get("reviewer_session_id", "")))
    if reviewer_id != request.get("reviewer_id") or reviewer_id != track.get("reviewer_id"):
        raise HarnessError("Verdict reviewer identity does not match the review track.")
    state = load_json(state_path(wu_path), {})
    if request.get("reviewed_spec_hash") != state.get("spec_approved_hash"):
        raise HarnessError("Review request is stale because the approved spec changed.")
    if request.get("reviewed_plan_hash") != file_hash(plan_path(wu_path)):
        raise HarnessError("Review request is stale because the technical plan changed.")
    if args.mode == "close":
        current_impl_hash = implementation_diff_hash(root, str(state.get("base_commit", "")))
        if request.get("reviewed_implementation_diff_hash") != current_impl_hash:
            raise HarnessError("Close review request is stale because implementation content changed.")
        verification_decision, verification_blocking, _verification_warnings = check_verification(root, wu_path)
        if verification_decision == "BLOCK":
            raise HarnessError("Close review verdict is blocked by stale or missing evidence: " + "; ".join(verification_blocking))
    human_gate = args.independence_level == "human_gate"
    if human_gate:
        if not reviewer_id.startswith("human:"):
            raise HarnessError("human_gate requires a human:<identity> reviewer.")
        if not args.approval_ref:
            raise HarnessError("human_gate requires --approval-ref for an auditable human decision.")
    if args.mode == "plan":
        subject_id = str(request.get("planner_id", ""))
        subject_session = str(request.get("planner_session_id", ""))
    else:
        subject_id = str(state.get("builder_id", ""))
        subject_session = str(state.get("builder_session_id", ""))
    independently_separated = bool(
        reviewer_id
        and subject_id
        and reviewer_id != subject_id
        and reviewer_session
        and subject_session
        and reviewer_session != subject_session
    )
    is_independent = human_gate or independently_separated
    if args.mode == "close" and reviewer_id == state.get("builder_id"):
        raise HarnessError("Builder cannot submit its own close review verdict.")
    if args.mode == "close" and reviewer_session and reviewer_session == state.get("builder_session_id"):
        raise HarnessError("Close review cannot use the builder session.")
    evidence_refs = args.evidence_ref or list(request.get("evidence_refs", []))
    verdict = {
        "schema_version": REVIEW_VERDICT_SCHEMA,
        "review_id": "rv-" + uuid.uuid4().hex[:12],
        "request_id": request["request_id"],
        "review_track_id": request["review_track_id"],
        "work_unit_id": work_unit_id,
        "mode": args.mode,
        "reviewer_id": reviewer_id,
        "reviewer_identity_source": identity_source,
        "reviewer_session_id": reviewer_session,
        "reviewer_session_source": session_source,
        "planner_id": request.get("planner_id", ""),
        "planner_session_id": request.get("planner_session_id", ""),
        "builder_id": state.get("builder_id", ""),
        "builder_session_id": state.get("builder_session_id", ""),
        "independence_level": args.independence_level,
        "is_independent": is_independent,
        "decision": args.decision,
        "approval_ref": args.approval_ref or "",
        "reviewed_spec_hash": request.get("reviewed_spec_hash"),
        "reviewed_plan_hash": request.get("reviewed_plan_hash"),
        "reviewed_implementation_diff_hash": request.get("reviewed_implementation_diff_hash"),
        "evidence_refs": evidence_refs,
        "findings": args.finding or [],
        "required_rework": args.required_rework or [],
        "created_at": now_iso(),
    }
    risk = str(state.get("risk", "low"))
    if args.decision == "PASS" and RISK_ORDER.get(risk, 1) >= 1 and not is_independent:
        subject = "planner" if args.mode == "plan" else "builder"
        raise HarnessError(f"{risk} risk PASS requires reviewer identity/session separation from the {subject} or human_gate.")
    write_json(review_verdicts_dir(wu_path) / f"{verdict['review_id']}.json", verdict)
    sessions = list(track.get("reviewer_sessions", []))
    if reviewer_session and reviewer_session not in sessions:
        sessions.append(reviewer_session)
    track["reviewer_sessions"] = sessions
    track["updated_at"] = now_iso()
    if args.mode == "plan":
        track["plan_review_id"] = verdict["review_id"]
        track["plan_findings"] = verdict["findings"]
    else:
        track["close_review_id"] = verdict["review_id"]
    write_json(review_track_path(wu_path), track)
    if args.mode == "plan":
        if args.decision == "PASS":
            update_state(root, wu_path, status="ready", plan_approved_hash=request["reviewed_plan_hash"], plan_review_approved_spec_hash=request["reviewed_spec_hash"], plan_review_id=verdict["review_id"], next_safe_action="Start an isolated worker with `harnessctl start-work`.")
        else:
            update_state(root, wu_path, status="planning", plan_approved_hash="", next_safe_action="Revise plan.md and request plan review again.")
    else:
        if args.decision == "PASS":
            update_state(root, wu_path, status="reviewing", close_review_id=verdict["review_id"], next_safe_action="Run finalize-check, then integrate, hand off, or archive.")
        else:
            update_state(root, wu_path, status="running", next_safe_action="Return findings to the worker, fix them, rerun affected evidence, and request close review again.")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0


def validate_work_unit(root: Path, work_unit_id: str, wu_path: Path) -> Tuple[List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    state = load_json(state_path(wu_path), {})
    if state.get("schema_version") != STATE_SCHEMA:
        blocking.append(f"state.json schema_version must be {STATE_SCHEMA}.")
    if state.get("work_unit_id") != work_unit_id:
        blocking.append("state.json work_unit_id mismatch.")
    if state.get("status") not in VALID_STATUSES:
        blocking.append(f"Invalid state status: {state.get('status')}")
    spec_blocking, spec_warnings = check_spec_document(spec_path(wu_path), work_unit_id)
    blocking.extend(spec_blocking)
    warnings.extend(spec_warnings)
    for row in evidence_receipts(wu_path):
        if row.get("schema_version") != EVIDENCE_SCHEMA:
            blocking.append(f"Receipt {row.get('receipt_id')} has unsupported schema.")
        if row.get("work_unit_id") != work_unit_id:
            blocking.append(f"Receipt {row.get('receipt_id')} work_unit_id mismatch.")
        if row.get("result") == "pass" and row.get("observation") != "controller_executed_command":
            blocking.append(f"Receipt {row.get('receipt_id')} claims pass without controller command observation.")
        log_ref = str(row.get("command_log_ref", ""))
        if row.get("result") == "pass" and (not log_ref or not (root / log_ref).exists()):
            blocking.append(f"Pass receipt {row.get('receipt_id')} has no readable command log.")
        elif row.get("result") == "pass" and row.get("command_log_hash") != file_hash(root / log_ref):
            blocking.append(f"Pass receipt {row.get('receipt_id')} command log hash does not match the recorded log.")
        if not row.get("spec_hash"):
            blocking.append(f"Receipt {row.get('receipt_id')} is not bound to an approved spec revision.")
        if not row.get("plan_hash"):
            blocking.append(f"Receipt {row.get('receipt_id')} is not bound to an approved plan revision.")
    request_ids = {str(row.get("request_id")) for row in review_requests(wu_path)}
    for verdict in review_verdicts(wu_path):
        if verdict.get("schema_version") != REVIEW_VERDICT_SCHEMA:
            blocking.append(f"Review {verdict.get('review_id')} has unsupported schema.")
        if verdict.get("request_id") not in request_ids:
            blocking.append(f"Review {verdict.get('review_id')} references missing request.")
        blocking.extend(
            f"Review {verdict.get('review_id')}: {reason}"
            for reason in review_independence_errors(verdict)
        )
    return blocking, warnings


def validate(args: argparse.Namespace) -> int:
    root = args.root
    units: List[Tuple[str, Path]] = []
    if args.all:
        for base in (active_dir(root), archive_dir(root)):
            if base.exists():
                units.extend((path.name, path) for path in sorted(base.iterdir()) if path.is_dir())
    else:
        units.append(resolve_wu(root, args.id))
    blocking: List[str] = []
    warnings: List[str] = []
    for work_unit_id, wu_path in units:
        b, w = validate_work_unit(root, work_unit_id, wu_path)
        blocking.extend(f"{work_unit_id}: {x}" for x in b)
        warnings.extend(f"{work_unit_id}: {x}" for x in w)
    decision = "BLOCK" if blocking else "WARN" if warnings else "PASS"
    print(json.dumps({"decision": decision, "checked_work_units": [x[0] for x in units], "blocking_reasons": blocking, "warnings": warnings}, ensure_ascii=False, indent=2))
    return 2 if decision == "BLOCK" and args.strict else 0


def parse_frontmatter(text: str) -> Dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    out: Dict[str, str] = {}
    for raw in parts[1].splitlines():
        if ":" in raw:
            key, value = raw.split(":", 1)
            out[key.strip()] = clean_scalar(value)
    return out


def check_skills(root: Path) -> Tuple[str, List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    canonical = root / "skills"
    platform_dirs = [root / ".agents" / "skills", root / ".claude" / "skills"]
    if not canonical.exists():
        canonical = next((path for path in platform_dirs if path.exists()), canonical)
    skills = sorted(path for path in canonical.glob("harness-*") if (path / "SKILL.md").exists())
    if not skills:
        return "BLOCK", ["No harness skills found."], warnings
    names = [path.name for path in skills]
    if "harness-waiver" in names:
        blocking.append("harness-waiver must not be installed; missing evidence blocks or requires spec revision.")
    for platform in platform_dirs:
        if platform.exists():
            platform_names = sorted(path.name for path in platform.glob("harness-*") if (path / "SKILL.md").exists())
            if platform_names != names:
                blocking.append(f"Skill mirror mismatch for {platform.relative_to(root)}.")
    required = {
        "harness-clarify": ["one high-value question", "do not implement"],
        "harness-spec": ["docs/spec", "approve-spec"],
        "harness-plan": ["plan.md", "plan review"],
        "harness-evidence": ["harnessctl verify", "controller"],
        "harness-review": ["review track", "same reviewer"],
        "harness-tdd": ["RED", "GREEN", "expected reason"],
    }
    for path in skills:
        text = (path / "SKILL.md").read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm.get("name") != path.name or not fm.get("description"):
            blocking.append(f"{path.name} frontmatter name/description is invalid.")
        for phrase in required.get(path.name, []):
            if phrase.lower() not in text.lower():
                blocking.append(f"{path.name} is missing required phrase: {phrase}")
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


CHECKS = {
    "spec": check_spec,
    "plan": check_plan,
    "plan-review": check_plan_review,
    "scope": check_scope,
    "verification": check_verification,
    "review": check_review,
    "archive": check_archive,
    "skills": check_skills,
}


def check(args: argparse.Namespace) -> int:
    if args.gate == "skills":
        work_unit_id = "repo"
        decision, blocking, warnings = check_skills(args.root)
        details: Dict[str, Any] = {}
    else:
        work_unit_id, wu_path = resolve_wu(args.root, args.id)
        decision, blocking, warnings = CHECKS[args.gate](args.root, wu_path)
        details = {}
        if args.gate == "verification":
            report, _b, _w = verification_detail_report(args.root, wu_path)
            details["evidence_status"] = report
            details["minimal_evidence_plan"] = [row for row in report if row["status"] != "satisfied"]
    out = {
        "schema_version": "harness.controller_check.v2",
        "work_unit_id": work_unit_id,
        "check": args.gate,
        "decision": decision,
        "blocking_reasons": blocking,
        "warnings": warnings,
        "required_next_action": "Fix blocking reasons." if blocking else "Proceed with caution." if warnings else "Gate passed.",
        "created_at": now_iso(),
        **details,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 2 if decision == "BLOCK" and args.strict else 0


def finalize_check(args: argparse.Namespace) -> int:
    work_unit_id, wu_path = resolve_wu(args.root, args.id)
    validation_blocking, validation_warnings = validate_work_unit(args.root, work_unit_id, wu_path)
    gates: Dict[str, Any] = {}
    blocking = [f"validate: {x}" for x in validation_blocking]
    warnings = [f"validate: {x}" for x in validation_warnings]
    for name in ("spec", "scope", "verification", "review"):
        decision, b, w = CHECKS[name](args.root, wu_path)
        gates[name] = {"decision": decision, "blocking_reasons": b, "warnings": w}
        blocking.extend(f"{name}: {x}" for x in b)
        warnings.extend(f"{name}: {x}" for x in w)
    decision = "BLOCK" if blocking else "WARN" if warnings else "PASS"
    out = {
        "schema_version": "harness.finalize_check.v2",
        "work_unit_id": work_unit_id,
        "decision": decision,
        "gates": gates,
        "blocking_reasons": blocking,
        "warnings": warnings,
        "required_next_action": "Fix blocking reasons." if blocking else "Integrate, hand off, or archive.",
        "created_at": now_iso(),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 2 if decision == "BLOCK" and args.strict else 0


def ci(args: argparse.Namespace) -> int:
    root = args.root
    blocking: List[str] = []
    warnings: List[str] = []
    skills_decision, skills_blocking, skills_warnings = check_skills(root)
    blocking.extend(f"skills: {x}" for x in skills_blocking)
    warnings.extend(f"skills: {x}" for x in skills_warnings)
    specs = sorted((root / "docs" / "spec").glob("*.md")) if (root / "docs" / "spec").exists() else []
    for path in specs:
        if path.name.lower() == "readme.md":
            continue
        b, w = check_spec_document(path, path.stem)
        blocking.extend(f"{path}: {x}" for x in b)
        warnings.extend(f"{path}: {x}" for x in w)
    if active_dir(root).exists():
        for wu_path in sorted(path for path in active_dir(root).iterdir() if path.is_dir()):
            b, w = validate_work_unit(root, wu_path.name, wu_path)
            blocking.extend(f"{wu_path.name}: {x}" for x in b)
            warnings.extend(f"{wu_path.name}: {x}" for x in w)
    decision = "BLOCK" if blocking else "WARN" if warnings else "PASS"
    print(json.dumps({"schema_version": "harness.ci_check.v2", "decision": decision, "checked_specs": [str(path.relative_to(root)) for path in specs], "blocking_reasons": blocking, "warnings": warnings, "created_at": now_iso()}, ensure_ascii=False, indent=2))
    return 2 if decision == "BLOCK" and args.strict else 0


def render_list(items: Iterable[Any]) -> str:
    values = [str(x) for x in items if str(x).strip()]
    return "\n".join(f"- {value}" for value in values) if values else "- none"


def handoff(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    state_before = load_json(state_path(wu_path), {})
    resume_status = str(state_before.get("resume_status") or state_before.get("status") or "running")
    state = update_state(root, wu_path, status="handoff", resume_status=resume_status, next_safe_action=args.next_safe_action)
    receipts = evidence_receipts(wu_path)[-5:]
    verdicts = review_verdicts(wu_path)[-3:]
    text = f"""# Handoff: {work_unit_id}

## Tracked intent

- spec: {state.get('spec_path')}
- approved spec hash: {state.get('spec_approved_hash')}

## Local technical plan

- plan: {state.get('plan_path')}
- approved plan hash: {state.get('plan_approved_hash')}

## Status

{state.get('status')}

## Branch / worktree / head

- branch: {state.get('branch')}
- worktree: {state.get('worktree')}
- head_commit: {state.get('head_commit')}
- base_commit: {state.get('base_commit')}

## Objective

{spec_summary(wu_path)}

## Implementation changed files

{render_list(state.get('implementation_changed_files', []))}

## Latest evidence

{render_list(f"{row.get('receipt_id')} {row.get('result')} {row.get('claim_ref')} {row.get('command')}" for row in receipts)}

## Latest reviews

{render_list(f"{row.get('review_id')} {row.get('mode')} {row.get('decision')} reviewer={row.get('reviewer_id')}" for row in verdicts)}

## Known failures

{render_list(state.get('known_failures', []))}

## Blockers

{render_list(state.get('blockers', []))}

## Next safe action

{args.next_safe_action}

## Recovery rule

Read the tracked spec and current repository first. Treat this handoff and local plan as recoverable runtime context, not project truth. If `.harness` is unavailable, run `harnessctl resume --id {work_unit_id}` and rebuild the plan from the spec, Git/GitHub, and codebase.

## Rollback or reopen path

{state.get('rollback_or_reopen_path')}
"""
    atomic_write_text(wu_path / "handoff.md", text)
    print(f"Generated local handoff: {wu_path / 'handoff.md'}")
    return 0


def archive(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    if args.no_next_step_reason:
        update_state(root, wu_path, no_next_step_reason=args.no_next_step_reason)
    decision, blocking, warnings = check_archive(root, wu_path)
    if decision == "BLOCK" and not args.force:
        print(json.dumps({"decision": decision, "blocking_reasons": blocking, "warnings": warnings}, ensure_ascii=False, indent=2))
        return 2
    update_state(root, wu_path, status="archived", next_safe_action="No local next step; reopen or create a follow-up Work Unit for further work.")
    destination = archive_dir(root) / work_unit_id
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise HarnessError(f"Archive destination already exists: {destination}")
    shutil.move(str(wu_path), str(destination))
    cur = current_file(root)
    if cur.exists() and cur.read_text(encoding="utf-8").strip() == work_unit_id:
        cur.unlink()
    print(f"Archived local Work Unit {work_unit_id}; tracked spec remains at docs/spec/{work_unit_id}.md")
    return 0


def doctor(args: argparse.Namespace) -> int:
    root = args.root
    checks = [
        ("controller cli", (root / "harness" / "cli" / "harnessctl.py").exists()),
        ("tracked specs directory", (root / "docs" / "spec").exists()),
        ("local runtime ignored", ".harness/" in (root / ".gitignore").read_text(encoding="utf-8") if (root / ".gitignore").exists() else False),
        ("evidence schema", (root / "harness" / "schemas" / "evidence-receipt.schema.json").exists()),
        ("spec template", (root / "harness" / "templates" / "feature-spec.md").exists()),
        ("plan template", (root / "harness" / "templates" / "technical-plan.md").exists()),
        ("skills", check_skills(root)[0] != "BLOCK"),
        ("git repository", is_git_repo(root)),
    ]
    for name, ok in checks:
        print(f"{'PASS' if ok else 'WARN'}\t{name}")
    return 0


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
    p.add_argument("--risk", default="low", choices=sorted(RISK_ORDER, key=RISK_ORDER.get))
    p.set_defaults(func=new)

    p = sub.add_parser("resume")
    p.add_argument("--id", required=True)
    p.set_defaults(func=resume)

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
    p.add_argument("--approved-by")
    p.add_argument("--approval-ref")
    p.set_defaults(func=approve_spec)

    p = sub.add_parser("amend")
    p.add_argument("--id")
    p.add_argument("--reason", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--actor")
    p.add_argument("--approval-ref")
    p.set_defaults(func=amend)

    p = sub.add_parser("start-work")
    p.add_argument("--id")
    p.add_argument("--builder-id")
    p.add_argument("--builder-session")
    p.set_defaults(func=start_work)

    p = sub.add_parser("resume-work")
    p.add_argument("--id")
    p.add_argument("--builder-id")
    p.add_argument("--builder-session")
    p.set_defaults(func=resume_work)

    p = sub.add_parser("verify")
    p.add_argument("--id")
    p.add_argument("--claim", required=True)
    p.add_argument("--type", default="test")
    p.add_argument("--phase", choices=["red", "green", "final"], default="final")
    p.add_argument("--expect", choices=["pass", "fail"], default="pass")
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--verification-scope", default="behavior")
    p.add_argument("--environment-ref")
    p.add_argument("--note")
    p.add_argument("command", nargs=argparse.REMAINDER)
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
    p.add_argument("--independence-level", choices=["self_check", "separate_role", "fresh_context", "human_gate"], default="fresh_context")
    p.add_argument("--approval-ref", default="")
    p.add_argument("--evidence-ref", action="append")
    p.add_argument("--finding", action="append")
    p.add_argument("--required-rework", action="append")
    p.set_defaults(func=submit_review)

    p = sub.add_parser("check")
    p.add_argument("--id")
    p.add_argument("--gate", required=True, choices=sorted(CHECKS))
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

    p = sub.add_parser("handoff")
    p.add_argument("--id")
    p.add_argument("--next-safe-action", required=True)
    p.set_defaults(func=handoff)

    p = sub.add_parser("archive")
    p.add_argument("--id")
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-next-step-reason")
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
