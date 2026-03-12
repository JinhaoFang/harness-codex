#!/usr/bin/env python3
"""Agentdocs hard checks: flowcheck / lint / coverage.

This is a **repo-local harness tool**. It reads markdown sources of truth
(workflow/plan/index) and surfaces deterministic signals early.

This version is compatible with BOTH packs:
- V2 templates (e.g. headings like "1) Align（S1）")
- V3 runtime-governed templates (e.g. "1) Align", "3) Plan Status", "4) Phase Board")

Exit codes:
  0 -> OK/WARN/EXCEPTION_ALLOWED
  2 -> BLOCK
  3 -> ERROR (unexpected)
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")
FRONTMATTER_BOUNDARY = "---"
LEGACY_ACTIVE_TASKS_RE = re.compile(r"## Active Tasks\n(?P<body>[\s\S]*?)(?:\n## |\Z)")


@dataclass
class CheckResult:
    name: str
    status: str  # OK|WARN|BLOCK|EXCEPTION_ALLOWED
    message: str
    details: Dict[str, Any]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def parse_frontmatter(md: str) -> Dict[str, str]:
    lines = md.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_BOUNDARY:
        return {}
    out: Dict[str, str] = {}
    for i in range(1, len(lines)):
        if lines[i].strip() == FRONTMATTER_BOUNDARY:
            break
        line = lines[i]
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = v.strip()
    return out


def split_sections(md: str) -> Dict[str, str]:
    """Return mapping from heading title (full line after ##) to section body."""
    lines = md.splitlines()
    sections: Dict[str, List[str]] = {}
    current: Optional[str] = None
    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            current = m.group(1)
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
    return {k: "\n".join(v).strip("\n") for k, v in sections.items()}


def get_section(sections: Dict[str, str], *, exact: List[str] | None = None, contains: List[str] | None = None) -> str:
    exact = exact or []
    contains = contains or []

    for k in exact:
        if k in sections:
            return sections[k]

    if contains:
        for title, body in sections.items():
            if any(token in title for token in contains):
                return body

    return ""


def find_in_text(text: str, pattern: str) -> Optional[str]:
    m = re.search(pattern, text, flags=re.MULTILINE)
    return m.group(1).strip() if m else None


def find_in_section(section: str, pattern: str) -> Optional[str]:
    return find_in_text(section, pattern)


def normalize_ref(value: str) -> str:
    return value.strip().strip("`")


def repo_root_from_workflow(workflow_path: Path) -> Path:
    # prefer task-scoped workflows under <root>/.agentdocs/tasks/<task-id>/workflow.md
    p = workflow_path.resolve()
    parts = list(p.parts)
    if ".agentdocs" in parts:
        idx = parts.index(".agentdocs")
        return Path(*parts[:idx])
    return workflow_path.parent


def parse_phase_table(phase_board_section: str) -> List[Dict[str, str]]:
    """Parse the Phase Board markdown table rows."""
    rows: List[Dict[str, str]] = []
    lines = [ln.strip() for ln in phase_board_section.splitlines()]
    table_lines = [ln for ln in lines if ln.startswith("|")]
    if len(table_lines) < 3:
        return rows
    header = [c.strip() for c in table_lines[0].strip("|").split("|")]
    # skip separator line
    for ln in table_lines[2:]:
        cols = [c.strip() for c in ln.strip("|").split("|")]
        if len(cols) != len(header):
            continue
        row = dict(zip(header, cols))
        rows.append(row)
    return rows


def detect_committed_build(sections: Dict[str, str]) -> Tuple[bool, Dict[str, Any]]:
    details: Dict[str, Any] = {}

    phase_sec = get_section(
        sections,
        exact=["3) Phase Board（执行状态 SSOT）", "4) Phase Board（执行状态 SSOT）"],
        contains=["Phase Board"],
    )
    rows = parse_phase_table(phase_sec)
    details["phase_rows"] = rows

    build_started = False
    build_signals: List[str] = []

    for r in rows:
        status = (r.get("Status") or "").upper()
        verify = (r.get("Verify Run") or r.get("Verification") or "").strip()
        evidence = (r.get("Evidence Ref") or "").strip()
        if status and status not in {"TODO", ""}:
            build_started = True
            build_signals.append(f"phase_status={status}")
            break
        if verify or evidence:
            build_started = True
            build_signals.append("phase_verify_or_evidence")
            break

    build_log = get_section(
        sections,
        exact=["4) Build Log（S3）", "5) Build Log"],
        contains=["Build Log"],
    )
    if re.search(r"^\s*-\s*\d{4}-\d{2}-\d{2}", build_log, flags=re.MULTILINE):
        build_started = True
        build_signals.append("build_log_entry")

    details["build_signals"] = build_signals
    return build_started, details


def read_exception_status(wf_text: str, secs: Dict[str, str]) -> str:
    # V3: status header has '- Exception Status: ...'
    v3 = find_in_text(wf_text, r"^\s*-\s*Exception Status:\s*(.+?)\s*$")
    if v3:
        return v3

    # V2: Plan Status section may have '- Exception Lane: ...'
    plan_status = get_section(secs, exact=["2) Plan Status（S2）"], contains=["Plan Status"])
    v2 = find_in_section(plan_status, r"^\s*-\s*Exception Lane:\s*(.+?)\s*$")
    if v2:
        return v2

    return "NONE"


def flowcheck(workflow_path: Path, intent: str) -> CheckResult:
    wf_text = read_text(workflow_path)
    secs = split_sections(wf_text)

    plan_status = get_section(secs, exact=["2) Plan Status（S2）", "3) Plan Status"], contains=["Plan Status"])
    review_status = find_in_section(plan_status, r"^\s*-\s*Review Status:\s*(.+?)\s*$")

    exception_status = read_exception_status(wf_text, secs)

    build_started, build_details = detect_committed_build(secs)

    details: Dict[str, Any] = {
        "review_status": review_status,
        "exception_status": exception_status,
        "build_started": build_started,
        **build_details,
    }

    if not review_status:
        return CheckResult(
            name="flowcheck",
            status="BLOCK",
            message="Missing Plan Review status in workflow (Plan Status section).",
            details=details,
        )

    normalized = review_status.strip().upper()
    exception_norm = (exception_status or "NONE").strip().upper()

    if intent == "build":
        if normalized == "PASS":
            return CheckResult("flowcheck", "OK", "Plan Review PASS: Build gate satisfied.", details)

        # Not PASS
        if build_started:
            if exception_norm not in {"NONE", ""} and exception_norm != "CLOSED":
                return CheckResult(
                    "flowcheck",
                    "EXCEPTION_ALLOWED",
                    "Committed Build detected without Plan Review PASS, but Exception is active. Treat this run as exception and tighten Close Review.",
                    details,
                )
            return CheckResult(
                "flowcheck",
                "BLOCK",
                "Committed Build appears to have started but Plan Review is not PASS. Enter Exception Recovery (or roll back to Plan Review) before continuing.",
                details,
            )

        return CheckResult(
            "flowcheck",
            "BLOCK",
            f"Plan Review is '{review_status}'. Committed Build requires PASS (or explicit Exception Recovery).",
            details,
        )

    if intent == "archive":
        # archive is stricter than general, but still not a full substitute for validate_workflow_state.py
        final_status = find_in_text(wf_text, r"^\s*-\s*Final Status:\s*(.+?)\s*$")
        if (final_status or "").strip().upper() != "PASS":
            return CheckResult(
                "flowcheck",
                "BLOCK",
                "ARCHIVE gate requires Final Status = PASS (close review).",
                {**details, "final_status": final_status},
            )
        if normalized != "PASS":
            return CheckResult(
                "flowcheck",
                "BLOCK",
                "ARCHIVE gate requires Plan Review PASS as prerequisite.",
                {**details, "final_status": final_status},
            )
        return CheckResult("flowcheck", "OK", "Archive gate signals present (Final PASS, Plan PASS).", {**details, "final_status": final_status})

    # general intent: warn only
    if normalized == "PASS":
        return CheckResult("flowcheck", "OK", "Plan Review PASS.", details)
    if build_started and exception_norm in {"NONE", "", "CLOSED"}:
        return CheckResult(
            "flowcheck",
            "WARN",
            "Build activity detected while Plan Review is not PASS (and no active exception).",
            details,
        )
    return CheckResult("flowcheck", "WARN", f"Plan Review not PASS ({review_status}).", details)


def lint_checks(workflow_path: Path) -> CheckResult:
    wf_text = read_text(workflow_path)
    fm = parse_frontmatter(wf_text)
    secs = split_sections(wf_text)
    root = repo_root_from_workflow(workflow_path)

    problems: List[str] = []
    details: Dict[str, Any] = {"root": str(root), "workflow": str(workflow_path)}

    # Plan path
    plan_path = fm.get("plan_doc")
    plan_status = get_section(secs, exact=["2) Plan Status（S2）", "3) Plan Status"], contains=["Plan Status"])
    plan_path2 = find_in_section(plan_status, r"^\s*-\s*Plan Doc Path:\s*(.+?)\s*$")
    plan_rel = plan_path2 or plan_path
    details["plan_path"] = plan_rel
    if plan_rel:
        plan_abs = (root / plan_rel).resolve()
        if not plan_abs.exists():
            problems.append(f"Plan doc not found: {plan_rel}")
    else:
        problems.append("Missing plan_doc in frontmatter and Plan Doc Path in Plan Status section.")

    # Index and AGENTS existence
    idx = root / ".agentdocs" / "index.md"
    if not idx.exists():
        problems.append("Missing .agentdocs/index.md")
    else:
        text = read_text(idx)
        defaults = re.findall(r"^\s*-\s*DEFAULT:\s*(\S+)", text, flags=re.MULTILINE)
        details["index_defaults"] = defaults
        details["index_has_current_task_section"] = "## 2) 当前任务（SSOT）" in text
        details["index_has_legacy_active_tasks"] = bool(LEGACY_ACTIVE_TASKS_RE.search(text))
        if len(defaults) > 1:
            problems.append(f"Multiple DEFAULT workflows in index.md: {defaults}")
        if "## 2) 当前任务（SSOT）" in text and LEGACY_ACTIVE_TASKS_RE.search(text):
            problems.append("index.md mixes canonical current-task section with legacy Active Tasks format.")
        if "## 2) 当前任务（SSOT）" not in text and not LEGACY_ACTIVE_TASKS_RE.search(text):
            problems.append("index.md is missing both canonical current-task section and legacy Active Tasks block.")

    agents_md = root / "AGENTS.md"
    if not agents_md.exists():
        problems.append("Missing AGENTS.md")

    # Evidence refs: if path exists, ensure it exists
    phase_sec = get_section(
        secs,
        exact=["3) Phase Board（执行状态 SSOT）", "4) Phase Board（执行状态 SSOT）"],
        contains=["Phase Board"],
    )
    rows = parse_phase_table(phase_sec)
    missing_evidence: List[str] = []
    for r in rows:
        status = (r.get("Status") or "").upper()
        owner = (r.get("Owner") or "").strip()
        verify_value = (r.get("Verify Run") or r.get("Verification") or "").strip()
        ev_raw = (r.get("Evidence Ref") or "").strip()
        ev = normalize_ref(ev_raw)
        if owner in {"plan_reviewer", "close_reviewer"}:
            problems.append(f"Phase Board should track execution phases only, not review gates (phase={r.get('Phase')}).")
        if ev:
            if "/reviews/" in ev:
                problems.append(f"Evidence Ref must point to evidence bundle, not review bundle (phase={r.get('Phase')}).")
            ev_abs = (root / ev).resolve()
            if not ev_abs.exists():
                missing_evidence.append(ev)
        if status in {"DONE", "COMPLETE"}:
            if not verify_value:
                problems.append(f"Phase marked {status} but Verification is empty (phase={r.get('Phase')}).")
            if not ev_raw:
                problems.append(f"Phase marked {status} but Evidence Ref is empty (phase={r.get('Phase')}).")

    if missing_evidence:
        problems.append(f"Evidence Ref paths do not exist: {missing_evidence}")

    details["problems"] = problems

    if problems:
        return CheckResult("lint", "WARN", "Found lint issues in agentdocs references.", details)
    return CheckResult("lint", "OK", "Basic agentdocs references look consistent.", details)


def coverage_check(workflow_path: Path) -> CheckResult:
    wf_text = read_text(workflow_path)
    secs = split_sections(wf_text)

    # V3: Align has Context Coverage fields.
    # V2: Align had Coverage Proof block.
    align = get_section(secs, exact=["1) Align（S1）", "1) Align"], contains=["Align"])

    v3_must_have = [
        "Must Read",
        "Adjacent Scan",
        "Unread But Potentially Relevant",
        "Coverage Decision",
    ]

    v2_must_have = [
        "Coverage Proof",
        "Must-read",
        "Adjacency Scan",
        "Residual",
    ]

    text = align.lower()
    missing_v3 = [k for k in v3_must_have if k.lower() not in text]
    missing_v2 = [k for k in v2_must_have if k.lower() not in text]

    # Accept either style.
    if len(missing_v3) < len(v3_must_have):
        missing = missing_v3
        style = "v3"
    else:
        missing = missing_v2
        style = "v2"

    details: Dict[str, Any] = {
        "style": style,
        "missing_anchors": missing,
    }

    if missing:
        return CheckResult(
            "coverage",
            "WARN",
            "Coverage block missing or incomplete (expected anchors for the chosen template style).",
            details,
        )
    return CheckResult("coverage", "OK", "Coverage anchors present.", details)


def render_human_summary(status: str, checks: List[CheckResult]) -> str:
    lines = [f"agentdocs_check: {status}"]
    for c in checks:
        lines.append(f"- {c.name}: {c.status} — {c.message}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", required=True, help="Path to workflow markdown")
    ap.add_argument("--mode", choices=["flowcheck", "lint", "coverage", "all"], default="all")
    ap.add_argument("--intent", choices=["build", "archive", "general"], default="general")
    ap.add_argument("--out", default="", help="Write JSON result to this path")
    args = ap.parse_args()

    wf = Path(args.workflow)
    if not wf.exists():
        print(f"ERROR: workflow not found: {wf}")
        sys.exit(3)

    checks: List[CheckResult] = []
    try:
        if args.mode in {"flowcheck", "all"}:
            checks.append(flowcheck(wf, intent=args.intent))
        if args.mode in {"lint", "all"}:
            checks.append(lint_checks(wf))
        if args.mode in {"coverage", "all"}:
            checks.append(coverage_check(wf))

        # Aggregate status precedence: BLOCK > EXCEPTION_ALLOWED > WARN > OK
        precedence = {"BLOCK": 3, "EXCEPTION_ALLOWED": 2, "WARN": 1, "OK": 0}
        worst = max(checks, key=lambda c: precedence.get(c.status, 1)).status if checks else "OK"

        out: Dict[str, Any] = {
            "status": worst,
            "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "workflow": str(wf),
            "checks": [
                {"name": c.name, "status": c.status, "message": c.message, "details": c.details}
                for c in checks
            ],
            "suggested_next_steps": [],
            "tool_version": "v3x-v2-crossfused",
        }

        # Suggestions
        if any(c.status == "BLOCK" for c in checks):
            out["suggested_next_steps"].append(
                "Fix BLOCKing issues, or explicitly enter Exception Recovery in workflow and tighten Close Review."
            )
        if any(c.name == "coverage" and c.status != "OK" for c in checks):
            out["suggested_next_steps"].append(
                "Fill Context Coverage (Must Read / Adjacent Scan / Unread Risk / Coverage Decision) before claiming sufficient context."
            )
        if any(c.name == "lint" and c.status != "OK" for c in checks):
            out["suggested_next_steps"].append(
                "Fix missing references (plan path, evidence bundle paths, index DEFAULT uniqueness)."
            )

        print(render_human_summary(worst, checks))

        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        if worst == "BLOCK":
            sys.exit(2)
        sys.exit(0)

    except Exception as e:  # noqa
        print(f"ERROR: unexpected failure: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
