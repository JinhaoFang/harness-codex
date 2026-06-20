#!/usr/bin/env python3
"""Incrementally install the harness without hiding tracked implementation assets."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Union

PathSpec = Union[str, tuple[str, str]]

COMMON_PATHS: list[PathSpec] = [
    "docs/harness/README.md",
    "docs/harness/workflow.md",
    "docs/harness/risk-gates.md",
    "docs/harness/platform-adapters.md",
    "docs/spec/README.md",
    "harness/cli",
    "harness/hooks",
    "harness/schemas",
    "harness/templates",
    "harness/tests",
    ".github/workflows/harness-checks.yml",
    "Makefile",
]
PLATFORM_PATHS: dict[str, list[PathSpec]] = {
    "codex": [
        ("harness/templates/adoption/AGENTS.md", "AGENTS.md"),
        ".codex",
        ".agents/skills",
    ],
    "claude": [
        ("harness/templates/adoption/CLAUDE.md", "CLAUDE.md"),
        ".claude",
    ],
}
PROFILES = sorted(PLATFORM_PATHS)
APPEND_MARKERS = {
    "AGENTS.md": ("# BEGIN CODING AGENT HARNESS", "# END CODING AGENT HARNESS"),
    "CLAUDE.md": ("# BEGIN CODING AGENT HARNESS", "# END CODING AGENT HARNESS"),
}


def split_spec(spec: PathSpec) -> tuple[str, str]:
    return spec if isinstance(spec, tuple) else (spec, spec)


def append_marked(src: Path, dst: Path, rel: str, dry_run: bool) -> str:
    begin, end = APPEND_MARKERS[rel]
    block = f"{begin}\n{src.read_text(encoding='utf-8').strip()}\n{end}\n"
    if dst.exists():
        text = dst.read_text(encoding="utf-8")
        if begin in text and end in text:
            return f"kept existing {rel} harness block"
        if dry_run:
            return f"would append harness block to {rel}"
        prefix = "" if not text or text.endswith("\n") else "\n"
        dst.write_text(text + prefix + "\n" + block, encoding="utf-8")
        return f"appended harness block to {rel}"
    if dry_run:
        return f"would create {rel}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(block, encoding="utf-8")
    return f"created {rel}"


def copy_file(src: Path, dst: Path, rel: str, dry_run: bool) -> str:
    if dst.exists():
        return f"kept existing {rel}"
    if dry_run:
        return f"would copy {rel}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return f"copied {rel}"


def copy_path(src_root: Path, dst_root: Path, spec: PathSpec, dry_run: bool) -> list[str]:
    src_rel, dst_rel = split_spec(spec)
    src, dst = src_root / src_rel, dst_root / dst_rel
    if not src.exists():
        return [f"missing {src_rel}"]
    if dst_rel in APPEND_MARKERS:
        return [append_marked(src, dst, dst_rel, dry_run)]
    if src.is_file():
        return [copy_file(src, dst, dst_rel, dry_run)]
    messages: list[str] = []
    for child in sorted(src.rglob("*")):
        if child.is_dir() or "__pycache__" in child.parts or child.suffix == ".pyc":
            continue
        rel = child.relative_to(src)
        messages.append(copy_file(child, dst / rel, f"{dst_rel}/{rel.as_posix()}", dry_run))
    return messages


def merge_gitignore(root: Path, dry_run: bool) -> str:
    path = root / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = {line.strip() for line in text.splitlines()}
    if ".harness/" in lines or ".harness" in lines:
        return "kept .gitignore (.harness runtime already ignored)"
    if dry_run:
        return "would append .harness/ to .gitignore"
    prefix = "" if not text or text.endswith("\n") else "\n"
    path.write_text(text + prefix + ".harness/\n", encoding="utf-8")
    return "appended .harness/ to .gitignore"


def init_runtime(root: Path, profile: str, dry_run: bool) -> str:
    if dry_run:
        return "would initialize untracked .harness runtime"
    for path in [
        root / ".harness" / "work-units" / "active",
        root / ".harness" / "work-units" / "archive",
        root / ".harness" / "runtime",
        root / ".harness" / "tmp",
        root / "docs" / "spec",
    ]:
        path.mkdir(parents=True, exist_ok=True)
    config = root / ".harness" / "config.json"
    if config.exists():
        return "kept existing .harness/config.json"
    config.write_text(
        json.dumps(
            {
                "schema_version": "harness.config.v2",
                "profile": profile,
                "tracked_specs_dir": "docs/spec",
                "runtime_dir": ".harness",
                "runtime_tracked": False,
                "created_by": "scripts/adopt.py",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return "initialized untracked .harness/config.json"


def run_doctor(root: Path, dry_run: bool) -> list[str]:
    if dry_run:
        return ["would run harness doctor"]
    ctl = root / "harness" / "cli" / "harnessctl.py"
    if not ctl.exists():
        return ["skipped doctor (controller missing)"]
    proc = subprocess.run([sys.executable, str(ctl), "--root", str(root), "doctor"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if proc.stderr.strip():
        lines.extend(f"doctor stderr: {line}" for line in proc.stderr.splitlines() if line.strip())
    return lines or [f"doctor exited {proc.returncode}"]


def install(src_root: Path, target: Path, profile: str, dry_run: bool, doctor: bool) -> int:
    print(f"installing profile={profile} into {target}")
    print("mode=incremental; tracked harness assets remain visible to Git; only .harness runtime is ignored")
    paths = list(dict.fromkeys([*COMMON_PATHS, *PLATFORM_PATHS[profile]]))
    for spec in sorted(paths, key=lambda value: split_spec(value)[1]):
        for message in copy_path(src_root, target, spec, dry_run):
            print(message)
    print(merge_gitignore(target, dry_run))
    print(init_runtime(target, profile, dry_run))
    if doctor:
        for line in run_doctor(target, dry_run):
            print(line)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    p = sub.add_parser("install")
    p.add_argument("target", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="codex")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-doctor", action="store_true")
    return parser


def normalize_legacy(argv: list[str]) -> list[str]:
    if argv and argv[0] not in {"install", "-h", "--help"}:
        return ["install", *argv]
    return argv


def main(argv: Iterable[str] | None = None) -> int:
    args_list = normalize_legacy(list(argv if argv is not None else sys.argv[1:]))
    parser = build_parser()
    args = parser.parse_args(args_list)
    if args.cmd is None:
        parser.print_help()
        return 2
    src_root = Path(__file__).resolve().parents[1]
    return install(src_root, args.target.resolve(), args.profile, args.dry_run, not args.no_doctor)


if __name__ == "__main__":
    raise SystemExit(main())
