#!/usr/bin/env python3
"""Bootstrap or resume the task-scoped .agentdocs workspace.

Modes:
  - init: create a new task-scoped workspace through taskctl
  - resume: register an existing task-scoped workflow by path / slug / issue
  - adopt-current: return the current DEFAULT workflow from index
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
from pathlib import Path
from typing import List, Tuple

SECTION_MARKER = "## 2) 当前任务（SSOT）"
NONE_MARKER = "<!-- NONE -->"
ENTRY_RE = re.compile(r"^- (?P<kind>DEFAULT|ACTIVE): (?P<path>\S+) — (?P<title>.+)$")
LEGACY_ACTIVE_RE = re.compile(r"## Active Tasks\n(?P<body>[\s\S]*?)(?:\n## |\Z)")
TITLE_RE = re.compile(r"^title:\s*(?P<title>.+)$", re.MULTILINE)
SLUG_RE = re.compile(r"^slug:\s*(?P<slug>.+)$", re.MULTILINE)


def kebab(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = s.replace("_", " ")
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-") or "task"


def asset(rel: str) -> str:
    here = Path(__file__).resolve().parent
    return (here.parent / "assets" / rel).read_text(encoding="utf-8")


def ensure_file(path: Path, content: str) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def ensure_base(root: Path) -> None:
    agentdocs = root / ".agentdocs"
    (agentdocs / "tasks").mkdir(parents=True, exist_ok=True)
    (agentdocs / "archive").mkdir(parents=True, exist_ok=True)
    (agentdocs / "architecture").mkdir(parents=True, exist_ok=True)
    ensure_file(agentdocs / "index.md", asset("index-template.md"))
    ensure_file(agentdocs / "architecture" / "index.md", asset("architecture/index-template.md"))
    ensure_file(agentdocs / "insights.md", asset("insights-template.md"))


def split_index_sections(text: str) -> Tuple[List[str], List[str], List[str]]:
    lines = text.splitlines()
    before, section, after = [], [], []
    state = "before"
    for line in lines:
        if state == "before":
            before.append(line)
            if line.strip() == SECTION_MARKER:
                state = "section"
        elif state == "section":
            if line.startswith("## ") and line.strip() != SECTION_MARKER:
                after.append(line)
                state = "after"
            else:
                section.append(line)
        else:
            after.append(line)
    return before, section, after


def parse_entries(index_text: str) -> List[dict]:
    _, section, _ = split_index_sections(index_text)
    entries = []
    for line in section:
        m = ENTRY_RE.match(line.strip())
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

    legacy = LEGACY_ACTIVE_RE.search(index_text)
    if not legacy:
        return []

    body = legacy.group("body")
    workflow = re.search(r"^\s*-\s*Workflow:\s*(?P<v>.+)$", body, re.MULTILINE)
    title = re.search(r"^\s*-\s*Title:\s*(?P<v>.+)$", body, re.MULTILINE)
    if workflow:
        return [
            {
                "kind": "DEFAULT",
                "path": workflow.group("v").strip(),
                "title": title.group("v").strip() if title else "Untitled Task",
            }
        ]
    return []


def render_entries(entries: List[dict]) -> List[str]:
    lines = [
        SECTION_MARKER,
        "<!-- DEFAULT = 新会话默认先读的 workflow；同一时间应尽量只有一个 DEFAULT -->",
        "<!-- ACTIVE = 并行任务，仅在明确允许并行时保留 -->",
    ]
    if not entries:
        lines.append(NONE_MARKER)
        return lines
    default_entries = [e for e in entries if e["kind"] == "DEFAULT"]
    active_entries = [e for e in entries if e["kind"] == "ACTIVE"]
    for e in default_entries + active_entries:
        lines.append(f"- {e['kind']}: {e['path']} — {e['title']}")
    return lines


def write_entries(index_path: Path, entries: List[dict]) -> None:
    text = index_path.read_text(encoding="utf-8")
    before, _, after = split_index_sections(text)
    body = render_entries(entries)
    out_lines = before[:-1] + body if before else body
    if after:
        if out_lines and out_lines[-1] != "":
            out_lines.append("")
        out_lines.extend(after)
    index_path.write_text("\n".join(out_lines).rstrip() + "\n", encoding="utf-8")


def create_workflow(root: Path, title: str, issue: str) -> Tuple[Path, str, str]:
    now = dt.datetime.now().astimezone()
    task_id = now.strftime("%y%m%d%H%M")
    slug = kebab(title)
    cmd = [
        "python",
        str(root / ".codex" / "workflow" / "taskctl.py"),
        "create-task",
        "--root",
        str(root),
        "--task-id",
        task_id,
        "--slug",
        slug,
        "--title",
        title,
        "--issue",
        issue or "N/A",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit((proc.stderr or proc.stdout).strip() or "taskctl create-task failed")
    workflow = root / ".agentdocs" / "tasks" / task_id / "workflow.md"
    if not workflow.exists():
        raise SystemExit(f"taskctl create-task did not create workflow: {workflow}")
    return workflow, task_id, slug


def promote_or_register(index_path: Path, workflow_rel: str, title: str, allow_parallel: bool, make_default: bool) -> None:
    text = index_path.read_text(encoding="utf-8")
    entries = parse_entries(text)
    entries = [e for e in entries if e["path"] != workflow_rel]
    has_default = any(e["kind"] == "DEFAULT" for e in entries)
    if make_default or not has_default:
        for e in entries:
            if e["kind"] == "DEFAULT":
                e["kind"] = "ACTIVE"
        entries.insert(0, {"kind": "DEFAULT", "path": workflow_rel, "title": title})
    else:
        if not allow_parallel:
            current = next((e for e in entries if e["kind"] == "DEFAULT"), None)
            current_desc = current["path"] if current else "<unknown>"
            raise SystemExit(
                f"Refusing to register another workflow because a DEFAULT workflow already exists: {current_desc}. Use --allow-parallel, --mode resume, or --mode adopt-current."
            )
        entries.append({"kind": "ACTIVE", "path": workflow_rel, "title": title})
    write_entries(index_path, entries)


def find_candidates(root: Path, workflow: str, slug: str, issue: str) -> List[Path]:
    tasks_dir = root / ".agentdocs" / "tasks"
    candidates: List[Path] = []
    if workflow:
        p = Path(workflow)
        if not p.is_absolute():
            p = (root / p).resolve()
        if p.exists():
            return [p]
        rel = root / workflow
        if rel.exists():
            return [rel.resolve()]
        return []

    for path in tasks_dir.glob("*/workflow.md"):
        text = path.read_text(encoding="utf-8")
        if slug:
            m = SLUG_RE.search(text)
            if m and m.group("slug").strip() == slug:
                candidates.append(path)
                continue
        if issue and issue != "N/A" and issue in text:
            candidates.append(path)

    uniq = []
    seen = set()
    for p in candidates:
        rp = str(p.resolve())
        if rp not in seen:
            seen.add(rp)
            uniq.append(p)
    return uniq


def read_title_from_workflow(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = TITLE_RE.search(text)
    if m:
        return m.group("title").strip()
    for line in text.splitlines():
        if line.startswith("# Workflow："):
            return line.split("：", 1)[1].strip()
    return path.parent.name


def adopt_current(root: Path) -> Path:
    index_path = root / ".agentdocs" / "index.md"
    entries = parse_entries(index_path.read_text(encoding="utf-8"))
    defaults = [e for e in entries if e["kind"] == "DEFAULT"]
    if len(defaults) == 1:
        return (root / defaults[0]["path"]).resolve()
    if len(defaults) > 1:
        raise SystemExit("Found multiple DEFAULT workflows. Fix .agentdocs/index.md before adopting current.")
    actives = [e for e in entries if e["kind"] == "ACTIVE"]
    if len(actives) == 1:
        p = (root / actives[0]["path"]).resolve()
        promote_or_register(index_path, actives[0]["path"], actives[0]["title"], allow_parallel=True, make_default=True)
        return p
    raise SystemExit("No unique current workflow found. Use --mode init or --mode resume.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--mode", choices=["init", "resume", "adopt-current"])
    ap.add_argument("--title", help="Task title; required for init mode")
    ap.add_argument("--issue", default="", help="GitHub issue URL or identifier")
    ap.add_argument("--workflow", default="", help="Workflow path to resume")
    ap.add_argument("--slug", default="", help="Workflow slug to resume")
    ap.add_argument("--allow-parallel", action="store_true", help="Allow another ACTIVE workflow while keeping the current DEFAULT")
    ap.add_argument("--make-default", action="store_true", help="Promote a resumed workflow to DEFAULT")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    ensure_base(root)

    mode = args.mode or ("init" if args.title else "adopt-current")
    index_path = root / ".agentdocs" / "index.md"

    if mode == "adopt-current":
        wf = adopt_current(root)
        print(str(wf.relative_to(root)).replace("\\", "/"))
        return

    if mode == "init":
        if not args.title:
            raise SystemExit("--title is required for --mode init")
        existing_entries = parse_entries(index_path.read_text(encoding="utf-8"))
        has_default = any(e["kind"] == "DEFAULT" for e in existing_entries)
        if has_default and not args.allow_parallel:
            current = next(e for e in existing_entries if e["kind"] == "DEFAULT")
            raise SystemExit(
                f"Refusing to create a new workflow because a DEFAULT workflow already exists: {current['path']}. Use --mode resume, --mode adopt-current, or --allow-parallel."
            )
        wf, _task_id, _slug = create_workflow(root, args.title, args.issue)
        rel = str(wf.relative_to(root)).replace("\\", "/")
        promote_or_register(index_path, rel, args.title, allow_parallel=args.allow_parallel, make_default=not has_default)
        print(rel)
        return

    if mode == "resume":
        if not any([args.workflow, args.slug, args.issue]):
            raise SystemExit("resume mode requires one of --workflow, --slug, or --issue")
        matches = find_candidates(root, args.workflow, args.slug, args.issue)
        if not matches:
            raise SystemExit("No matching workflow found to resume.")
        if len(matches) > 1:
            listed = "\n".join(f"- {m.relative_to(root)}" for m in matches)
            raise SystemExit(f"Found multiple matching workflows; specify --workflow explicitly:\n{listed}")
        wf = matches[0]
        rel = str(wf.relative_to(root)).replace("\\", "/")
        title = read_title_from_workflow(wf)
        promote_or_register(index_path, rel, title, allow_parallel=args.allow_parallel, make_default=args.make_default)
        print(rel)
        return

    raise SystemExit(f"Unsupported mode: {mode}")


if __name__ == "__main__":
    main()
