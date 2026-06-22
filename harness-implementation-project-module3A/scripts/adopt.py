#!/usr/bin/env python3
"""Safely install, inspect, and upgrade tracked harness assets.

`.harness/` remains disposable local runtime. The small tracked adoption
manifest exists only to distinguish unmodified generated assets from files a
repository has edited, so upgrades can fail closed instead of overwriting user
work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Union

PathSpec = Union[str, tuple[str, str]]
MANIFEST_NAME = ".harness-adoption.json"
MANIFEST_SCHEMA = "harness.adoption_manifest.v1"

VENDORED_COMMON_PATHS: list[PathSpec] = [
    "docs/harness",
    "docs/spec/README.md",
    ("harness/templates/adoption/harnessctl", "harnessctl"),
    "harness/cli",
    "harness/core",
    "harness/hooks",
    "harness/platforms",
    "harness/schemas",
    "harness/templates",
    "skills",
    "scripts/adopt.py",
    "scripts/sync_platform_skills.py",
    ("harness/templates/adoption/harness-checks.yml", ".github/workflows/harness-checks.yml"),
    ("harness/templates/adoption/Makefile", "Makefile"),
]
THIN_SHARED_COMMON_PATHS: list[PathSpec] = [
    "docs/spec/README.md",
    ("harness/templates/adoption/thin-harness.lock", "harness.lock"),
    ("harness/templates/adoption/thin-project.yaml", "harness/project.yaml"),
    ("harness/templates/adoption/thin-docs-harness-README.md", "docs/harness/README.md"),
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
    "thin-shared-codex": [
        ("harness/templates/adoption/AGENTS.md", "AGENTS.md"),
        ("harness/templates/adoption/thin-codex-config.toml", ".codex/config.toml"),
        ("harness/templates/adoption/thin-codex-hooks.json", ".codex/hooks.json"),
        ".agents/skills",
        ("harness/templates/adoption/thin-harness.lock", "harness.lock"),
        ("harness/templates/adoption/thin-project.yaml", "harness/project.yaml"),
        ("harness/templates/adoption/thin-docs-harness-README.md", "docs/harness/README.md"),
    ],
    "thin-shared-claude": [
        ("harness/templates/adoption/CLAUDE.md", "CLAUDE.md"),
        ("harness/templates/adoption/thin-claude-settings.json", ".claude/settings.json"),
        ".claude/skills",
        ("harness/templates/adoption/thin-harness.lock", "harness.lock"),
        ("harness/templates/adoption/thin-project.yaml", "harness/project.yaml"),
        ("harness/templates/adoption/thin-docs-harness-README.md", "docs/harness/README.md"),
    ],
}
PROFILE_COMMON_PATHS: dict[str, list[PathSpec]] = {
    "codex": VENDORED_COMMON_PATHS,
    "claude": VENDORED_COMMON_PATHS,
    "thin-shared-codex": THIN_SHARED_COMMON_PATHS,
    "thin-shared-claude": THIN_SHARED_COMMON_PATHS,
}
PROFILES = sorted(PLATFORM_PATHS)
APPEND_MARKERS = {
    "AGENTS.md": ("# BEGIN CODING AGENT HARNESS", "# END CODING AGENT HARNESS"),
    "CLAUDE.md": ("# BEGIN CODING AGENT HARNESS", "# END CODING AGENT HARNESS"),
}
GITIGNORE_ENTRIES = (
    ".harness/",
    "docs/harness/",
    "harness/",
    "harnessctl",
    ".codex",
    ".claude",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes()) if path.exists() and path.is_file() else ""


def text_hash(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def source_version(root: Path) -> str:
    path = root / "pyproject.toml"
    if not path.exists():
        return "unknown"
    match = re.search(r'^version\s*=\s*"([^"]+)"', path.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1) if match else "unknown"


def split_spec(spec: PathSpec) -> tuple[str, str]:
    return spec if isinstance(spec, tuple) else (spec, spec)


def desired_files(src_root: Path, profile: str) -> list[tuple[Path, str, str]]:
    """Return (source file, source rel, target rel) in deterministic order."""
    rows: list[tuple[Path, str, str]] = []
    common = PROFILE_COMMON_PATHS.get(profile)
    if common is None:
        raise RuntimeError(f"unsupported adoption profile {profile!r}")
    specs = list(dict.fromkeys([*common, *PLATFORM_PATHS[profile]]))
    for spec in specs:
        src_rel, dst_rel = split_spec(spec)
        src = src_root / src_rel
        if not src.exists():
            print(f"warning: missing source asset {src_rel}", file=sys.stderr)
            continue
        if src.is_file():
            rows.append((src, src_rel, dst_rel))
            continue
        for child in sorted(src.rglob("*")):
            if child.is_dir() or "__pycache__" in child.parts or child.suffix == ".pyc":
                continue
            rel = child.relative_to(src).as_posix()
            rows.append((child, f"{src_rel}/{rel}", f"{dst_rel}/{rel}"))
    # A platform mirror can overlap canonical paths; one target has one owner.
    dedup: dict[str, tuple[Path, str, str]] = {}
    for row in rows:
        dedup[row[2]] = row
    return [dedup[key] for key in sorted(dedup)]


def marker_body(text: str, begin: str, end: str) -> tuple[str, int, int] | None:
    start = text.find(begin)
    if start < 0:
        return None
    body_start = start + len(begin)
    finish = text.find(end, body_start)
    if finish < 0:
        return None
    body = text[body_start:finish].strip("\n")
    return body, start, finish + len(end)


def rendered_marker(src: Path, rel: str) -> tuple[str, str]:
    begin, end = APPEND_MARKERS[rel]
    body = src.read_text(encoding="utf-8").strip()
    return body, f"{begin}\n{body}\n{end}"


def install_marker(src: Path, dst: Path, rel: str, dry_run: bool) -> tuple[str, dict[str, Any] | None]:
    begin, end = APPEND_MARKERS[rel]
    body, block = rendered_marker(src, rel)
    if dst.exists():
        text = dst.read_text(encoding="utf-8")
        existing = marker_body(text, begin, end)
        if existing:
            if existing[0].strip() == body:
                return f"managed existing {rel} harness block", {"mode": "marker", "source_rel": "", "installed_hash": text_hash(body)}
            return f"kept locally modified/unmanaged {rel} harness block", None
        if dry_run:
            return f"would append harness block to {rel}", {"mode": "marker", "source_rel": "", "installed_hash": text_hash(body)}
        prefix = "" if not text or text.endswith("\n") else "\n"
        dst.write_text(text + prefix + "\n" + block + "\n", encoding="utf-8")
        return f"appended harness block to {rel}", {"mode": "marker", "source_rel": "", "installed_hash": text_hash(body)}
    if dry_run:
        return f"would create {rel}", {"mode": "marker", "source_rel": "", "installed_hash": text_hash(body)}
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(block + "\n", encoding="utf-8")
    return f"created {rel}", {"mode": "marker", "source_rel": "", "installed_hash": text_hash(body)}


def install_file(src: Path, dst: Path, src_rel: str, dst_rel: str, dry_run: bool) -> tuple[str, dict[str, Any] | None]:
    source_hash = file_hash(src)
    if dst.exists():
        if file_hash(dst) == source_hash:
            return f"managed existing {dst_rel}", {"mode": "file", "source_rel": src_rel, "installed_hash": source_hash}
        return f"kept locally owned {dst_rel} (not added to upgrade manifest)", None
    if dry_run:
        return f"would copy {dst_rel}", {"mode": "file", "source_rel": src_rel, "installed_hash": source_hash}
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if src_rel.endswith("/harnessctl") or dst_rel == "harnessctl":
        dst.chmod(0o755)
    return f"copied {dst_rel}", {"mode": "file", "source_rel": src_rel, "installed_hash": source_hash}


def merge_gitignore(root: Path, dry_run: bool) -> str:
    path = root / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = {line.strip() for line in text.splitlines()}
    missing = [entry for entry in GITIGNORE_ENTRIES if entry not in lines and entry.rstrip("/") not in lines]
    if not missing:
        return "kept .gitignore (harness-owned local assets already ignored)"
    if dry_run:
        return "would append harness-owned paths to .gitignore"
    prefix = "" if not text or text.endswith("\n") else "\n"
    path.write_text(text + prefix + "".join(f"{entry}\n" for entry in missing), encoding="utf-8")
    return "appended harness-owned paths to .gitignore"


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
                "schema_version": "harness.config.v3",
                "profile": profile,
                "tracked_specs_dir": "docs/spec",
                "runtime_dir": ".harness",
                "runtime_tracked": False,
                "created_by": "scripts/adopt.py",
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return "initialized untracked .harness/config.json"


def write_manifest(target: Path, profile: str, version: str, managed: dict[str, Any], dry_run: bool) -> None:
    if dry_run:
        return
    payload = {
        "schema_version": MANIFEST_SCHEMA,
        "profile": profile,
        "source_version": version,
        "managed_files": {key: managed[key] for key in sorted(managed)},
    }
    path = target / MANIFEST_NAME
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_manifest(target: Path) -> dict[str, Any]:
    path = target / MANIFEST_NAME
    if not path.exists():
        raise RuntimeError(f"missing {MANIFEST_NAME}; run install before upgrade/check")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != MANIFEST_SCHEMA or not isinstance(value.get("managed_files"), dict):
        raise RuntimeError(f"unsupported or corrupt {MANIFEST_NAME}")
    return value


def run_doctor(root: Path, dry_run: bool) -> list[str]:
    if dry_run:
        return ["would run harness doctor"]
    ctl = root / "harness" / "cli" / "harnessctl.py"
    if not ctl.exists():
        return ["skipped doctor (controller missing)"]
    proc = subprocess.run(
        [sys.executable, str(ctl), "--root", str(root), "doctor"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env={**dict(__import__("os").environ), "PYTHONDONTWRITEBYTECODE": "1"},
    )
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if proc.stderr.strip():
        lines.extend(f"doctor stderr: {line}" for line in proc.stderr.splitlines() if line.strip())
    return lines or [f"doctor exited {proc.returncode}"]


def install(src_root: Path, target: Path, profile: str, dry_run: bool, doctor: bool) -> int:
    if (target / MANIFEST_NAME).exists():
        print(
            f"ERROR: {MANIFEST_NAME} already exists; use 'check' or 'upgrade' instead of reinstalling",
            file=sys.stderr,
        )
        return 2
    print(f"installing profile={profile} into {target}")
    print("mode=safe incremental; tracked harness assets remain visible; harness-owned local assets are added to .gitignore")
    managed: dict[str, Any] = {}
    for src, src_rel, dst_rel in desired_files(src_root, profile):
        dst = target / dst_rel
        if dst_rel in APPEND_MARKERS:
            message, entry = install_marker(src, dst, dst_rel, dry_run)
            if entry:
                entry["source_rel"] = src_rel
        else:
            message, entry = install_file(src, dst, src_rel, dst_rel, dry_run)
        print(message)
        if entry:
            managed[dst_rel] = entry
    print(merge_gitignore(target, dry_run))
    print(init_runtime(target, profile, dry_run))
    write_manifest(target, profile, source_version(src_root), managed, dry_run)
    if not dry_run:
        print(f"wrote {MANIFEST_NAME} for {len(managed)} safely managed files")
    if doctor:
        for line in run_doctor(target, dry_run):
            print(line)
    return 0


def current_managed_hash(target: Path, rel: str, entry: dict[str, Any]) -> str:
    path = target / rel
    if entry.get("mode") == "marker":
        if not path.exists() or rel not in APPEND_MARKERS:
            return ""
        begin, end = APPEND_MARKERS[rel]
        found = marker_body(path.read_text(encoding="utf-8"), begin, end)
        return text_hash(found[0].strip()) if found else ""
    return file_hash(path)


def check_installation(target: Path) -> int:
    try:
        manifest = load_manifest(target)
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    drift: list[str] = []
    for rel, raw in sorted(manifest["managed_files"].items()):
        entry = raw if isinstance(raw, dict) else {}
        current = current_managed_hash(target, rel, entry)
        if not current:
            drift.append(f"missing {rel}")
        elif current != str(entry.get("installed_hash", "")):
            drift.append(f"locally modified {rel}")
    decision = "PASS" if not drift else "BLOCK"
    print(json.dumps({"decision": decision, "profile": manifest.get("profile"), "source_version": manifest.get("source_version"), "managed_files": len(manifest["managed_files"]), "drift": drift}, ensure_ascii=False, indent=2))
    return 0 if not drift else 2


def replace_marker(path: Path, rel: str, new_body: str) -> None:
    begin, end = APPEND_MARKERS[rel]
    text = path.read_text(encoding="utf-8")
    found = marker_body(text, begin, end)
    if not found:
        raise RuntimeError(f"managed marker block missing in {rel}")
    _body, start, finish = found
    path.write_text(text[:start] + f"{begin}\n{new_body}\n{end}" + text[finish:], encoding="utf-8")


def upgrade(src_root: Path, target: Path, dry_run: bool, doctor: bool) -> int:
    try:
        old = load_manifest(target)
    except (RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    profile = str(old.get("profile", ""))
    if profile not in PLATFORM_PATHS:
        print(f"ERROR: manifest profile {profile!r} is unsupported", file=sys.stderr)
        return 2
    previous = old["managed_files"]
    managed: dict[str, Any] = {}
    desired = {dst_rel: (src, src_rel) for src, src_rel, dst_rel in desired_files(src_root, profile)}

    # Preflight every previously managed asset before writing anything. A
    # conflict discovered late in lexical order must not leave the target on a
    # half-upgraded Harness version.
    conflicts: list[str] = []
    for rel in sorted(desired):
        prior = previous.get(rel) if isinstance(previous.get(rel), dict) else None
        if not prior:
            continue
        src, _src_rel = desired[rel]
        if rel in APPEND_MARKERS:
            body, _block = rendered_marker(src, rel)
            new_hash = text_hash(body)
            current = current_managed_hash(target, rel, prior)
        else:
            new_hash = file_hash(src)
            current = file_hash(target / rel)
        if current not in {str(prior.get("installed_hash", "")), new_hash}:
            conflicts.append(rel)
    if conflicts:
        print("upgrade blocked by locally modified managed files:", file=sys.stderr)
        for rel in conflicts:
            print(f"  - {rel}", file=sys.stderr)
        return 2

    for rel in sorted(desired):
        src, src_rel = desired[rel]
        dst = target / rel
        prior = previous.get(rel) if isinstance(previous.get(rel), dict) else None
        if rel in APPEND_MARKERS:
            body, _block = rendered_marker(src, rel)
            new_hash = text_hash(body)
            if prior:
                current = current_managed_hash(target, rel, prior)
                if not dry_run and current != new_hash:
                    replace_marker(dst, rel, body)
                print(("would upgrade " if dry_run else "upgraded ") + f"{rel} harness block")
                managed[rel] = {"mode": "marker", "source_rel": src_rel, "installed_hash": new_hash}
            else:
                message, entry = install_marker(src, dst, rel, dry_run)
                print(message)
                if entry:
                    entry["source_rel"] = src_rel
                    managed[rel] = entry
            continue
        new_hash = file_hash(src)
        if prior:
            current = file_hash(dst)
            if not dry_run and current != new_hash:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                if src_rel.endswith("/harnessctl") or rel == "harnessctl":
                    dst.chmod(0o755)
            print(("would upgrade " if dry_run else "upgraded ") + rel)
            managed[rel] = {"mode": "file", "source_rel": src_rel, "installed_hash": new_hash}
        else:
            message, entry = install_file(src, dst, src_rel, rel, dry_run)
            print(message)
            if entry:
                managed[rel] = entry
    # Keep ownership records for removed source assets; never silently delete a repository file.
    for rel, entry in previous.items():
        if rel not in desired:
            managed[rel] = entry
            print(f"kept deprecated managed asset {rel}; removal requires an explicit migration")
    print(merge_gitignore(target, dry_run))
    print(init_runtime(target, profile, dry_run))
    write_manifest(target, profile, source_version(src_root), managed, dry_run)
    if doctor:
        for line in run_doctor(target, dry_run):
            print(line)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely adopt or upgrade the coding-agent harness")
    sub = parser.add_subparsers(dest="cmd")
    p = sub.add_parser("install")
    p.add_argument("target", type=Path)
    p.add_argument("--profile", choices=PROFILES, default="codex")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-doctor", action="store_true")
    p = sub.add_parser("check")
    p.add_argument("target", type=Path)
    p = sub.add_parser("upgrade")
    p.add_argument("target", type=Path)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-doctor", action="store_true")
    return parser


def normalize_legacy(argv: list[str]) -> list[str]:
    if argv and argv[0] not in {"install", "check", "upgrade", "-h", "--help"}:
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
    target = args.target.resolve()
    if args.cmd == "install":
        return install(src_root, target, args.profile, args.dry_run, not args.no_doctor)
    if args.cmd == "check":
        return check_installation(target)
    return upgrade(src_root, target, args.dry_run, not args.no_doctor)


if __name__ == "__main__":
    raise SystemExit(main())
