#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

TZ = timezone(timedelta(hours=8))

LEGAL_TRANSITIONS = {
    "DISCUSS": {"ALIGN_PROOF", "EXCEPTION_RECOVERY"},
    "ALIGN_PROOF": {"BOOTSTRAP", "EXCEPTION_RECOVERY"},
    "BOOTSTRAP": {"ISSUE_SYNC", "EXCEPTION_RECOVERY"},
    "ISSUE_SYNC": {"PLAN_DRAFT", "EXCEPTION_RECOVERY"},
    "PLAN_DRAFT": {"PLAN_REVIEW", "EXCEPTION_RECOVERY"},
    "PLAN_REVIEW": {"PLAN_DRAFT", "BUILD", "EXCEPTION_RECOVERY"},
    "BUILD": {"BUILD", "PLAN_DRAFT", "CLOSE_REVIEW", "BLOCKED", "EXCEPTION_RECOVERY"},
    "CLOSE_REVIEW": {"BUILD", "ARCHIVE", "BLOCKED", "EXCEPTION_RECOVERY"},
    "ARCHIVE": set(),
    "BLOCKED": {"DISCUSS", "ALIGN_PROOF", "BOOTSTRAP", "ISSUE_SYNC", "PLAN_DRAFT", "PLAN_REVIEW", "BUILD", "CLOSE_REVIEW", "EXCEPTION_RECOVERY"},
    "EXCEPTION_RECOVERY": {"DISCUSS", "ALIGN_PROOF", "PLAN_DRAFT", "PLAN_REVIEW", "BUILD", "CLOSE_REVIEW", "BLOCKED"},
}

ILLEGAL_DIRECT = {
    ("DISCUSS", "PLAN_DRAFT"),
    ("ALIGN_PROOF", "BUILD"),
    ("PLAN_DRAFT", "BUILD"),
    ("PLAN_REVIEW", "CLOSE_REVIEW"),
    ("BUILD", "ARCHIVE"),
    ("EXCEPTION_RECOVERY", "ARCHIVE"),
}

REQUIRED_PACK_SECTIONS = [
    "## Identity",
    "## Understanding Proof",
    "## Source Pointers",
    "## Frozen Context",
    "## Read Boundary",
    "## Current Truth Anchors",
    "## Action Boundary",
    "## Invariants",
    "## Verification",
]

REQUIRED_BRIEF_SECTIONS = [
    "## Identity",
    "## Boundary",
    "## Objective",
    "## Procedure",
    "## Output Contract",
    "## Escalation",
]

SKILL_ALLOWED_FRONTMATTER_KEYS = {"name", "description"}
SKILL_FORBIDDEN_BODY_HEADINGS = [
    "## When to use",
    "## When NOT to use",
]
SKILL_FORBIDDEN_AUX_FILES = {
    "README.md",
    "INSTALLATION_GUIDE.md",
    "QUICK_REFERENCE.md",
    "CHANGELOG.md",
}
SKILL_MAX_BODY_LINES = 500
CURRENT_TASKS_SECTION_MARKER = "## 2) 当前任务（SSOT）"
ARCHIVE_INDEX_SECTION_MARKER = "## Archived Tasks"
CURRENT_TASK_ENTRY_RE = re.compile(r"^- (?P<kind>DEFAULT|ACTIVE): (?P<path>\S+) — (?P<title>.+)$")
ARCHIVE_ENTRY_RE = re.compile(r"^- (?P<task_id>\S+): (?P<title>.+?) — (?P<workflow>\S+) — (?P<archived_at>.+)$")
LEGACY_ACTIVE_TASKS_RE = re.compile(r"## Active Tasks\n(?P<body>[\s\S]*?)(?:\n## |\Z)")
PLACEHOLDER_VALUES = {"<fill-me>", "<none>", "", "NONE", "N/A", "<none>"}
VALID_REVIEW_MODES = {"FULL_REVIEW", "DELTA_REVIEW", "FORMAT_ONLY"}
VALID_BUILD_SCOPES = {"APPROVED_SCOPE", "FINDINGS_ONLY", "FORMAT_ONLY"}
STATE_ORDER = [
    "DISCUSS",
    "ALIGN_PROOF",
    "BOOTSTRAP",
    "ISSUE_SYNC",
    "PLAN_DRAFT",
    "PLAN_REVIEW",
    "BUILD",
    "CLOSE_REVIEW",
    "BLOCKED",
    "EXCEPTION_RECOVERY",
    "ARCHIVE",
]
WORKFLOW_STATUS_BY_STATE = {
    "BLOCKED": "blocked",
    "ARCHIVE": "archived",
}


def now_str() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M %z")


def ensure_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_json(path: Path, payload: dict) -> None:
    ensure_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def load_template(root: Path, name: str) -> str:
    return (root / ".codex" / "workflow" / "templates" / name).read_text(encoding="utf-8")


def repo_root_from_path(path: Path) -> Path:
    resolved = path.resolve()
    parts = list(resolved.parts)
    if ".agentdocs" in parts:
        idx = parts.index(".agentdocs")
        return Path(*parts[:idx])
    return resolved.parent


def rel_to_root(root: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(resolved)


def find_in_text(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else None


def transition_status(src: str, dst: str) -> tuple[bool, str]:
    if (src, dst) in ILLEGAL_DIRECT:
        return False, f"illegal direct transition {src} -> {dst}"
    if dst in LEGAL_TRANSITIONS.get(src, set()):
        return True, f"legal transition {src} -> {dst}"
    return False, f"unsupported transition {src} -> {dst}"


def order_states(states: Iterable[str]) -> list[str]:
    rank = {state: idx for idx, state in enumerate(STATE_ORDER)}
    return sorted(states, key=lambda state: (rank.get(state, len(rank)), state))


def workflow_label_value(text: str, label: str) -> str:
    return find_in_text(text, rf"^\s*-\s*{re.escape(label)}:\s*(.+?)\s*$") or ""


def replace_front_matter_field(text: str, field: str, value: str) -> str:
    pattern = re.compile(rf"^(?P<prefix>{re.escape(field)}:\s*).*$", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(lambda match: f"{match.group('prefix')}{value}", text, count=1)
    if text.startswith("---\n"):
        return text.replace("---\n", f"---\n{field}: {value}\n", 1)
    return text


def workflow_status_for_state(state: str) -> str:
    return WORKFLOW_STATUS_BY_STATE.get(state, "active")


def resolve_allowed_next_state(state: str, requested: str) -> str:
    legal = LEGAL_TRANSITIONS.get(state, set())
    if not legal:
        if requested and requested.strip() not in PLACEHOLDER_VALUES and requested.strip() not in {"<none>", "<NONE>"}:
            print(f"BLOCK: state {state} is terminal and does not allow --allowed-next-state")
            raise SystemExit(2)
        return "<none>"

    if requested and requested.strip() not in PLACEHOLDER_VALUES:
        requested_states = [item.strip() for item in requested.split("|") if item.strip()]
        invalid = [item for item in requested_states if item not in legal]
        if invalid:
            options = " | ".join(order_states(legal))
            print(f"BLOCK: invalid --allowed-next-state for {state}: {invalid}; choose from {options}")
            raise SystemExit(2)
        return " | ".join(order_states(dict.fromkeys(requested_states)))

    return " | ".join(order_states(legal))


def _default_index_text(root: Path) -> str:
    try:
        return load_template(root, "index.template.md")
    except FileNotFoundError:
        return (
            "# .agentdocs/index.md（入口地图 / Context Map）\n\n"
            "## 2) 当前任务（SSOT）\n"
            "<!-- DEFAULT = 新会话默认先读的 workflow；同一时间应尽量只有一个 DEFAULT -->\n"
            "<!-- ACTIVE = 并行任务，仅在明确允许并行时保留 -->\n"
            "<!-- NONE -->\n"
        )


def _default_archive_index_text(root: Path) -> str:
    try:
        return load_template(root, "archive-index.template.md")
    except FileNotFoundError:
        return "# Archive Index\n\n## Archived Tasks\n<!-- NONE -->\n"


def ensure_index_files(root: Path) -> tuple[Path, Path]:
    agentdocs = root / ".agentdocs"
    agentdocs.mkdir(parents=True, exist_ok=True)
    archive_dir = agentdocs / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    index_path = agentdocs / "index.md"
    archive_index_path = archive_dir / "index.md"
    if not index_path.exists():
        ensure_text(index_path, _default_index_text(root))
    if not archive_index_path.exists():
        ensure_text(archive_index_path, _default_archive_index_text(root))
    return index_path, archive_index_path


def split_markdown_section(text: str, marker: str) -> tuple[list[str], list[str], list[str]]:
    lines = text.splitlines()
    before, section, after = [], [], []
    state = "before"
    for line in lines:
        if state == "before":
            before.append(line)
            if line.strip() == marker:
                state = "section"
        elif state == "section":
            if line.startswith("## ") and line.strip() != marker:
                after.append(line)
                state = "after"
            else:
                section.append(line)
        else:
            after.append(line)
    return before, section, after


def parse_current_task_entries(index_text: str) -> list[dict]:
    _, section, _ = split_markdown_section(index_text, CURRENT_TASKS_SECTION_MARKER)
    entries = []
    for line in section:
        m = CURRENT_TASK_ENTRY_RE.match(line.strip())
        if m:
            entries.append(
                {
                    "kind": m.group("kind"),
                    "path": m.group("path"),
                    "title": m.group("title"),
                }
            )
    if entries:
        return entries

    legacy = LEGACY_ACTIVE_TASKS_RE.search(index_text)
    if not legacy:
        return []

    body = legacy.group("body")
    workflow = find_in_text(body, r"^\s*-\s*Workflow:\s*(.+?)\s*$")
    title = find_in_text(body, r"^\s*-\s*Title:\s*(.+?)\s*$")
    if workflow:
        return [{"kind": "DEFAULT", "path": workflow, "title": title or "Untitled Task"}]
    return []


def render_current_task_entries(entries: list[dict]) -> list[str]:
    lines = [
        CURRENT_TASKS_SECTION_MARKER,
        "<!-- DEFAULT = 新会话默认先读的 workflow；同一时间应尽量只有一个 DEFAULT -->",
        "<!-- ACTIVE = 并行任务，仅在明确允许并行时保留 -->",
    ]
    if not entries:
        lines.append("<!-- NONE -->")
        return lines
    default_entries = [entry for entry in entries if entry["kind"] == "DEFAULT"]
    active_entries = [entry for entry in entries if entry["kind"] == "ACTIVE"]
    for entry in default_entries + active_entries:
        lines.append(f"- {entry['kind']}: {entry['path']} — {entry['title']}")
    return lines


def write_current_task_entries(root: Path, entries: list[dict]) -> Path:
    index_path, _ = ensure_index_files(root)
    text = index_path.read_text(encoding="utf-8")
    before, _, after = split_markdown_section(text, CURRENT_TASKS_SECTION_MARKER)
    if not before:
        text = _default_index_text(root)
        before, _, after = split_markdown_section(text, CURRENT_TASKS_SECTION_MARKER)
    body = render_current_task_entries(entries)
    out_lines = before[:-1] + body if before else body
    if after:
        if out_lines and out_lines[-1] != "":
            out_lines.append("")
        out_lines.extend(after)
    ensure_text(index_path, "\n".join(out_lines).rstrip() + "\n")
    return index_path


def upsert_current_task_entry(root: Path, workflow_rel: str, title: str, kind: str = "DEFAULT") -> Path:
    index_path, _ = ensure_index_files(root)
    entries = parse_current_task_entries(index_path.read_text(encoding="utf-8"))
    entries = [entry for entry in entries if entry["path"] != workflow_rel]
    if kind == "DEFAULT":
        for entry in entries:
            if entry["kind"] == "DEFAULT":
                entry["kind"] = "ACTIVE"
        entries.insert(0, {"kind": "DEFAULT", "path": workflow_rel, "title": title})
    else:
        entries.append({"kind": "ACTIVE", "path": workflow_rel, "title": title})
    return write_current_task_entries(root, entries)


def remove_current_task_entry(root: Path, workflow_rel: str) -> Path:
    index_path, _ = ensure_index_files(root)
    entries = parse_current_task_entries(index_path.read_text(encoding="utf-8"))
    entries = [entry for entry in entries if entry["path"] != workflow_rel]
    if entries and not any(entry["kind"] == "DEFAULT" for entry in entries):
        entries[0]["kind"] = "DEFAULT"
    return write_current_task_entries(root, entries)


def parse_archive_entries(text: str) -> list[dict]:
    _, section, _ = split_markdown_section(text, ARCHIVE_INDEX_SECTION_MARKER)
    entries = []
    for line in section:
        m = ARCHIVE_ENTRY_RE.match(line.strip())
        if m:
            entries.append(
                {
                    "task_id": m.group("task_id"),
                    "title": m.group("title"),
                    "workflow": m.group("workflow"),
                    "archived_at": m.group("archived_at"),
                }
            )
    return entries


def write_archive_entry(root: Path, task_id: str, title: str, workflow_rel: str, archived_at: str) -> Path:
    _, archive_index_path = ensure_index_files(root)
    text = archive_index_path.read_text(encoding="utf-8")
    before, _, after = split_markdown_section(text, ARCHIVE_INDEX_SECTION_MARKER)
    if not before:
        text = _default_archive_index_text(root)
        before, _, after = split_markdown_section(text, ARCHIVE_INDEX_SECTION_MARKER)
    entries = [entry for entry in parse_archive_entries(text) if entry["task_id"] != task_id]
    entries.append(
        {
            "task_id": task_id,
            "title": title,
            "workflow": workflow_rel,
            "archived_at": archived_at,
        }
    )
    lines = [ARCHIVE_INDEX_SECTION_MARKER]
    if not entries:
        lines.append("<!-- NONE -->")
    else:
        for entry in entries:
            lines.append(
                f"- {entry['task_id']}: {entry['title']} — {entry['workflow']} — {entry['archived_at']}"
            )
    out_lines = before[:-1] + lines if before else lines
    if after:
        if out_lines and out_lines[-1] != "":
            out_lines.append("")
        out_lines.extend(after)
    ensure_text(archive_index_path, "\n".join(out_lines).rstrip() + "\n")
    return archive_index_path


def rewrite_task_scoped_paths_for_archive(task_root: Path) -> None:
    old_prefix = f".agentdocs/tasks/{task_root.name}/"
    new_prefix = f".agentdocs/archive/{task_root.name}/"
    text_suffixes = {".md", ".json", ".jsonl", ".txt"}
    for path in task_root.rglob("*"):
        if not path.is_file() or path.suffix not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8")
        if old_prefix in text:
            ensure_text(path, text.replace(old_prefix, new_prefix))


def find_heading_range(lines: list[str], heading_tokens: list[str]) -> tuple[int | None, int | None]:
    start = None
    for idx, line in enumerate(lines):
        if line.startswith("## ") and any(token in line for token in heading_tokens):
            start = idx
            break
    if start is None:
        return None, None
    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if lines[idx].startswith("## "):
            end = idx
            break
    return start, end


def update_labeled_section_lines(lines: list[str], start: int, end: int, updates: list[tuple[str, str]]) -> list[str]:
    section = lines[start:end]
    for label, value in updates:
        prefix = f"- {label}:"
        replaced = False
        for idx in range(1, len(section)):
            if section[idx].startswith(prefix):
                section[idx] = f"{prefix} {value}"
                replaced = True
                break
        if not replaced:
            section.append(f"{prefix} {value}")
    return lines[:start] + section + lines[end:]


def update_workflow_review_section(workflow: Path, kind: str, review_rel: str, args) -> None:
    lines = workflow.read_text(encoding="utf-8").splitlines()
    heading_tokens = ["Plan Review"] if kind == "plan" else ["Final Review"]
    start, end = find_heading_range(lines, heading_tokens)
    if start is None or end is None:
        print(f"BLOCK: workflow review section not found for kind={kind}")
        raise SystemExit(2)

    if kind == "plan":
        updates = [
            ("Reviewer Session", review_rel),
            ("Review Mode Used", args.review_mode),
            ("Decision", args.decision),
            ("Summary", args.summary),
            ("Required Changes", args.required_changes),
            ("Evidence", args.evidence),
            ("Recheck Scope", args.recheck_scope),
            ("Global Impact", args.global_impact),
            ("Open Questions", args.open_questions),
            ("Materials Accessed", "; ".join(list_or_default(args.material_accessed, [])) or "<none>"),
        ]
    else:
        updates = [
            ("Reviewer Session", review_rel),
            ("Review Mode Used", args.review_mode),
            ("Final Status", args.decision),
            ("Key Findings", args.summary),
            ("Required Follow-ups", args.required_changes),
            ("Evidence Summary", args.evidence),
            ("Recheck Scope", args.recheck_scope),
            ("Global Impact", args.global_impact),
            ("Archive Actions", args.archive_actions),
            ("Materials Accessed", "; ".join(list_or_default(args.material_accessed, [])) or "<none>"),
        ]

    ensure_text(workflow, "\n".join(update_labeled_section_lines(lines, start, end, updates)).rstrip() + "\n")


def update_workflow_plan_status_section(workflow: Path, kind: str, args, recorded_at: str) -> None:
    if kind != "plan":
        return

    lines = workflow.read_text(encoding="utf-8").splitlines()
    start, end = find_heading_range(lines, ["Plan Status"])
    if start is None or end is None:
        print("BLOCK: workflow plan status section not found")
        raise SystemExit(2)

    updates = [
        ("Review Status", args.decision),
        ("Current Review Round", str(args.round)),
    ]
    if args.decision == "PASS":
        updates.append(("Approved At", recorded_at))
    lines = update_labeled_section_lines(lines, start, end, updates)
    ensure_text(workflow, "\n".join(lines).rstrip() + "\n")


def update_workflow_runtime_pointer_section(workflow: Path, updates: list[tuple[str, str]]) -> None:
    lines = workflow.read_text(encoding="utf-8").splitlines()
    start, end = find_heading_range(lines, ["Runtime Pointers", "Runtime / Task Pack"])
    if start is None or end is None:
        return
    lines = update_labeled_section_lines(lines, start, end, updates)
    ensure_text(workflow, "\n".join(lines).rstrip() + "\n")


def update_workflow_state_header(
    workflow: Path,
    *,
    current_state: str,
    allowed_next_state: str,
    exception_status: str,
    owner: str,
    transition_check: str,
    illegal_transition_seen: str,
    updated_at: str,
) -> None:
    text = workflow.read_text(encoding="utf-8")
    text = replace_front_matter_field(text, "status", workflow_status_for_state(current_state))
    text = replace_front_matter_field(text, "updated_at", updated_at)
    lines = text.splitlines()

    start, end = find_heading_range(lines, ["状态头部"])
    if start is None or end is None:
        print("BLOCK: workflow state header section not found")
        raise SystemExit(2)
    lines = update_labeled_section_lines(
        lines,
        start,
        end,
        [
            ("Current State", current_state),
            ("Allowed Next State", allowed_next_state),
            ("Exception Status", exception_status),
            ("Last Updated", updated_at),
        ],
    )

    start, end = find_heading_range(lines, ["Workflow State Machine"])
    if start is None or end is None:
        print("BLOCK: workflow state machine section not found")
        raise SystemExit(2)
    lines = update_labeled_section_lines(
        lines,
        start,
        end,
        [
            ("Current State Owner", owner),
            ("Transition Check", transition_check),
            ("Illegal Transition Seen", illegal_transition_seen),
        ],
    )
    ensure_text(workflow, "\n".join(lines).rstrip() + "\n")


def render_evidence_block(args) -> str:
    lines = [
        f"### {args.evidence_id}",
        f"- Evidence ID: {args.evidence_id}",
        f"- Phase: {args.phase}",
        f"- Purpose: {args.purpose}",
        f"- Command: {args.command}",
        f"- CWD: {args.cwd}",
        f"- Ran At: {args.ran_at or now_str()}",
        f"- Exit Code: {args.exit_code}",
        f"- Result: {args.result}",
        f"- Output Path: {args.output_path}",
        f"- Output Excerpt: {args.output_excerpt}",
        "- Related Artifacts:",
    ]
    related = list_or_default(args.related_artifact, [])
    if related:
        lines.extend([f"  - {item}" for item in related])
    else:
        lines.append("  - <none>")
    lines.extend(
        [
            f"- Notes: {args.notes}",
            f"- Reviewer Recheck: {args.reviewer_recheck}",
        ]
    )
    if args.result == "DEGRADED":
        lines.extend(
            [
                f"- Why: {args.why}",
                f"- Instead: {args.instead}",
                f"- To Run Later: {args.to_run_later}",
            ]
        )
    return "\n".join(lines)


def upsert_workflow_evidence_ledger(workflow: Path, args) -> None:
    lines = workflow.read_text(encoding="utf-8").splitlines()
    start, end = find_heading_range(lines, ["Evidence Ledger"])
    if start is None or end is None:
        print("BLOCK: Evidence Ledger section not found")
        raise SystemExit(2)

    section = lines[start:end]
    block = render_evidence_block(args).splitlines()
    placeholder_start = None
    placeholder_end = None
    existing_start = None
    existing_end = None

    idx = 1
    while idx < len(section):
        line = section[idx]
        if line.startswith("### "):
            block_start = idx
            block_end = len(section)
            for jdx in range(idx + 1, len(section)):
                if section[jdx].startswith("### ") or section[jdx].startswith("## "):
                    block_end = jdx
                    break
            heading = line.removeprefix("### ").strip()
            if heading == args.evidence_id:
                existing_start, existing_end = block_start, block_end
                break
            if placeholder_start is None:
                for probe in section[block_start:block_end]:
                    if probe.strip() in {"- Evidence ID:", "- Evidence ID: "}:
                        placeholder_start, placeholder_end = block_start, block_end
                        break
            idx = block_end
            continue
        idx += 1

    if existing_start is not None and existing_end is not None:
        section = section[:existing_start] + block + section[existing_end:]
    elif placeholder_start is not None and placeholder_end is not None:
        section = section[:placeholder_start] + block + section[placeholder_end:]
    else:
        if section and section[-1] != "":
            section.append("")
        section.extend(block)

    ensure_text(workflow, "\n".join(lines[:start] + section + lines[end:]).rstrip() + "\n")


def first_non_placeholder(items: list[str] | None) -> str | None:
    for item in items or []:
        stripped = item.strip()
        if stripped and stripped not in PLACEHOLDER_VALUES:
            return stripped
    return None


def list_or_default(value, default):
    return value if value else default


def bullet_block(items: Iterable[str]) -> str:
    return "\n".join(f"  - {item}" for item in items)


def phase_control_line(phase: str, review_mode: str, build_scope: str) -> str:
    if phase == "BUILD":
        return f"- Build Scope: {build_scope}"
    return f"- Review Mode: {review_mode}"


def slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "item"


def cmd_check_transition(args):
    src, dst = args.from_state, args.to_state
    ok, detail = transition_status(src, dst)
    if ok:
        print(f"OK: {detail}")
        return 0
    print(f"BLOCK: {detail}")
    return 2


def append_workflow_event(workflow: Path, kind: str, message: str, event_time: str) -> None:
    text = workflow.read_text(encoding="utf-8")
    entry = f"- {event_time} — [{kind}] {message}"

    if "## 5) Build Log" not in text:
        print("BLOCK: Build Log section not found")
        raise SystemExit(2)

    text = text.replace("- YYYY-MM-DD HH:MM — ...", f"- YYYY-MM-DD HH:MM — ...\n{entry}", 1)
    ensure_text(workflow, text)

    events_path = workflow.parent / "runtime-events.jsonl"
    with events_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"at": event_time, "kind": kind, "message": message}, ensure_ascii=False) + "\n")


def cmd_advance_state(args):
    workflow = Path(args.workflow).resolve()
    text = workflow.read_text(encoding="utf-8")
    current_state = workflow_label_value(text, "Current State")
    if not current_state:
        print("BLOCK: workflow missing Current State")
        return 2

    if args.from_state and args.from_state != current_state:
        print(f"BLOCK: workflow current state is {current_state}, not {args.from_state}")
        return 2

    dst = args.to_state
    ok, detail = transition_status(current_state, dst)
    if not ok:
        print(f"BLOCK: {detail}")
        return 2

    review_status = workflow_label_value(text, "Review Status")
    final_status = workflow_label_value(text, "Final Status")
    if dst == "BUILD" and review_status != "PASS":
        print("BLOCK: BUILD requires Review Status = PASS in workflow.md")
        return 2
    if dst == "ARCHIVE":
        if final_status != "PASS":
            print("BLOCK: ARCHIVE requires Final Status = PASS in workflow.md")
            return 2
        if "/.agentdocs/archive/" not in workflow.as_posix():
            print("BLOCK: ARCHIVE requires the workflow to already live under .agentdocs/archive/")
            return 2

    updated_at = args.at or now_str()
    exception_status = args.exception_status.strip() if args.exception_status.strip() else ("ACTIVE" if dst == "EXCEPTION_RECOVERY" else "NONE")
    if dst != "EXCEPTION_RECOVERY" and exception_status != "NONE":
        print("BLOCK: non-exception states must use Exception Status = NONE")
        return 2

    illegal_transition_seen = args.illegal_transition_seen
    if illegal_transition_seen == "YES" and exception_status == "NONE":
        print("BLOCK: Illegal Transition Seen = YES requires Exception Status != NONE")
        return 2

    allowed_next_state = resolve_allowed_next_state(dst, args.allowed_next_state)
    transition_check = f"PASS ({current_state} -> {dst}; {args.reason})"
    update_workflow_state_header(
        workflow,
        current_state=dst,
        allowed_next_state=allowed_next_state,
        exception_status=exception_status,
        owner=args.owner,
        transition_check=transition_check,
        illegal_transition_seen=illegal_transition_seen,
        updated_at=updated_at,
    )
    append_workflow_event(
        workflow,
        "STATE",
        f"{current_state} -> {dst}; next = {allowed_next_state}; owner = {args.owner}; reason = {args.reason}",
        updated_at,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "workflow": str(workflow),
                "from": current_state,
                "to": dst,
                "allowed_next_state": allowed_next_state,
                "exception_status": exception_status,
                "illegal_transition_seen": illegal_transition_seen,
                "updated_at": updated_at,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_create_task(args):
    root = Path(args.root).resolve()
    task_root = root / ".agentdocs" / "tasks" / args.task_id
    if task_root.exists() and any(task_root.iterdir()) and not args.force:
        print(f"BLOCK: task root already exists: {task_root}")
        return 2

    for sub in ["task-packs", "reviews", "evidence", "scratch", "findings"]:
        (task_root / sub).mkdir(parents=True, exist_ok=True)

    updated_at = now_str()
    repl = {
        "<task-id>": args.task_id,
        "<task-slug>": args.slug,
        "<task-title>": args.title,
        "<issue-url-or-na>": args.issue,
        "<updated-at>": updated_at,
    }
    for name in ["workflow.v2.template.md", "plan.v2.template.md"]:
        text = load_template(root, name)
        for key, val in repl.items():
            text = text.replace(key, val)
        target = task_root / ("workflow.md" if name.startswith("workflow") else "plan.md")
        ensure_text(target, text)

    print(task_root)
    return 0


def cmd_make_pack(args):
    root = Path(args.root).resolve()
    task_root = Path(args.task_root).resolve()
    rendered = load_template(root, "task-pack.template.md")

    repl = {
        "<task-id>": args.task_id,
        "<title>": args.title,
        "<phase>": args.phase,
        "<current-state>": args.current_state,
        "<allowed-next-state>": args.allowed_next_state,
        "<owner>": args.owner,
        "<goal>": args.goal,
        "<understanding>": args.understanding,
        "<coverage>": args.coverage,
        "<phase-control-line>": phase_control_line(args.phase, args.review_mode, args.build_scope),
        "<escalation-rule>": args.escalation_rule,
    }
    for key, val in repl.items():
        rendered = rendered.replace(key, val)

    mapping = {
        "<non-goal-1>": list_or_default(args.non_goal, ["<none>"]),
        "<missing-1>": list_or_default(args.missing_piece, ["<none>"]),
        "<spec-source-1>": list_or_default(args.spec_source, ["<fill-me>"]),
        "<review-input-1>": list_or_default(args.review_input, ["<none>"]),
        "<decision-1>": list_or_default(args.frozen_decision, ["<fill-me>"]),
        "<non-reopen-1>": list_or_default(args.non_reopen, ["<none>"]),
        "<risk-1>": list_or_default(args.risk, ["<none>"]),
        "<finding-1>": list_or_default(args.previous_finding, ["<none>"]),
        "<invariant-1>": list_or_default(args.invariant, ["<fill-me>"]),
        "<must-read-1>": list_or_default(args.must_read, ["AGENTS.md"]),
        "<adjacent-1>": list_or_default(args.adjacent, ["<none>"]),
        "<unread-1>": list_or_default(args.unread, ["<none>"]),
        "<code-path-1>": list_or_default(args.code_path, ["<fill-me>"]),
        "<symbol-1>": list_or_default(args.symbol, ["<fill-me>"]),
        "<test-1>": list_or_default(args.test_anchor, ["<fill-me>"]),
        "<runtime-1>": list_or_default(args.runtime_anchor, ["<fill-me>"]),
        "<write-boundary-1>": list_or_default(args.write_boundary, ["NONE"]),
        "<forbidden-1>": list_or_default(args.forbidden_write, ["workflow state headers", "canonical plan"]),
        "<must-have-1>": list_or_default(args.must_have, ["<fill-me>"]),
        "<verification-1>": list_or_default(args.verification, ["<fill-me>"]),
        "<recheck-1>": list_or_default(args.recheck, ["<fill-me>"]),
        "<uat-1>": list_or_default(args.uat, ["<fill-me>"]),
    }
    for key, items in mapping.items():
        rendered = rendered.replace(f"  - {key}", bullet_block(items))
        rendered = rendered.replace(f"- {key}", bullet_block(items))

    out = task_root / "task-packs" / f"{args.phase}-task-pack.md"
    ensure_text(out, rendered)
    print(out)
    return 0


def cmd_validate_pack(args):
    pack = Path(args.pack).resolve()
    if not pack.exists():
        print(f"BLOCK: pack not found: {pack}")
        return 2

    text = pack.read_text(encoding="utf-8")
    missing = [section for section in REQUIRED_PACK_SECTIONS if section not in text]
    invalid = []
    detail_checks = {
        "Task ID": "- Task ID:",
        "Phase": "- Phase:",
        "Goal": "- Goal Restatement:",
        "Spec Source": "- Spec Source:",
        "Write Boundary": "- Write Boundary:",
        "Verification Obligations": "- Verification Obligations:",
    }
    for label, marker in detail_checks.items():
        if marker not in text:
            missing.append(label)

    goal_match = re.search(r"^- Goal Restatement:\s*(.+)$", text, re.MULTILINE)
    goal_value = goal_match.group(1).strip() if goal_match else ""
    if goal_value in {"", "<fill-me>"}:
        invalid.append("Goal Restatement: requires a non-placeholder value")

    understanding_match = re.search(r"^- 95% Understanding Check:\s*(.+)$", text, re.MULTILINE)
    understanding_value = understanding_match.group(1).strip() if understanding_match else ""
    if understanding_value != "YES":
        invalid.append(f"95% Understanding Check: expected 'YES', got '{understanding_value or '<missing>'}'")

    phase_match = re.search(r"^- Phase:\s*(.+)$", text, re.MULTILINE)
    phase_value = phase_match.group(1).strip() if phase_match else ""
    review_mode_match = re.search(r"^- Review Mode:\s*(.+)$", text, re.MULTILINE)
    review_mode_value = review_mode_match.group(1).strip() if review_mode_match else ""
    build_scope_match = re.search(r"^- Build Scope:\s*(.+)$", text, re.MULTILINE)
    build_scope_value = build_scope_match.group(1).strip() if build_scope_match else ""

    if phase_value == "BUILD":
        if "- Build Scope:" not in text:
            missing.append("Build Scope")
        if build_scope_value not in VALID_BUILD_SCOPES:
            invalid.append(
                f"Build Scope: expected one of {sorted(VALID_BUILD_SCOPES)}, got '{build_scope_value or '<missing>'}'"
            )
        if review_mode_value:
            invalid.append("Review Mode: BUILD packs must not declare Review Mode")
    elif phase_value in {"PLAN_REVIEW", "CLOSE_REVIEW"}:
        if "- Review Mode:" not in text:
            missing.append("Review Mode")
        if review_mode_value not in VALID_REVIEW_MODES:
            invalid.append(
                f"Review Mode: expected one of {sorted(VALID_REVIEW_MODES)}, got '{review_mode_value or '<missing>'}'"
            )
        if build_scope_value:
            invalid.append("Build Scope: review packs must not declare Build Scope")

    coverage_match = re.search(r"^- Coverage Decision:\s*(.+)$", text, re.MULTILINE)
    coverage_value = coverage_match.group(1).strip() if coverage_match else ""
    if coverage_value not in {"SUFFICIENT", "PARTIAL"}:
        invalid.append(
            f"Coverage Decision: expected one of ['PARTIAL', 'SUFFICIENT'], got '{coverage_value or '<missing>'}'"
        )

    required_list_labels = {
        "Spec Source": re.search(r"- Spec Source:\n((?:\s{2}- .+\n?)*)", text),
        "Must Read": re.search(r"- Must Read:\n((?:\s{2}- .+\n?)*)", text),
        "Code Paths": re.search(r"- Code Paths:\n((?:\s{2}- .+\n?)*)", text),
        "Key Symbols / Entry Points": re.search(r"- Key Symbols / Entry Points:\n((?:\s{2}- .+\n?)*)", text),
        "Tests / Checks": re.search(r"- Tests / Checks:\n((?:\s{2}- .+\n?)*)", text),
        "Write Boundary": re.search(r"- Write Boundary:\n((?:\s{2}- .+\n?)*)", text),
        "Must-Haves": re.search(r"- Must-Haves:\n((?:\s{2}- .+\n?)*)", text),
        "Verification Obligations": re.search(r"- Verification Obligations:\n((?:\s{2}- .+\n?)*)", text),
        "Reviewer Recheck Plan": re.search(r"- Reviewer Recheck Plan:\n((?:\s{2}- .+\n?)*)", text),
        "UAT": re.search(r"- UAT:\n((?:\s{2}- .+\n?)*)", text),
    }
    for label, match in required_list_labels.items():
        items = re.findall(r"^\s{2}-\s*(.+)$", match.group(1), re.MULTILINE) if match else []
        if first_non_placeholder(items) is None:
            invalid.append(f"{label}: requires at least one non-placeholder entry")

    invariants_match = re.search(r"## Invariants\n((?:.*\n)*?)(?:\n## |\Z)", text)
    invariant_items = re.findall(r"^\s*-\s*(.+)$", invariants_match.group(1), re.MULTILINE) if invariants_match else []
    if first_non_placeholder(invariant_items) is None:
        invalid.append("Invariants: requires at least one non-placeholder entry")

    ok = not missing and not invalid
    payload = {"ok": ok, "pack": str(pack), "missing": missing, "invalid": invalid}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 2


def cmd_emit_delegation_brief(args):
    root = Path(args.root).resolve()
    task_root = Path(args.task_root).resolve()
    out = Path(args.output).resolve() if args.output else task_root / "scratch" / f"delegation-{slugify(args.role)}.md"
    rendered = load_template(root, "delegation-brief.template.md")

    repl = {
        "<role>": args.role,
        "<session-purpose>": args.session_purpose,
        "<task-pack>": args.task_pack,
        "<goal>": args.goal,
        "<phase-control-line>": phase_control_line(
            "BUILD" if args.build_scope else "REVIEW",
            args.review_mode,
            args.build_scope,
        ),
    }
    for key, val in repl.items():
        rendered = rendered.replace(key, val)

    mapping = {
        "<must-read-1>": list_or_default(args.must_read, [args.task_pack]),
        "<truth-anchor-1>": list_or_default(args.truth_anchor, ["<fill-me>"]),
        "<write-boundary-1>": list_or_default(args.write_boundary, ["NONE"]),
        "<forbidden-write-1>": list_or_default(args.forbidden_write, ["business code", "workflow state headers"]),
        "<output-line-1>": list_or_default(args.output_line, ["Provide a self-describing result bundle."]),
        "<escalation-line-1>": list_or_default(args.escalation_line, ["Escalate if task pack is stale or required anchors are missing."]),
    }
    for key, items in mapping.items():
        rendered = rendered.replace(f"  - {key}", bullet_block(items))
        rendered = rendered.replace(f"- {key}", bullet_block(items))

    ensure_text(out, rendered)
    brief_text = out.read_text(encoding="utf-8")
    missing = [section for section in REQUIRED_BRIEF_SECTIONS if section not in brief_text]
    if missing:
        print(json.dumps({"ok": False, "missing": missing, "path": str(out)}, ensure_ascii=False, indent=2))
        return 2

    print(out)
    return 0


def _render_plan_review(args) -> str:
    return (
        f"# Plan Review R{args.round}\n\n"
        f"- Decision: {args.decision}\n"
        f"- Summary: {args.summary}\n"
        f"- Required Changes: {args.required_changes}\n"
        f"- Evidence: {args.evidence}\n"
        f"- Recheck Scope: {args.recheck_scope}\n"
        f"- Review Mode Used: {args.review_mode}\n"
        f"- Global Impact: {args.global_impact}\n"
        f"- Open Questions: {args.open_questions}\n"
    )


def _render_close_review(args) -> str:
    return (
        f"# Close Review R{args.round}\n\n"
        f"- Final Status: {args.decision}\n"
        f"- Key Findings: {args.summary}\n"
        f"- Required Follow-ups: {args.required_changes}\n"
        f"- Evidence Summary: {args.evidence}\n"
        f"- Recheck Scope: {args.recheck_scope}\n"
        f"- Review Mode Used: {args.review_mode}\n"
        f"- Global Impact: {args.global_impact}\n"
        f"- Archive Actions: {args.archive_actions}\n"
    )


def cmd_record_review(args):
    task_root = Path(args.task_root).resolve()
    review_dir = task_root / "reviews"
    review_dir.mkdir(parents=True, exist_ok=True)

    kind = args.kind.lower()
    if kind not in {"plan", "close"}:
        print("BLOCK: --kind must be 'plan' or 'close'")
        return 2

    stem = f"{kind}-review-r{args.round}"
    json_path = review_dir / f"{stem}.json"

    if args.input:
        body_markdown = Path(args.input).read_text(encoding="utf-8")
    else:
        body_markdown = None

    recorded_at = now_str()
    payload = {
        "kind": kind,
        "round": args.round,
        "decision": args.decision,
        "summary": args.summary,
        "required_changes": args.required_changes,
        "evidence": args.evidence,
        "recheck_scope": args.recheck_scope,
        "review_mode": args.review_mode,
        "global_impact": args.global_impact,
        "open_questions": args.open_questions,
        "archive_actions": args.archive_actions,
        "materials_accessed": list_or_default(args.material_accessed, []),
        "recorded_at": recorded_at,
    }
    if body_markdown:
        payload["body_markdown"] = body_markdown

    ensure_json(json_path, payload)
    if args.workflow:
        workflow = Path(args.workflow).resolve()
        root = repo_root_from_path(task_root)
        update_workflow_review_section(workflow, kind, rel_to_root(root, json_path), args)
        update_workflow_plan_status_section(workflow, kind, args, recorded_at)
        pointer_label = "Latest Plan Review Ref" if kind == "plan" else "Latest Close Review Ref"
        update_workflow_runtime_pointer_section(
            workflow,
            [
                (pointer_label, rel_to_root(root, json_path)),
                ("Review Input", rel_to_root(root, json_path)),
            ],
        )
    print(json_path)
    return 0


def cmd_record_evidence(args):
    task_root = Path(args.task_root).resolve()
    evidence_dir = task_root / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    json_path = evidence_dir / f"{args.evidence_id}.json"
    related = list_or_default(args.related_artifact, [])
    ran_at = args.ran_at or now_str()

    if args.result == "DEGRADED":
        degraded_fields = {
            "why": args.why,
            "instead": args.instead,
            "to_run_later": args.to_run_later,
        }
        missing = [label for label, value in degraded_fields.items() if not value.strip()]
        if missing:
            print(f"BLOCK: DEGRADED evidence requires fields: {', '.join(missing)}")
            return 2

    payload = {
        "evidence_id": args.evidence_id,
        "phase": args.phase,
        "purpose": args.purpose,
        "command": args.command,
        "cwd": args.cwd,
        "ran_at": ran_at,
        "exit_code": args.exit_code,
        "result": args.result,
        "output_path": args.output_path,
        "output_excerpt": args.output_excerpt,
        "related_artifacts": related,
        "notes": args.notes,
        "reviewer_recheck": args.reviewer_recheck,
    }
    if args.result == "DEGRADED":
        payload.update(
            {
                "why": args.why,
                "instead": args.instead,
                "to_run_later": args.to_run_later,
            }
        )

    ensure_json(json_path, payload)
    if args.workflow:
        workflow = Path(args.workflow).resolve()
        upsert_workflow_evidence_ledger(workflow, argparse.Namespace(**{**vars(args), "ran_at": ran_at}))
        update_workflow_runtime_pointer_section(
            workflow,
            [("Latest Evidence Ref", rel_to_root(repo_root_from_path(task_root), json_path))],
        )
    print(json_path)
    return 0


def cmd_record_workflow_event(args):
    workflow = Path(args.workflow).resolve()
    event_time = args.at or now_str()
    append_workflow_event(workflow, args.kind, args.message, event_time)
    print(workflow)
    return 0


def cmd_sync_index(args):
    root = Path(args.root).resolve()
    workflow_rel = f".agentdocs/tasks/{args.task_id}/workflow.md"
    entry_kind = args.entry_kind
    if args.force_default:
        entry_kind = "DEFAULT"
    index_path = upsert_current_task_entry(root, workflow_rel, args.title, kind=entry_kind)
    print(index_path)
    return 0


def cmd_archive_task(args):
    task_root = Path(args.task_root).resolve()
    if not task_root.exists():
        print(f"BLOCK: task root not found: {task_root}")
        return 2

    workflow = task_root / "workflow.md"
    title = task_root.name
    if workflow.exists():
        wf_text = workflow.read_text(encoding="utf-8")
        title = find_in_text(wf_text, r"^title:\s*(.+?)\s*$") or title
        final_status = find_in_text(wf_text, r"^\s*-\s*Final Status:\s*(.+?)\s*$")
        if (final_status or "").strip().upper() != "PASS":
            print("BLOCK: archive-task requires Final Status = PASS in workflow.md")
            return 2

    archive_root = Path(args.archive_root).resolve() if args.archive_root else task_root.parents[1] / "archive"
    archive_root.mkdir(parents=True, exist_ok=True)
    dst = archive_root / task_root.name
    if dst.exists():
        print(f"BLOCK: archive target already exists: {dst}")
        return 2

    root = repo_root_from_path(task_root)
    archived_at = now_str()
    ensure_json(
        task_root / "archive-manifest.json",
        {
            "task_id": task_root.name,
            "title": title,
            "archived_at": archived_at,
            "source": str(task_root),
            "archived_workflow": f".agentdocs/archive/{task_root.name}/workflow.md",
            "archive_index": ".agentdocs/archive/index.md",
        },
    )
    rewrite_task_scoped_paths_for_archive(task_root)
    shutil.move(str(task_root), str(dst))
    remove_current_task_entry(root, f".agentdocs/tasks/{task_root.name}/workflow.md")
    write_archive_entry(root, task_root.name, title, f".agentdocs/archive/{task_root.name}/workflow.md", archived_at)
    print(dst)
    return 0


def parse_front_matter(text: str):
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    meta = {}
    current_key = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
            current_key = key.strip()
        elif current_key:
            meta[current_key] = (meta[current_key] + "\n" + line).strip()
    return meta, body


def cmd_lint_skills(args):
    root = Path(args.root).resolve()
    skills_root = root / ".agents" / "skills"
    errors = []
    checked = 0

    for skill_md in sorted(skills_root.glob("*/SKILL.md")):
        checked += 1
        text = skill_md.read_text(encoding="utf-8")
        meta, body = parse_front_matter(text)
        if not meta:
            errors.append(f"{skill_md}: missing or invalid front matter")
            continue
        if "name" not in meta:
            errors.append(f"{skill_md}: missing name in front matter")
        if "description" not in meta:
            errors.append(f"{skill_md}: missing description in front matter")
        extra_keys = sorted(set(meta.keys()) - SKILL_ALLOWED_FRONTMATTER_KEYS)
        if extra_keys:
            errors.append(f"{skill_md}: unexpected front matter keys: {extra_keys}")
        expected_name = skill_md.parent.name
        if meta.get("name") and meta["name"].strip() != expected_name:
            errors.append(f"{skill_md}: front matter name must match folder name '{expected_name}'")
        body_lines = body.splitlines()
        if len(body_lines) > SKILL_MAX_BODY_LINES:
            errors.append(f"{skill_md}: body exceeds {SKILL_MAX_BODY_LINES} lines")
        for heading in SKILL_FORBIDDEN_BODY_HEADINGS:
            if heading in body:
                errors.append(f"{skill_md}: body should not contain heading '{heading}'")
        refs = skill_md.parent / "references"
        if refs.exists() and not refs.is_dir():
            errors.append(f"{skill_md}: references exists but is not a directory")
        for aux_name in SKILL_FORBIDDEN_AUX_FILES:
            aux_path = skill_md.parent / aux_name
            if aux_path.exists():
                errors.append(f"{skill_md}: forbidden auxiliary file present: {aux_name}")

    print(json.dumps({"checked": checked, "errors": errors}, ensure_ascii=False, indent=2))
    return 2 if errors else 0


def build_parser():
    p = argparse.ArgumentParser(description="Deterministic controller for agentic_codex_workflow V2")
    sub = p.add_subparsers(dest="cmd", required=True)

    x = sub.add_parser("check-transition")
    x.add_argument("--from", dest="from_state", required=True)
    x.add_argument("--to", dest="to_state", required=True)
    x.set_defaults(func=cmd_check_transition)

    x = sub.add_parser("advance-state")
    x.add_argument("--workflow", required=True)
    x.add_argument("--to", dest="to_state", required=True)
    x.add_argument("--from", dest="from_state")
    x.add_argument("--allowed-next-state", default="")
    x.add_argument("--owner", default="controller")
    x.add_argument("--reason", required=True)
    x.add_argument("--exception-status", default="")
    x.add_argument("--illegal-transition-seen", choices=["YES", "NO"], default="NO")
    x.add_argument("--at")
    x.set_defaults(func=cmd_advance_state)

    x = sub.add_parser("create-task")
    x.add_argument("--root", default=".")
    x.add_argument("--task-id", required=True)
    x.add_argument("--slug", required=True)
    x.add_argument("--title", required=True)
    x.add_argument("--issue", default="N/A")
    x.add_argument("--force", action="store_true")
    x.set_defaults(func=cmd_create_task)

    x = sub.add_parser("make-pack")
    x.add_argument("--root", default=".")
    x.add_argument("--task-root", required=True)
    x.add_argument("--task-id", required=True)
    x.add_argument("--title", required=True)
    x.add_argument("--phase", required=True)
    x.add_argument("--current-state", required=True)
    x.add_argument("--allowed-next-state", required=True)
    x.add_argument("--owner", default="worker")
    x.add_argument("--goal", required=True)
    x.add_argument("--understanding", default="NO")
    x.add_argument("--review-mode", default="FULL_REVIEW")
    x.add_argument("--build-scope", default="APPROVED_SCOPE")
    x.add_argument("--coverage", default="SUFFICIENT")
    x.add_argument("--escalation-rule", default="If local changes imply global impact, stop and escalate to FULL_REVIEW.")
    for name in ["non-goal", "missing-piece", "spec-source", "review-input", "must-read", "adjacent", "unread", "code-path", "symbol", "test-anchor", "runtime-anchor", "write-boundary", "forbidden-write", "frozen-decision", "non-reopen", "risk", "previous-finding", "invariant", "must-have", "verification", "recheck", "uat"]:
        x.add_argument(f"--{name}", action="append")
    x.set_defaults(func=cmd_make_pack)

    x = sub.add_parser("validate-pack")
    x.add_argument("--pack", required=True)
    x.set_defaults(func=cmd_validate_pack)

    x = sub.add_parser("emit-delegation-brief")
    x.add_argument("--root", default=".")
    x.add_argument("--task-root", required=True)
    x.add_argument("--role", required=True)
    x.add_argument("--session-purpose", required=True)
    x.add_argument("--task-pack", required=True)
    x.add_argument("--goal", required=True)
    x.add_argument("--review-mode", default="FULL_REVIEW")
    x.add_argument("--build-scope", default="")
    x.add_argument("--output")
    for name in ["must-read", "truth-anchor", "write-boundary", "forbidden-write", "output-line", "escalation-line"]:
        x.add_argument(f"--{name}", action="append")
    x.set_defaults(func=cmd_emit_delegation_brief)

    x = sub.add_parser("record-review")
    x.add_argument("--task-root", required=True)
    x.add_argument("--kind", required=True)
    x.add_argument("--workflow")
    x.add_argument("--round", type=int, default=1)
    x.add_argument("--input")
    x.add_argument("--decision", default="NOT_STARTED")
    x.add_argument("--review-mode", default="FULL_REVIEW")
    x.add_argument("--summary", default="")
    x.add_argument("--required-changes", default="")
    x.add_argument("--evidence", default="")
    x.add_argument("--recheck-scope", default="")
    x.add_argument("--global-impact", default="UNKNOWN")
    x.add_argument("--open-questions", default="")
    x.add_argument("--archive-actions", default="")
    x.add_argument("--material-accessed", action="append")
    x.set_defaults(func=cmd_record_review)

    x = sub.add_parser("record-evidence")
    x.add_argument("--task-root", required=True)
    x.add_argument("--workflow")
    x.add_argument("--evidence-id", required=True)
    x.add_argument("--phase", required=True)
    x.add_argument("--purpose", required=True)
    x.add_argument("--command", required=True)
    x.add_argument("--cwd", default=".")
    x.add_argument("--ran-at")
    x.add_argument("--exit-code", default="0")
    x.add_argument("--result", default="PASS")
    x.add_argument("--output-path", default="")
    x.add_argument("--output-excerpt", default="")
    x.add_argument("--related-artifact", action="append")
    x.add_argument("--notes", default="")
    x.add_argument("--reviewer-recheck", default="NO")
    x.add_argument("--why", default="")
    x.add_argument("--instead", default="")
    x.add_argument("--to-run-later", default="")
    x.set_defaults(func=cmd_record_evidence)

    x = sub.add_parser("record-workflow-event")
    x.add_argument("--workflow", required=True)
    x.add_argument("--kind", required=True)
    x.add_argument("--message", required=True)
    x.add_argument("--at")
    x.set_defaults(func=cmd_record_workflow_event)

    x = sub.add_parser("sync-index")
    x.add_argument("--root", default=".")
    x.add_argument("--task-id", required=True)
    x.add_argument("--title", required=True)
    x.add_argument("--current-state", required=True)
    x.add_argument("--entry-kind", choices=["DEFAULT", "ACTIVE"], default="DEFAULT")
    x.add_argument("--force-default", action="store_true")
    x.add_argument("--force", action="store_true")
    x.set_defaults(func=cmd_sync_index)

    x = sub.add_parser("archive-task")
    x.add_argument("--task-root", required=True)
    x.add_argument("--archive-root")
    x.set_defaults(func=cmd_archive_task)

    x = sub.add_parser("lint-skills")
    x.add_argument("--root", default=".")
    x.set_defaults(func=cmd_lint_skills)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
