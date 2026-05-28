#!/usr/bin/env python3
"""Small controller CLI for a coding-agent harness.

This controller owns deterministic lifecycle checks only. It does not judge product
quality and it does not replace human/product review.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
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


def diff_hash(root: Path, base_commit: str = "") -> str:
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
        h.update("\0".join(args).encode("utf-8"))
        h.update(out.encode("utf-8"))
    return h.hexdigest()


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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


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
    state = load_json(state_path(wu_path))
    state.update({k: v for k, v in patch.items() if v is not None})
    state["branch"] = current_branch(root)
    state["head_commit"] = head_commit(root)
    base_commit = str(state.get("base_commit", ""))
    state["diff_hash"] = diff_hash(root, base_commit)
    state["changed_files"] = work_unit_changed_files(root, base_commit)
    state["updated_at"] = now_iso()
    write_json(state_path(wu_path), state)
    return state


def parse_yaml_header(text: str) -> Dict[str, str]:
    if "```yaml" not in text:
        return {}
    block = text.split("```yaml", 1)[1].split("```", 1)[0]
    out: Dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def get_section_lines(text: str, heading: str) -> List[str]:
    lines = text.splitlines()
    start = None
    target = heading.strip().lower()
    for i, line in enumerate(lines):
        if line.strip().lower() == target:
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
    for heading in ("## Intent", "## Expected Outcome", "## Scope", "## Required evidence", "## Open questions"):
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
    return str(value).strip().lower() in {"true", "yes", "1", "required"}


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
    simple_id_re = re.compile(r"^-\s*([A-Za-z][A-Za-z0-9_.:-]*)\s*:?(.*)$")
    key_re = re.compile(r"^(id|claim|command|required_for_completion|type|scope|covers)\s*:\s*(.*)$")
    for raw in lines:
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            body = stripped[2:].strip()
            if body.upper() == "TBD":
                continue
            if body.startswith("id:"):
                if cur:
                    items.append(cur)
                cur = {"id": body.split(":", 1)[1].strip()}
                continue
            m = simple_id_re.match(stripped)
            if m:
                if cur:
                    items.append(cur)
                ev_id, rest = m.group(1).strip(), m.group(2).strip()
                cur = {"id": ev_id}
                if rest:
                    cur["claim"] = rest
                continue
        m = key_re.match(stripped)
        if m and cur is not None:
            key, value = m.group(1), m.group(2).strip()
            cur[key] = value
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


def receipt_has_reviewable_support(receipt: Dict[str, Any]) -> bool:
    if receipt.get("artifact_uri") or receipt.get("command_log_ref") or receipt.get("manual_artifact_ref"):
        return True
    command = str(receipt.get("command", "")).strip()
    return bool(command)


def review_verdicts(wu_path: Path) -> List[Dict[str, Any]]:
    out = []
    for path in sorted(reviews_dir(wu_path).glob("verdict-*.json")):
        out.append(load_json(path))
    return out


def init(args: argparse.Namespace) -> int:
    root = args.root
    for p in [active_dir(root), archive_dir(root), harness_dir(root) / "tmp"]:
        p.mkdir(parents=True, exist_ok=True)
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
        "contract_hash": contract_hash(wu_path),
        "created_at": now_iso(),
    }
    append_jsonl(amendments_path(wu_path), amendment)
    if decision == "BLOCK" and args.allow_draft:
        state = update_state(root, wu_path, status="draft", contract_locked=False, contract_lock_hash="", last_amendment_at=amendment["created_at"], next_safe_action="Finish contract amendment and run spec gate before locking.")
    else:
        state = update_state(root, wu_path, status="specified", contract_locked=True, contract_lock_hash=contract_hash(wu_path), last_amendment_at=amendment["created_at"], next_safe_action="Re-request plan review before running because contract changed.")
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
    request_id = "review-request-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
    required_inputs = ["contract.md", "scope boundary", "risk notes", "context pointers", "proposed execution plan"] if args.mode == "plan" else ["contract.md", "git diff", "evidence/receipts.jsonl", "scope boundary", "risk notes"]
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
    if args.mode == "close" and args.reviewer_role == args.builder_role:
        raise HarnessError("Close review cannot be written by the builder role.")
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
        "evidence_refs": args.evidence_ref or [],
        "scope_check": {},
        "risk_check": {},
        "findings": args.finding or [],
        "required_rework": args.required_rework or [],
        "created_at": now_iso()
    }
    write_json(reviews_dir(wu_path) / f"verdict-{review_id}.json", obj)
    next_action = "Integrate or archive if remaining gates pass." if args.decision in PASS_DECISIONS else "Address review findings and resubmit."
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

    required = ["## Intent", "## Expected Outcome", "## Non-goals", "## Scope", "## Required evidence", "## Stop conditions", "## Open questions"]
    for heading in required:
        section = get_section_lines(text, heading)
        if not section:
            blocking.append(f"Missing heading: {heading}")
    if meta.get("risk") not in RISK_ORDER:
        blocking.append("Contract risk must be one of trivial, low, medium, high, critical.")

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
    files = [f for f in work_unit_changed_files(root, base_commit) if not f.startswith(".harness/work-units/")]
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


def check_verification(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    state = load_json(state_path(wu_path), {})
    work_unit_id = str(state.get("work_unit_id") or wu_path.name)
    required = required_evidence_items(wu_path)
    if not required:
        blocking.append("No required evidence IDs found in contract.md. Add claim-relative evidence under ## Required evidence.")
        return "BLOCK", blocking, warnings

    cur_head = head_commit(root)
    risk = str(state.get("risk") or contract_meta(wu_path).get("risk", "low"))
    base_commit = str(state.get("base_commit", ""))
    cur_diff = diff_hash(root, base_commit)
    scoped_waivers = waivers_by_requirement(wu_path, work_unit_id)

    for item in required:
        ev_id = str(item.get("id", "")).strip()
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
                warnings.append(f"Required evidence {ev_id} is satisfied by scoped waiver {valid_waiver.get('waiver_id')}; ensure risk acceptance remains appropriate.")
                continue
            if invalid_reasons:
                blocking.append(f"Required evidence {ev_id} has only invalid waiver(s): {', '.join(invalid_reasons)}.")
            else:
                blocking.append(f"Missing fresh pass evidence for required claim {ev_id}.")
            continue

        if receipt.get("result") == "skipped":
            blocking.append(f"Required evidence {ev_id} is skipped; skipped receipts cannot satisfy verification.")
        if receipt.get("head_commit") != cur_head:
            warnings.append(f"Evidence {ev_id} was recorded on a different HEAD. Confirm documented equivalence or rerun.")
        if receipt.get("diff_hash") != cur_diff:
            blocking.append(f"Evidence {ev_id} is stale: current diff hash differs from receipt diff_hash.")
        if not receipt_has_reviewable_support(receipt):
            blocking.append(f"Evidence {ev_id} lacks command, command log, artifact, or manual artifact reference.")
        if RISK_ORDER.get(risk, 1) >= 2 and not (receipt.get("artifact_uri") or receipt.get("command_log_ref") or receipt.get("manual_artifact_ref")):
            blocking.append(f"Evidence {ev_id} for {risk} risk needs command_log_ref, artifact_uri, or manual_artifact_ref; command text alone is not enough.")

    # Flag receipts whose claim_ref is not in the contract. They are not blocking by
    # themselves, but they cannot satisfy completion and usually indicate drift.
    required_ids = {str(x.get("id", "")).strip() for x in required}
    for receipt in evidence_receipts(wu_path, work_unit_id):
        claim = str(receipt.get("claim_ref", "")).strip()
        if claim and claim not in required_ids:
            warnings.append(f"Receipt {receipt.get('receipt_id')} references non-contract claim {claim}; it does not satisfy completion.")

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
    close_passes = [v for v in review_verdicts(wu_path) if v.get("mode") == "close" and v.get("decision") in PASS_DECISIONS]
    verdicts = sorted(close_passes, key=lambda v: (v.get("created_at", ""), v.get("review_id", "")))[-1:]
    if RISK_ORDER.get(risk, 1) <= 1:
        if not verdicts:
            warnings.append("Low/trivial risk has no close review. Self-check may be acceptable.")
            return "WARN", [], warnings
    if RISK_ORDER.get(risk, 1) >= 2 and not verdicts:
        blocking.append(f"{risk} risk requires a passing close review verdict.")
        return "BLOCK", blocking, warnings
    if RISK_ORDER.get(risk, 1) >= 3:
        independent = [v for v in verdicts if v.get("is_independent") or v.get("independence_level") == "human_gate"]
        if not independent:
            blocking.append(f"{risk} risk requires independent close review or human gate.")
    for v in verdicts:
        if v.get("mode") == "close" and v.get("reviewer_role") == v.get("builder_role"):
            blocking.append("Builder-authored close review detected.")

    required = required_evidence_items(wu_path)
    base_commit = str(state.get("base_commit", ""))
    cur_head = head_commit(root)
    cur_diff = diff_hash(root, base_commit)
    for v in verdicts:
        refs = set(str(x).strip() for x in v.get("evidence_refs", []) if str(x).strip())
        if RISK_ORDER.get(risk, 1) >= 2 and not refs:
            blocking.append("Passing close review for medium+ risk must cite fresh evidence receipt IDs.")
        for item in required:
            ev_id = str(item.get("id", "")).strip()
            receipt = latest_pass_for_claim(wu_path, work_unit_id, ev_id)
            if receipt is None:
                continue
            rid = str(receipt.get("receipt_id", ""))
            if receipt.get("head_commit") != cur_head or receipt.get("diff_hash") != cur_diff:
                blocking.append(f"Close review cites stale evidence context for {ev_id}; rerun verification before passing review.")
            if refs and rid not in refs:
                msg = f"Passing close review does not cite latest fresh receipt {rid} for required claim {ev_id}."
                if RISK_ORDER.get(risk, 1) >= 2:
                    blocking.append(msg)
                else:
                    warnings.append(msg)
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


def check_archive(root: Path, wu_path: Path) -> Tuple[str, List[str], List[str]]:
    blocking: List[str] = []
    warnings: List[str] = []
    state = load_json(state_path(wu_path), {})
    risk = str(state.get("risk") or contract_meta(wu_path).get("risk", "low"))
    for name, func in (("verification", check_verification), ("review", check_review)):
        decision, b, w = func(root, wu_path)
        blocking.extend([f"{name}: {x}" for x in b])
        warnings.extend([f"{name}: {x}" for x in w])
    handoff = wu_path / "handoff.md"
    no_next_step_reason = str(state.get("no_next_step_reason", "")).strip()
    missing_handoff = not handoff.exists() or "Not generated yet" in handoff.read_text(encoding="utf-8")
    if missing_handoff and not no_next_step_reason:
        msg = "Handoff is missing or not generated. Archive should include handoff or no-next-step reason."
        if RISK_ORDER.get(risk, 1) >= 2:
            blocking.append(msg)
        else:
            warnings.append(msg)
    return ("BLOCK" if blocking else "WARN" if warnings else "PASS"), blocking, warnings


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


def archive(args: argparse.Namespace) -> int:
    root = args.root
    work_unit_id, wu_path = resolve_wu(root, args.id)
    if args.no_next_step_reason:
        update_state(root, wu_path, no_next_step_reason=args.no_next_step_reason)
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
    p.add_argument("--mode", default="close", choices=["plan", "close", "risk", "security", "architecture", "evaluator"])
    p.add_argument("--reviewer-role", default="reviewer-agent")
    p.set_defaults(func=request_review)

    p = sub.add_parser("submit-review")
    p.add_argument("--id")
    p.add_argument("--request-id")
    p.add_argument("--mode", default="close", choices=["plan", "close", "risk", "security", "architecture", "evaluator"])
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
