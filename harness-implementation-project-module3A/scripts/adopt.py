#!/usr/bin/env python3
"""Install the harness into a target repository without overwriting user files."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Iterable, Union

PathSpec = Union[str, tuple[str, str]]

COMMON_PATHS: list[PathSpec] = [
    "docs/harness/README.md",
    "docs/harness/workflow.md",
    "docs/harness/risk-gates.md",
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
        "docs/harness/platform-adapters.md",
    ],
    "claude": [
        ("harness/templates/adoption/CLAUDE.md", "CLAUDE.md"),
        ".claude",
        "docs/harness/platform-adapters.md",
    ],
}

PROFILES = sorted(PLATFORM_PATHS)
APPEND_MARKERS = {
    "AGENTS.md": ("# BEGIN CODING AGENT HARNESS", "# END CODING AGENT HARNESS"),
    "CLAUDE.md": ("# BEGIN CODING AGENT HARNESS", "# END CODING AGENT HARNESS"),
}
GITIGNORE_ENTRIES = {
    "codex": [
        ".harness/",
        "harness/",
        "docs/harness/",
        ".codex/",
        "AGENTS.md",
        ".github/workflows/harness-checks.yml",
        "Makefile",
    ],
    "claude": [
        ".harness/",
        "harness/",
        "docs/harness/",
        ".claude/",
        "CLAUDE.md",
        ".github/workflows/harness-checks.yml",
        "Makefile",
    ],
}


def split_path_spec(spec: PathSpec) -> tuple[str, str]:
    if isinstance(spec, tuple):
        return spec
    return spec, spec


def path_spec_key(spec: PathSpec) -> str:
    _src, dst = split_path_spec(spec)
    return dst


def merge_gitignore(dst_root: Path, profile: str, dry_run: bool) -> str:
    path = dst_root / ".gitignore"
    entries = GITIGNORE_ENTRIES[profile]
    if path.exists():
        text = path.read_text(encoding="utf-8")
        lines = [line.strip() for line in text.splitlines()]
        missing = [entry for entry in entries if entry not in lines and entry.rstrip("/") not in lines]
        if not missing:
            return "kept .gitignore (harness entries already present)"
        if dry_run:
            return "would append harness entries to .gitignore: " + ", ".join(missing)
        prefix = "" if text.endswith("\n") or not text else "\n"
        path.write_text(text + prefix + "\n".join(missing) + "\n", encoding="utf-8")
        return "appended harness entries to .gitignore: " + ", ".join(missing)
    if dry_run:
        return "would create .gitignore"
    path.write_text("\n".join(entries) + "\n", encoding="utf-8")
    return "created .gitignore"


def append_marked_file(src: Path, dst: Path, dst_rel: str, dry_run: bool) -> str:
    begin, end = APPEND_MARKERS[dst_rel]
    body = src.read_text(encoding="utf-8").strip()
    block = f"{begin}\n{body}\n{end}\n"
    if dst.exists():
        text = dst.read_text(encoding="utf-8")
        if begin in text and end in text:
            return f"kept existing {dst_rel} harness block"
        if dry_run:
            return f"would append harness block to existing {dst_rel}"
        prefix = "" if text.endswith("\n") or not text else "\n"
        dst.write_text(text + prefix + "\n" + block, encoding="utf-8")
        return f"appended harness block to {dst_rel}"
    if dry_run:
        return f"would create {dst_rel}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(block, encoding="utf-8")
    return f"created {dst_rel}"


def copy_file_incremental(src: Path, dst: Path, dst_rel: str, dry_run: bool) -> str:
    if dst.exists():
        return f"kept existing {dst_rel}"
    if dry_run:
        return f"would copy {dst_rel}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return f"copied {dst_rel}"


def copy_dir_incremental(src: Path, dst: Path, dst_rel: str, dry_run: bool) -> list[str]:
    messages: list[str] = []
    for child in sorted(src.rglob("*")):
        if child.is_dir():
            continue
        if "__pycache__" in child.parts or child.suffix == ".pyc":
            continue
        rel = child.relative_to(src)
        target = dst / rel
        display = f"{dst_rel}/{rel.as_posix()}"
        messages.append(copy_file_incremental(child, target, display, dry_run))
    if not messages and not dst.exists():
        if dry_run:
            messages.append(f"would create {dst_rel}")
        else:
            dst.mkdir(parents=True, exist_ok=True)
            messages.append(f"created {dst_rel}")
    return messages


def copy_path(src_root: Path, dst_root: Path, spec: PathSpec, dry_run: bool) -> list[str]:
    src_rel, dst_rel = split_path_spec(spec)
    src = src_root / src_rel
    dst = dst_root / dst_rel
    if not src.exists():
        return [f"missing {src_rel}"]
    if dst_rel in APPEND_MARKERS:
        return [append_marked_file(src, dst, dst_rel, dry_run)]
    if src.is_dir():
        return copy_dir_incremental(src, dst, dst_rel, dry_run)
    return [copy_file_incremental(src, dst, dst_rel, dry_run)]


def profile_paths(profile: str) -> list[PathSpec]:
    paths = COMMON_PATHS + PLATFORM_PATHS[profile]
    deduped = list(dict.fromkeys(paths))
    return sorted(deduped, key=path_spec_key)


def init_harness(dst_root: Path, profile: str, dry_run: bool) -> str:
    if dry_run:
        return "would initialize .harness runtime state"
    for path in [
        dst_root / ".harness" / "work-units" / "active",
        dst_root / ".harness" / "work-units" / "archive",
        dst_root / ".harness" / "tmp",
    ]:
        path.mkdir(parents=True, exist_ok=True)
    config = dst_root / ".harness" / "config.json"
    if config.exists():
        return "kept existing .harness/config.json"
    config.write_text(
        json.dumps(
            {
                "schema_version": "harness.config.v1",
                "profile": profile,
                "created_by": "scripts/adopt.py install",
                "work_units_dir": ".harness/work-units",
                "default_required_gates": ["spec", "verification"],
                "high_risk_requires": ["independent_review_or_human_gate", "rollback_or_reopen_path"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return "initialized .harness/config.json"


def run_doctor(dst_root: Path, dry_run: bool) -> list[str]:
    if dry_run:
        return ["would run harness doctor"]
    ctl = dst_root / "harness" / "cli" / "harnessctl.py"
    if not ctl.exists():
        return ["skipped doctor (missing harness/cli/harnessctl.py)"]
    proc = subprocess.run([sys.executable, str(ctl), "doctor"], cwd=dst_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    out = [line for line in proc.stdout.splitlines() if line.strip()]
    if proc.stderr.strip():
        out.extend(f"doctor stderr: {line}" for line in proc.stderr.splitlines() if line.strip())
    return out or [f"doctor exited {proc.returncode}"]


def install(src_root: Path, dst_root: Path, profile: str, dry_run: bool, doctor: bool) -> int:
    print(f"installing profile={profile} into {dst_root}")
    print("mode=incremental; existing target files are kept or appended, not replaced")
    for rel in profile_paths(profile):
        for message in copy_path(src_root, dst_root, rel, dry_run):
            print(message)
    print(merge_gitignore(dst_root, profile, dry_run))
    print(init_harness(dst_root, profile, dry_run))
    if doctor:
        for line in run_doctor(dst_root, dry_run):
            print(line)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install the coding-agent harness into a repository.")
    sub = parser.add_subparsers(dest="cmd")

    install_parser = sub.add_parser("install", help="Install harness files into a target repository.")
    install_parser.add_argument("target", type=Path)
    install_parser.add_argument("--profile", choices=PROFILES, default="codex", help="Install profile. Defaults to codex.")
    install_parser.add_argument("--dry-run", action="store_true")
    install_parser.add_argument("--no-doctor", action="store_true", help="Skip post-install doctor check.")
    return parser


def normalize_legacy_args(argv: list[str]) -> list[str]:
    if argv and argv[0] not in {"install", "-h", "--help"}:
        return ["install", *argv]
    return argv


def main(argv: Iterable[str] | None = None) -> int:
    args_list = normalize_legacy_args(list(argv if argv is not None else sys.argv[1:]))
    parser = build_parser()
    args = parser.parse_args(args_list)
    if args.cmd is None:
        parser.print_help()
        return 2
    src_root = Path(__file__).resolve().parents[1]
    dst_root = args.target.resolve()
    return install(src_root, dst_root, args.profile, args.dry_run, not args.no_doctor)


if __name__ == "__main__":
    raise SystemExit(main())
