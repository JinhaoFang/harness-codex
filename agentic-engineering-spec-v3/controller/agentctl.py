#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

TZ = timezone(timedelta(hours=8))
PLACEHOLDER_VALUES = {"<task-id>", "<task-title>", "<updated-at>", "<subtask-id>", "<subtask-id-or-na>", "<title>", "..."}


def now_str() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M %z")


def now_compact() -> str:
    return datetime.now(TZ).strftime("%Y%m%d-%H%M%S")


def ensure_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def ensure_json(path: Path, payload: dict) -> None:
    ensure_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def repo_root_from_arg(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return Path.cwd().resolve()


def template_root_from_arg(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / "templates"


def load_template(template_root: Path, name: str) -> str:
    return (template_root / name).read_text(encoding="utf-8")


def replace_tokens(text: str, mapping: dict[str, str]) -> str:
    for key, value in mapping.items():
        text = text.replace(f"<{key}>", value)
    return text


def agentdocs_root(repo_root: Path) -> Path:
    return repo_root / ".agentdocs"


def tasks_root(repo_root: Path) -> Path:
    return agentdocs_root(repo_root) / "tasks"


def archive_root(repo_root: Path) -> Path:
    return agentdocs_root(repo_root) / "archive"


def task_dir(repo_root: Path, task_id: str, *, archived: bool = False) -> Path:
    root = archive_root(repo_root) if archived else tasks_root(repo_root)
    return root / task_id


def find_bullet_value(lines: list[str], bullet_label: str) -> str | None:
    pattern = re.compile(rf"^\s*-\s*{re.escape(bullet_label)}\s*:\s*(.*?)\s*$")
    for line in lines:
        match = pattern.match(line)
        if match:
            return match.group(1)
    return None


def replace_bullet_value(lines: list[str], bullet_label: str, value: str) -> list[str]:
    pattern = re.compile(rf"^(?P<prefix>\s*-\s*{re.escape(bullet_label)}\s*:\s*).*$")
    out: list[str] = []
    replaced = False
    for line in lines:
        if not replaced and pattern.match(line):
            out.append(pattern.sub(lambda m: f"{m.group('prefix')}{value}", line))
            replaced = True
        else:
            out.append(line)
    if not replaced:
        raise SystemExit(f"BLOCK: workflow missing bullet '- {bullet_label}:'")
    return out


def is_placeholder(value: str) -> bool:
    raw = value.strip()
    if raw in PLACEHOLDER_VALUES:
        return True
    if raw.startswith("<") and raw.endswith(">"):
        return True
    return False


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not (lines and lines[0].strip() == "---"):
        raise SystemExit("BLOCK: missing frontmatter start ('---')")
    out: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip()
    if not out:
        raise SystemExit("BLOCK: empty frontmatter")
    return out


def section_slice(lines: list[str], heading: str) -> list[str]:
    start = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            start = i + 1
            break
    if start is None:
        return []
    out: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        out.append(line)
    return out


def bullets_to_map(lines: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^\s*-\s*(?P<label>[^:]+)\s*:\s*(?P<value>.*)\s*$", line)
        if not match:
            continue
        out[match.group("label").strip()] = match.group("value").strip()
    return out


def find_subtask_block(plan_lines: list[str], subtask_id: str) -> list[str]:
    subtasks = section_slice(plan_lines, "## Subtasks")
    if not subtasks:
        return []
    header_re = re.compile(r"^###\s+(?P<id>[^\s—-]+)\s*(?:—|-)\s*(?P<title>.+?)\s*$")

    blocks: dict[str, list[str]] = {}
    current_id: str | None = None
    for line in subtasks:
        if line.startswith("### "):
            m = header_re.match(line.strip())
            current_id = (m.group("id") if m else line.strip().split(maxsplit=1)[0].removeprefix("###")).strip()
            blocks[current_id] = []
            continue
        if current_id is not None:
            blocks[current_id].append(line)
    return blocks.get(subtask_id, [])


def rewrite_agentdocs_prefix(text: str, *, src_prefix: str, dst_prefix: str) -> str:
    return text.replace(src_prefix, dst_prefix)


def remove_index_task_entries(index_text: str, task_id: str) -> str:
    lines = index_text.splitlines()
    kept: list[str] = []
    for line in lines:
        if re.match(rf"^\s*-\s*{re.escape(task_id)}\s+—\s+", line):
            continue
        kept.append(line)
    return "\n".join(kept).rstrip() + "\n"


def sync_indexes(repo_root: Path) -> None:
    index_path, archive_index_path = ensure_agentdocs(repo_root)

    tasks: list[tuple[str, str]] = []
    for wf in sorted(tasks_root(repo_root).glob("*/workflow.md")):
        text = wf.read_text(encoding="utf-8")
        title = parse_frontmatter(text).get("title", "<task-title>")
        task_id = wf.parent.name
        tasks.append((task_id, title))

    archived: list[tuple[str, str]] = []
    for wf in sorted(archive_root(repo_root).glob("*/workflow.md")):
        text = wf.read_text(encoding="utf-8")
        title = parse_frontmatter(text).get("title", "<task-title>")
        task_id = wf.parent.name
        archived.append((task_id, title))

    active_lines = minimal_index_text().splitlines()
    insert_at = active_lines.index("<!-- - <task-id> — <title> — .agentdocs/tasks/<task-id>/workflow.md -->") + 1
    active_entries = [f"- {tid} — {title} — .agentdocs/tasks/{tid}/workflow.md" for tid, title in tasks]
    active_lines[insert_at:insert_at] = active_entries
    if tasks:
        active_lines = [line for line in active_lines if line.strip() != "<!-- NONE -->"]
    ensure_text(index_path, "\n".join(active_lines) + "\n")

    archive_lines = minimal_archive_index_text().splitlines()
    insert_at = archive_lines.index("<!-- - <task-id> — <title> — .agentdocs/archive/<task-id>/workflow.md -->") + 1
    archive_entries = [f"- {tid} — {title} — .agentdocs/archive/{tid}/workflow.md" for tid, title in archived]
    archive_lines[insert_at:insert_at] = archive_entries
    if archived:
        archive_lines = [line for line in archive_lines if line.strip() != "<!-- NONE -->"]
    ensure_text(archive_index_path, "\n".join(archive_lines) + "\n")


def update_frontmatter_field(text: str, field: str, value: str) -> str:
    pattern = re.compile(rf"^(?P<prefix>{re.escape(field)}:\s*).*$", re.MULTILINE)
    if pattern.search(text):
        return pattern.sub(lambda m: f"{m.group('prefix')}{value}", text, count=1)
    raise SystemExit(f"BLOCK: missing frontmatter field '{field}:'")


def minimal_index_text() -> str:
    return (
        "# .agentdocs\n\n"
        "> 派生入口地图（非真相层）；可由 controller 重建。\n\n"
        "## Active tasks\n"
        "<!-- - <task-id> — <title> — .agentdocs/tasks/<task-id>/workflow.md -->\n"
        "<!-- NONE -->\n\n"
        "## Archived tasks\n"
        "See `.agentdocs/archive/index.md`.\n"
    )


def minimal_archive_index_text() -> str:
    return (
        "# Archived tasks\n\n"
        "> 派生索引（非真相层）；可由 controller 重建。\n\n"
        "<!-- - <task-id> — <title> — .agentdocs/archive/<task-id>/workflow.md -->\n"
        "<!-- NONE -->\n"
    )


def ensure_agentdocs(repo_root: Path) -> tuple[Path, Path]:
    root = agentdocs_root(repo_root)
    root.mkdir(parents=True, exist_ok=True)
    archive = archive_root(repo_root)
    archive.mkdir(parents=True, exist_ok=True)
    index_path = root / "index.md"
    archive_index_path = archive / "index.md"
    if not index_path.exists():
        ensure_text(index_path, minimal_index_text())
    if not archive_index_path.exists():
        ensure_text(archive_index_path, minimal_archive_index_text())
    return index_path, archive_index_path


def append_index_entry(index_path: Path, entry: str) -> None:
    text = index_path.read_text(encoding="utf-8")
    if entry in text:
        return
    if "<!-- NONE -->" in text:
        text = text.replace("<!-- NONE -->", entry + "\n<!-- NONE -->", 1)
        ensure_text(index_path, text)
        return
    ensure_text(index_path, text.rstrip() + "\n" + entry + "\n")


@dataclass(frozen=True)
class TaskPaths:
    task_dir: Path
    plan: Path
    workflow: Path
    reviews_dir: Path
    evidence_dir: Path
    packs_dir: Path


def resolve_task_paths(repo_root: Path, task_id: str, *, archived: bool = False) -> TaskPaths:
    root = task_dir(repo_root, task_id, archived=archived)
    return TaskPaths(
        task_dir=root,
        plan=root / "plan.md",
        workflow=root / "workflow.md",
        reviews_dir=root / "reviews",
        evidence_dir=root / "evidence",
        packs_dir=root / "subtask-packs",
    )


def cmd_init_agentdocs(args: argparse.Namespace) -> None:
    repo_root = repo_root_from_arg(args.repo_root)
    index_path, archive_index_path = ensure_agentdocs(repo_root)
    print("OK: ensured .agentdocs")
    print(f"- index: {index_path}")
    print(f"- archive index: {archive_index_path}")


def render_plan(template_root: Path, task_id: str, title: str) -> str:
    text = load_template(template_root, "plan.md")
    return replace_tokens(
        text,
        {
            "task-id": task_id,
            "task-title": title,
            "updated-at": now_str(),
        },
    )


def render_workflow(template_root: Path, task_id: str, title: str, subtask_id: str, *, repo_root: Path) -> str:
    text = load_template(template_root, "workflow.md")
    text = replace_tokens(
        text,
        {
            "task-id": task_id,
            "task-title": title,
            "updated-at": now_str(),
        },
    )
    lines = text.splitlines()
    # Current
    lines = replace_bullet_value(lines, "Active subtask", subtask_id)
    lines = replace_bullet_value(lines, "Current gate", "Understand")
    lines = replace_bullet_value(lines, "Allowed next action", "Ground in World")
    lines = replace_bullet_value(lines, "Exception status", "NONE")
    # Pointers
    rel_plan = f".agentdocs/tasks/{task_id}/plan.md"
    rel_pack = f".agentdocs/tasks/{task_id}/subtask-packs/{subtask_id}.md"
    lines = replace_bullet_value(lines, "Plan doc", rel_plan)
    lines = replace_bullet_value(lines, "Active subtask pack", rel_pack)
    lines = replace_bullet_value(lines, "Latest evidence ref", "")
    # Reviews
    lines = replace_bullet_value(lines, "Latest plan review ref", "")
    lines = replace_bullet_value(lines, "Latest close review ref", "")
    return "\n".join(lines) + "\n"


def cmd_create_task(args: argparse.Namespace) -> None:
    repo_root = repo_root_from_arg(args.repo_root)
    template_root = template_root_from_arg(args.template_root)
    ensure_agentdocs(repo_root)

    task_id: str = args.task_id.strip()
    title: str = args.title.strip()
    subtask_id: str = (args.subtask or "S1").strip()

    paths = resolve_task_paths(repo_root, task_id, archived=False)
    if paths.task_dir.exists() and any(paths.task_dir.iterdir()) and not args.force:
        raise SystemExit(f"BLOCK: task dir exists and is non-empty: {paths.task_dir} (use --force to overwrite files)")

    paths.reviews_dir.mkdir(parents=True, exist_ok=True)
    paths.evidence_dir.mkdir(parents=True, exist_ok=True)
    paths.packs_dir.mkdir(parents=True, exist_ok=True)

    ensure_text(paths.plan, render_plan(template_root, task_id, title))
    ensure_text(paths.workflow, render_workflow(template_root, task_id, title, subtask_id, repo_root=repo_root))

    index_path = agentdocs_root(repo_root) / "index.md"
    append_index_entry(index_path, f"- {task_id} — {title} — .agentdocs/tasks/{task_id}/workflow.md")

    # Create an initial derived pack (can be regenerated anytime).
    pack_path = paths.packs_dir / f"{subtask_id}.md"
    if not pack_path.exists() or args.force:
        cmd_refresh_pack(
            argparse.Namespace(
                repo_root=str(repo_root),
                template_root=str(template_root),
                task_id=task_id,
                subtask=subtask_id,
                plan_ref=None,
                workflow_ref=None,
                evidence_refs=[],
                out=str(pack_path),
            )
        )

    print("OK: created task")
    print(f"- task: {paths.task_dir}")
    print(f"- plan: {paths.plan}")
    print(f"- workflow: {paths.workflow}")
    print(f"- subtask pack: {pack_path}")


def load_workflow_lines(workflow_path: Path) -> list[str]:
    if not workflow_path.exists():
        raise SystemExit(f"BLOCK: missing workflow: {workflow_path}")
    return workflow_path.read_text(encoding="utf-8").splitlines()


def save_workflow_lines(workflow_path: Path, lines: list[str]) -> None:
    ensure_text(workflow_path, "\n".join(lines) + "\n")


def cmd_write_review(args: argparse.Namespace) -> None:
    repo_root = repo_root_from_arg(args.repo_root)
    template_root = template_root_from_arg(args.template_root)
    task_id: str = args.task_id.strip()
    subtask_id: str = (args.subtask or "<subtask-id-or-na>").strip()
    review_type: str = args.review_type
    decision: str = args.decision

    paths = resolve_task_paths(repo_root, task_id, archived=False)
    if not paths.task_dir.exists():
        raise SystemExit(f"BLOCK: missing task dir: {paths.task_dir}")

    ts = now_compact()
    out_path = paths.reviews_dir / f"{ts}-{review_type}.json"

    if review_type == "plan":
        template_name = "review-plan.json"
        checked = {
            "plan": str(args.plan_ref or f".agentdocs/tasks/{task_id}/plan.md"),
            "world_anchors": args.world_anchors or [],
        }
        reviewer = "plan_reviewer"
    else:
        template_name = "review-close.json"
        checked = {
            "approved_plan": str(args.plan_ref or f".agentdocs/tasks/{task_id}/plan.md"),
            "code_paths": args.code_paths or [],
            "tests": args.tests or [],
            "evidence": args.evidence_refs or [],
        }
        reviewer = "close_reviewer"

    template = load_template(template_root, template_name)
    payload = json.loads(template)
    payload["task_id"] = task_id
    payload["subtask"] = subtask_id or "<subtask-id-or-na>"
    payload["decision"] = decision
    payload["reviewer"] = reviewer
    payload["updated_at"] = now_str()
    payload["checked_against"] = checked

    findings = []
    for raw in args.findings or []:
        # type:severity:summary
        parts = raw.split(":", 2)
        if len(parts) != 3:
            raise SystemExit("BLOCK: --finding must be 'type:severity:summary'")
        findings.append({"type": parts[0], "severity": parts[1], "summary": parts[2]})
    payload["findings"] = findings
    payload["required_changes"] = args.required_changes or []

    ensure_json(out_path, payload)

    workflow_lines = load_workflow_lines(paths.workflow)
    if review_type == "plan":
        workflow_lines = replace_bullet_value(workflow_lines, "Plan review", decision)
        workflow_lines = replace_bullet_value(workflow_lines, "Latest plan review ref", str(rel_path(repo_root, out_path)))
    else:
        workflow_lines = replace_bullet_value(workflow_lines, "Close review", decision)
        workflow_lines = replace_bullet_value(workflow_lines, "Latest close review ref", str(rel_path(repo_root, out_path)))
    workflow_lines = apply_workflow_updated_at(workflow_lines)
    save_workflow_lines(paths.workflow, workflow_lines)

    print("OK: wrote review")
    print(f"- review: {out_path}")
    print(f"- workflow updated: {paths.workflow}")


def rel_path(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def apply_workflow_updated_at(lines: list[str]) -> list[str]:
    text = "\n".join(lines)
    text = update_frontmatter_field(text, "updated_at", now_str())
    return text.splitlines()


def cmd_write_evidence(args: argparse.Namespace) -> None:
    repo_root = repo_root_from_arg(args.repo_root)
    template_root = template_root_from_arg(args.template_root)
    task_id: str = args.task_id.strip()
    subtask_id: str = (args.subtask or "<subtask-id-or-na>").strip()

    paths = resolve_task_paths(repo_root, task_id, archived=False)
    if not paths.task_dir.exists():
        raise SystemExit(f"BLOCK: missing task dir: {paths.task_dir}")

    ts = now_compact()
    out_path = paths.evidence_dir / f"{ts}-{args.kind}.json"

    template = load_template(template_root, "evidence.json")
    payload = json.loads(template)
    payload["task_id"] = task_id
    payload["subtask"] = subtask_id or "<subtask-id-or-na>"
    payload["kind"] = args.kind
    payload["purpose"] = args.purpose or ""
    payload["command"] = args.command or ""
    payload["cwd"] = args.cwd or str(repo_root)
    payload["result"] = args.result
    payload["artifact_paths"] = args.artifact_paths or []
    payload["notes"] = args.notes or ""
    payload["ran_at"] = now_str()

    ensure_json(out_path, payload)

    workflow_lines = load_workflow_lines(paths.workflow)
    workflow_lines = replace_bullet_value(workflow_lines, "Latest evidence ref", str(rel_path(repo_root, out_path)))
    workflow_lines = apply_workflow_updated_at(workflow_lines)
    save_workflow_lines(paths.workflow, workflow_lines)

    print("OK: wrote evidence")
    print(f"- evidence: {out_path}")
    print(f"- workflow updated: {paths.workflow}")


def cmd_refresh_pack(args: argparse.Namespace) -> None:
    repo_root = repo_root_from_arg(args.repo_root)
    template_root = template_root_from_arg(args.template_root)
    task_id: str = args.task_id.strip()
    subtask_id: str = (args.subtask or "S1").strip()

    paths = resolve_task_paths(repo_root, task_id, archived=False)
    plan_ref = args.plan_ref or f".agentdocs/tasks/{task_id}/plan.md"
    workflow_ref = args.workflow_ref or f".agentdocs/tasks/{task_id}/workflow.md"
    out = Path(args.out) if args.out else (paths.packs_dir / f"{subtask_id}.md")

    plan_path = repo_root / plan_ref
    workflow_path = repo_root / workflow_ref
    plan_lines = plan_path.read_text(encoding="utf-8").splitlines() if plan_path.exists() else []

    plan_goal = bullets_to_map(section_slice(plan_lines, "## Goal"))
    plan_acceptance = bullets_to_map(section_slice(plan_lines, "## Acceptance"))
    plan_boundaries = bullets_to_map(section_slice(plan_lines, "## Boundaries"))
    plan_verification = bullets_to_map(section_slice(plan_lines, "## Verification"))
    plan_anchors = bullets_to_map(section_slice(plan_lines, "## World-grounded anchors"))
    plan_decision = bullets_to_map(section_slice(plan_lines, "## Decision freeze"))

    subtask_block = find_subtask_block(plan_lines, subtask_id)
    subtask_fields = bullets_to_map(subtask_block)

    template = load_template(template_root, "subtask-pack.md")
    lines = template.splitlines()

    def set_field(label: str, value: str) -> None:
        nonlocal lines
        lines = replace_bullet_value(lines, label, value)

    set_field("Task ID", task_id)
    set_field("Subtask ID", subtask_id)
    set_field("Generated at", now_str())

    # Objective
    goal_value = subtask_fields.get("Goal") or plan_goal.get("Goal") or ""
    acceptance_value = plan_acceptance.get("Success criteria") or ""
    if subtask_fields.get("Verify"):
        acceptance_value = f"{acceptance_value} (Verify: {subtask_fields.get('Verify')})".strip()
    set_field("Goal", goal_value)
    set_field("Acceptance for this subtask", acceptance_value)

    # Boundaries
    set_field("Write boundary", subtask_fields.get("Write boundary") or plan_boundaries.get("Write boundary") or "")
    set_field("Forbidden zones", plan_boundaries.get("Forbidden zones") or "")
    set_field("Invariants", plan_boundaries.get("Invariants") or "")

    # References
    set_field("Plan section", f"{plan_ref} (Subtasks/{subtask_id})")
    set_field("Workflow state", workflow_ref)
    set_field("Relevant code paths", plan_anchors.get("Code paths") or "")
    set_field("Existing tests", plan_anchors.get("Existing tests") or "")
    set_field("Reusable mechanisms", plan_anchors.get("Reusable existing mechanisms") or "")

    # Checks
    required_verification = subtask_fields.get("Verify") or plan_verification.get("Required checks") or ""
    reviewer_focus = subtask_fields.get("Review focus") or plan_verification.get("Reviewer recheck focus") or ""
    escalation = plan_decision.get("Open questions requiring escalation") or ""
    if args.evidence_refs:
        required_verification = (required_verification + ("; " if required_verification else "") + "Evidence refs: " + ", ".join(args.evidence_refs)).strip()
    set_field("Required verification", required_verification)
    set_field("Reviewer focus", reviewer_focus)
    set_field("Escalation triggers", escalation)

    if args.evidence_refs:
        # pack template does not have evidence field; keep in Checks section via "Required verification" for now.
        set_field("Required verification", "Evidence refs: " + ", ".join(args.evidence_refs))

    ensure_text(out, "\n".join(lines) + "\n")

    workflow_lines = load_workflow_lines(paths.workflow)
    workflow_lines = replace_bullet_value(workflow_lines, "Active subtask pack", str(rel_path(repo_root, out)))
    workflow_lines = apply_workflow_updated_at(workflow_lines)
    save_workflow_lines(paths.workflow, workflow_lines)

    print("OK: refreshed pack")
    print(f"- pack: {out}")
    print(f"- workflow updated: {paths.workflow}")


def cmd_validate_refs(args: argparse.Namespace) -> None:
    repo_root = repo_root_from_arg(args.repo_root)
    task_id: str = args.task_id.strip()
    paths = resolve_task_paths(repo_root, task_id, archived=args.archived)

    broken: list[str] = []

    for required in [paths.plan, paths.workflow]:
        if not required.exists():
            broken.append(f"missing {rel_path(repo_root, required)}")

    if paths.plan.exists():
        try:
            fm = parse_frontmatter(paths.plan.read_text(encoding="utf-8"))
            if fm.get("task_id") != task_id:
                broken.append(f"plan frontmatter task_id mismatch: {fm.get('task_id')} (expected {task_id})")
            if not fm.get("title") or is_placeholder(fm.get("title", "")):
                broken.append("plan frontmatter title is placeholder/empty")
        except SystemExit as e:
            broken.append(f"plan frontmatter invalid: {e}")

    if paths.workflow.exists():
        wf_text = paths.workflow.read_text(encoding="utf-8")
        try:
            wf_fm = parse_frontmatter(wf_text)
            if wf_fm.get("task_id") != task_id:
                broken.append(f"workflow frontmatter task_id mismatch: {wf_fm.get('task_id')} (expected {task_id})")
        except SystemExit as e:
            broken.append(f"workflow frontmatter invalid: {e}")

        lines = wf_text.splitlines()
        required_bullets = [
            "Active subtask",
            "Current gate",
            "Allowed next action",
            "Exception status",
            "Plan review",
            "Close review",
            "Plan doc",
            "Active subtask pack",
        ]
        for label in required_bullets:
            value = find_bullet_value(lines, label)
            if value is None:
                broken.append(f"workflow missing bullet: {label}")

        for label in ["Plan doc", "Active subtask pack", "Latest evidence ref", "Latest plan review ref", "Latest close review ref"]:
            value = (find_bullet_value(lines, label) or "").strip()
            if not value:
                continue
            if re.search(r"(^|/)task-packs(/|$)", value):
                broken.append(f"forbidden legacy v2 task-packs ref in workflow: {label} -> {value}")
                continue
            if label in {"Latest evidence ref", "Latest plan review ref", "Latest close review ref"} and not value.endswith(".json"):
                broken.append(f"workflow ref should be .json: {label} -> {value}")
                continue
            ref_path = (repo_root / value).resolve() if not Path(value).is_absolute() else Path(value)
            if not ref_path.exists():
                broken.append(f"broken ref in workflow: {label} -> {value}")
            else:
                # Minimal schema checks for referenced json
                if label == "Latest evidence ref":
                    try:
                        payload = json.loads(ref_path.read_text(encoding="utf-8"))
                        for k in ["task_id", "subtask", "kind", "result", "artifact_paths", "ran_at"]:
                            if k not in payload:
                                broken.append(f"evidence missing key {k}: {value}")
                        if payload.get("task_id") != task_id:
                            broken.append(f"evidence task_id mismatch: {value}")
                    except Exception as e:
                        broken.append(f"invalid evidence json: {value} ({e})")
                if label in {"Latest plan review ref", "Latest close review ref"}:
                    try:
                        payload = json.loads(ref_path.read_text(encoding="utf-8"))
                        for k in ["task_id", "subtask", "review_type", "decision", "fresh_context", "checked_against", "updated_at"]:
                            if k not in payload:
                                broken.append(f"review missing key {k}: {value}")
                        if payload.get("task_id") != task_id:
                            broken.append(f"review task_id mismatch: {value}")
                    except Exception as e:
                        broken.append(f"invalid review json: {value} ({e})")

        # Validate pack matches workflow active subtask.
        pack_ref = (find_bullet_value(lines, "Active subtask pack") or "").strip()
        active_subtask = (find_bullet_value(lines, "Active subtask") or "").strip()
        if pack_ref and active_subtask and (repo_root / pack_ref).exists():
            pack_lines = (repo_root / pack_ref).read_text(encoding="utf-8").splitlines()
            pack_task = (find_bullet_value(pack_lines, "Task ID") or "").strip()
            pack_subtask = (find_bullet_value(pack_lines, "Subtask ID") or "").strip()
            if pack_task and pack_task != task_id:
                broken.append(f"pack task id mismatch: {pack_ref}")
            if pack_subtask and pack_subtask != active_subtask:
                broken.append(f"pack subtask id mismatch: {pack_ref} (expected {active_subtask})")

    if broken:
        print("FAIL: broken refs")
        for item in broken:
            print(f"- {item}")
        raise SystemExit(2)

    print("PASS: refs OK")


def cmd_check_gate(args: argparse.Namespace) -> None:
    repo_root = repo_root_from_arg(args.repo_root)
    task_id: str = args.task_id.strip()
    action: str = args.action
    workflow_ref = args.workflow_ref

    paths = resolve_task_paths(repo_root, task_id, archived=False)
    workflow_path = (repo_root / workflow_ref) if workflow_ref else paths.workflow
    lines = load_workflow_lines(workflow_path)

    current_gate = (find_bullet_value(lines, "Current gate") or "").strip()
    plan_review = (find_bullet_value(lines, "Plan review") or "").strip()
    close_review = (find_bullet_value(lines, "Close review") or "").strip()
    latest_evidence = (find_bullet_value(lines, "Latest evidence ref") or "").strip()

    required_refs: list[str] = [rel_path(repo_root, paths.plan), rel_path(repo_root, workflow_path)]
    ok = True
    reasons: list[str] = []

    if action == "plan-review":
        if not paths.plan.exists():
            ok = False
            reasons.append("missing plan.md")
        required_refs.append(rel_path(repo_root, paths.plan))
    elif action == "implement":
        required_refs.append((find_bullet_value(lines, "Active subtask pack") or "").strip())
        if plan_review != "PASS":
            ok = False
            reasons.append("requires Plan review = PASS")
    elif action == "close-review":
        if plan_review != "PASS":
            ok = False
            reasons.append("requires Plan review = PASS before close review")
        if not latest_evidence and not list(paths.evidence_dir.glob("*.json")):
            ok = False
            reasons.append("requires at least one evidence json (latest evidence ref or evidence/*.json)")
    elif action == "archive":
        if close_review != "PASS":
            ok = False
            reasons.append("requires Close review = PASS")

    # validate-refs is a general preflight for all actions
    try:
        cmd_validate_refs(argparse.Namespace(repo_root=str(repo_root), task_id=task_id, archived=False))
    except SystemExit as e:
        ok = False
        reasons.append(f"validate-refs failed (exit {e.code if hasattr(e, 'code') else 'nonzero'})")

    result = {
        "task_id": task_id,
        "current_gate": current_gate or None,
        "action": action,
        "pass": ok,
        "reasons": reasons,
        "required_refs": [r for r in required_refs if r],
    }
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not ok:
            raise SystemExit(2)
        return

    print("gate:", current_gate or "<unknown>")
    print("action:", action)
    if ok:
        print("PASS")
        return
    print("FAIL")
    for r in reasons:
        print("-", r)
    raise SystemExit(2)


def cmd_archive(args: argparse.Namespace) -> None:
    repo_root = repo_root_from_arg(args.repo_root)
    task_id: str = args.task_id.strip()

    src = task_dir(repo_root, task_id, archived=False)
    dst = task_dir(repo_root, task_id, archived=True)
    if not src.exists():
        raise SystemExit(f"BLOCK: missing active task dir: {src}")
    if dst.exists() and any(dst.iterdir()) and not args.force:
        raise SystemExit(f"BLOCK: archive dir exists and non-empty: {dst} (use --force)")

    # Gate: require close review PASS.
    paths = resolve_task_paths(repo_root, task_id, archived=False)
    lines = load_workflow_lines(paths.workflow)
    close_review = (find_bullet_value(lines, "Close review") or "").strip()
    if close_review != "PASS":
        raise SystemExit("BLOCK: archive requires Close review = PASS in workflow.md")
    recovery_needed = (find_bullet_value(lines, "Recovery needed") or "NO").strip()
    if recovery_needed not in {"NO", "No", "false", "FALSE"}:
        raise SystemExit("BLOCK: archive requires Recovery needed = NO in workflow.md")

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and args.force:
        shutil.rmtree(dst)
    shutil.move(str(src), str(dst))

    # Update workflow status in-place under archive.
    archived_paths = resolve_task_paths(repo_root, task_id, archived=True)
    wf_text = archived_paths.workflow.read_text(encoding="utf-8")
    wf_text = rewrite_agentdocs_prefix(wf_text, src_prefix=f".agentdocs/tasks/{task_id}/", dst_prefix=f".agentdocs/archive/{task_id}/")
    wf_text = update_frontmatter_field(wf_text, "status", "archived")
    wf_text = update_frontmatter_field(wf_text, "updated_at", now_str())
    ensure_text(archived_paths.workflow, wf_text)

    # Update derived indexes (remove from active, add to archive).
    index_path, archive_index_path = ensure_agentdocs(repo_root)
    ensure_text(index_path, remove_index_task_entries(index_path.read_text(encoding="utf-8"), task_id))
    archive_index_path = archive_root(repo_root) / "index.md"
    append_index_entry(archive_index_path, f"- {task_id} — {find_title_from_workflow(wf_text)} — .agentdocs/archive/{task_id}/workflow.md")
    sync_indexes(repo_root)

    print("OK: archived task")
    print(f"- archived: {dst}")


def find_title_from_workflow(text: str) -> str:
    match = re.search(r"^title:\s*(.+?)\s*$", text, flags=re.MULTILINE)
    return match.group(1).strip() if match else "<task-title>"


def cmd_reopen(args: argparse.Namespace) -> None:
    repo_root = repo_root_from_arg(args.repo_root)
    task_id: str = args.task_id.strip()

    src = task_dir(repo_root, task_id, archived=True)
    dst = task_dir(repo_root, task_id, archived=False)
    if not src.exists():
        raise SystemExit(f"BLOCK: missing archived task dir: {src}")
    if dst.exists() and any(dst.iterdir()) and not args.force:
        raise SystemExit(f"BLOCK: active task dir exists and non-empty: {dst} (use --force)")

    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and args.force:
        shutil.rmtree(dst)
    shutil.move(str(src), str(dst))

    paths = resolve_task_paths(repo_root, task_id, archived=False)
    wf_text = paths.workflow.read_text(encoding="utf-8")
    wf_text = rewrite_agentdocs_prefix(wf_text, src_prefix=f".agentdocs/archive/{task_id}/", dst_prefix=f".agentdocs/tasks/{task_id}/")
    wf_text = update_frontmatter_field(wf_text, "status", "active")
    wf_text = update_frontmatter_field(wf_text, "updated_at", now_str())
    # record reopen trigger into recovery section (best-effort)
    wf_lines = wf_text.splitlines()
    if args.trigger:
        wf_lines = replace_bullet_value(wf_lines, "Recovery needed", "YES")
        wf_lines = replace_bullet_value(wf_lines, "Trigger", args.trigger)
        wf_lines = replace_bullet_value(wf_lines, "Exit condition", args.reason or "Re-evaluate next gate and clear recovery")
        wf_text = "\n".join(wf_lines) + "\n"
    ensure_text(paths.workflow, wf_text)

    # Update derived indexes.
    index_path, archive_index_path = ensure_agentdocs(repo_root)
    ensure_text(archive_index_path, remove_index_task_entries(archive_index_path.read_text(encoding="utf-8"), task_id))
    append_index_entry(index_path, f"- {task_id} — {find_title_from_workflow(wf_text)} — .agentdocs/tasks/{task_id}/workflow.md")
    sync_indexes(repo_root)

    print("OK: reopened task")
    print(f"- active: {dst}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Agentic Engineering Spec v3 controller (reference implementation)")
    p.add_argument("--repo-root", default=None, help="Target repo root (default: cwd)")
    p.add_argument("--template-root", default=None, help="Template root (default: <this-repo>/templates)")
    sub = p.add_subparsers(dest="cmd", required=True)

    x = sub.add_parser("init-agentdocs", help="Initialize .agentdocs/ skeleton (derived indexes)")
    x.set_defaults(fn=cmd_init_agentdocs)

    x = sub.add_parser("create-task", help="Create a new task skeleton under .agentdocs/tasks/<task-id>/")
    x.add_argument("--task-id", required=True)
    x.add_argument("--title", required=True)
    x.add_argument("--subtask", default="S1", help="Default subtask id (default: S1)")
    x.add_argument("--force", action="store_true", help="Overwrite existing files in task dir")
    x.set_defaults(fn=cmd_create_task)

    x = sub.add_parser("write-review", help="Write a structured review JSON and update workflow pointers")
    x.add_argument("--task-id", required=True)
    x.add_argument("--subtask", default=None)
    x.add_argument("--review-type", choices=["plan", "close"], required=True)
    x.add_argument("--decision", choices=["PASS", "CHANGES_REQUIRED", "REJECT"], required=True)
    x.add_argument("--plan-ref", default=None)
    x.add_argument("--world-anchor", dest="world_anchors", action="append", default=[])
    x.add_argument("--code-path", dest="code_paths", action="append", default=[])
    x.add_argument("--test", dest="tests", action="append", default=[])
    x.add_argument("--evidence-ref", dest="evidence_refs", action="append", default=[])
    x.add_argument("--finding", dest="findings", action="append", default=[], help="type:severity:summary")
    x.add_argument("--required-change", dest="required_changes", action="append", default=[])
    x.set_defaults(fn=cmd_write_review)

    x = sub.add_parser("write-evidence", help="Write a structured evidence JSON and update workflow pointers")
    x.add_argument("--task-id", required=True)
    x.add_argument("--subtask", default=None)
    x.add_argument("--kind", choices=["command", "test", "build", "behavior", "screenshot", "other"], required=True)
    x.add_argument("--result", choices=["PASS", "FAIL", "INFO"], required=True)
    x.add_argument("--purpose", default=None)
    x.add_argument("--command", default=None)
    x.add_argument("--cwd", default=None)
    x.add_argument("--artifact-path", dest="artifact_paths", action="append", default=[])
    x.add_argument("--notes", default=None)
    x.set_defaults(fn=cmd_write_evidence)

    x = sub.add_parser("refresh-pack", help="Regenerate a derived subtask-pack and update workflow pointer")
    x.add_argument("--task-id", required=True)
    x.add_argument("--subtask", default="S1")
    x.add_argument("--plan-ref", default=None)
    x.add_argument("--workflow-ref", default=None)
    x.add_argument("--evidence-ref", dest="evidence_refs", action="append", default=[])
    x.add_argument("--out", default=None)
    x.set_defaults(fn=cmd_refresh_pack)

    x = sub.add_parser("validate-refs", help="Validate plan/workflow pointers and referenced artifacts exist")
    x.add_argument("--task-id", required=True)
    x.add_argument("--archived", action="store_true")
    x.set_defaults(fn=cmd_validate_refs)

    x = sub.add_parser("check-gate", help="Deterministically check whether a requested action is allowed")
    x.add_argument("--task-id", required=True)
    x.add_argument("--action", choices=["plan-review", "implement", "close-review", "archive"], required=True)
    x.add_argument("--workflow-ref", default=None, help="Optional workflow ref to check instead of default")
    x.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    x.set_defaults(fn=cmd_check_gate)

    x = sub.add_parser("archive", help="Archive a task under .agentdocs/archive/<task-id>/ (requires close review PASS)")
    x.add_argument("--task-id", required=True)
    x.add_argument("--force", action="store_true")
    x.set_defaults(fn=cmd_archive)

    x = sub.add_parser("reopen", help="Reopen an archived task back under .agentdocs/tasks/<task-id>/")
    x.add_argument("--task-id", required=True)
    x.add_argument("--trigger", default=None)
    x.add_argument("--reason", default=None)
    x.add_argument("--force", action="store_true")
    x.set_defaults(fn=cmd_reopen)

    x = sub.add_parser("sync-index", help="Regenerate derived .agentdocs index files from disk state")
    x.set_defaults(fn=lambda a: (sync_indexes(repo_root_from_arg(a.repo_root)), print("OK: synced indexes")))

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
