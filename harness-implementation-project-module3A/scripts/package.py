#!/usr/bin/env python3
"""Build and optionally verify a deterministic harness release archive."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

EXCLUDED_DIRS = {".git", ".harness", "__pycache__", ".pytest_cache", ".venv", ".mypy_cache", ".ruff_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
EXCLUDED_EXACT = {".harness-adoption.json"}
MANIFEST_NAME = "PACKAGE-MANIFEST.json"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def project_version(root: Path) -> str:
    match = re.search(r'^version\s*=\s*"([^"]+)"', (root / "pyproject.toml").read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise RuntimeError("pyproject.toml has no project version")
    return match.group(1)


def source_files(root: Path) -> list[Path]:
    rows: list[Path] = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.is_dir() or path.suffix in EXCLUDED_SUFFIXES or path.name in {MANIFEST_NAME, *EXCLUDED_EXACT}:
            continue
        rows.append(path)
    return sorted(rows, key=lambda value: value.relative_to(root).as_posix())


def zip_write_bytes(archive: zipfile.ZipFile, name: str, payload: bytes, mode: int = 0o644) -> None:
    info = zipfile.ZipInfo(name, FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (mode & 0xFFFF) << 16
    archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build(root: Path, output: Path) -> tuple[Path, dict[str, str]]:
    version = project_version(root)
    prefix = f"coding-agent-harness-v{version}"
    files = source_files(root)
    hashes = {path.relative_to(root).as_posix(): sha256(path.read_bytes()) for path in files}
    manifest = {
        "schema_version": "harness.package_manifest.v1",
        "version": version,
        "archive_root": prefix,
        "files": hashes,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    if temporary.exists():
        temporary.unlink()
    with zipfile.ZipFile(temporary, "w") as archive:
        for path in files:
            rel = path.relative_to(root).as_posix()
            mode = 0o755 if os.access(path, os.X_OK) else 0o644
            zip_write_bytes(archive, f"{prefix}/{rel}", path.read_bytes(), mode)
        zip_write_bytes(
            archive,
            f"{prefix}/{MANIFEST_NAME}",
            (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
    temporary.replace(output)
    return output, hashes


def verify_archive(output: Path) -> tuple[str, dict[str, str]]:
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        roots = {name.split("/", 1)[0] for name in names if "/" in name}
        if len(roots) != 1:
            raise RuntimeError("archive must contain exactly one top-level directory")
        prefix = next(iter(roots))
        manifest_name = f"{prefix}/{MANIFEST_NAME}"
        if manifest_name not in names:
            raise RuntimeError("archive manifest is missing")
        manifest = json.loads(archive.read(manifest_name))
        expected = manifest.get("files", {})
        if not isinstance(expected, dict):
            raise RuntimeError("archive manifest files map is invalid")
        actual: dict[str, str] = {}
        for name in names:
            if name.endswith("/") or name == manifest_name:
                continue
            rel = name[len(prefix) + 1 :]
            if (
                any(part in EXCLUDED_DIRS for part in Path(rel).parts)
                or Path(rel).suffix in EXCLUDED_SUFFIXES
                or Path(rel).name in EXCLUDED_EXACT
            ):
                raise RuntimeError(f"excluded runtime/cache asset leaked into package: {rel}")
            actual[rel] = sha256(archive.read(name))
        if actual != expected:
            missing = sorted(set(expected) - set(actual))
            extra = sorted(set(actual) - set(expected))
            changed = sorted(key for key in set(actual) & set(expected) if actual[key] != expected[key])
            raise RuntimeError(f"package hash mismatch missing={missing} extra={extra} changed={changed}")
        return prefix, actual


def run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int = 600,
) -> None:
    proc = subprocess.run(command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(
            "release verification failed: " + " ".join(command) + "\nstdout:\n" + proc.stdout + "\nstderr:\n" + proc.stderr
        )


def git_init_repo(root: Path, env: dict[str, str]) -> None:
    run(["git", "init"], cwd=root, env=env)
    run(["git", "config", "user.email", "release-test@example.com"], cwd=root, env=env)
    run(["git", "config", "user.name", "Harness Release Test"], cwd=root, env=env)
    (root / "README.md").write_text("fixture\n", encoding="utf-8")


def run_adoption_smoke(source_root: Path, env: dict[str, str]) -> None:
    for profile, required_path in (
        ("thin-shared-codex", ".agents/skills/harness-clarify/SKILL.md"),
        ("thin-shared-claude", ".claude/skills/harness-clarify/SKILL.md"),
    ):
        with tempfile.TemporaryDirectory(prefix=f"harness-adopt-{profile}-") as target_tmp:
            target = Path(target_tmp)
            git_init_repo(target, env)
            run([sys.executable, "scripts/adopt.py", "install", str(target), "--profile", profile, "--no-doctor"], cwd=source_root, env=env)
            if not (target / required_path).exists():
                raise RuntimeError(f"{profile} adoption did not install required skill asset {required_path}")
            run([sys.executable, str(source_root / "harness" / "cli" / "harnessctl.py"), "--root", str(target), "check", "--gate", "skills", "--strict"], cwd=source_root, env=env)


def run_release_checks(output: Path, *, skip_tests: bool = False) -> None:
    prefix, _ = verify_archive(output)
    with tempfile.TemporaryDirectory(prefix="harness-release-check-") as tmp:
        with zipfile.ZipFile(output) as archive:
            archive.extractall(tmp)
        root = Path(tmp) / prefix
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        commands: list[list[str]] = []
        if not skip_tests:
            commands.append([sys.executable, "-m", "unittest", "discover", "-s", "harness/tests", "-q"])
        commands.extend(
            [
                [sys.executable, "harness/cli/harnessctl.py", "doctor"],
                [sys.executable, "harness/cli/harnessctl.py", "ci", "--strict"],
                [sys.executable, "harness/cli/harnessctl.py", "validate", "--all", "--strict"],
                [sys.executable, "harness/cli/harnessctl.py", "check", "--gate", "skills", "--strict"],
            ]
        )
        for command in commands:
            run(command, cwd=root, env=env)
        run_adoption_smoke(root, env)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a deterministic coding-agent harness zip")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", action="store_true", help="extract the archive and run tests/controller gates")
    parser.add_argument("--skip-tests", action="store_true", help="with --verify, run structural gates but skip unittest")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    root = Path(__file__).resolve().parents[1]
    version = project_version(root)
    output = args.output.resolve() if args.output else root.parent / f"coding-agent-harness-v{version}.zip"
    built, hashes = build(root, output)
    verify_archive(built)
    if args.verify:
        run_release_checks(built, skip_tests=args.skip_tests)
    print(json.dumps({"archive": str(built), "version": version, "files": len(hashes), "verified": bool(args.verify)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, zipfile.BadZipFile, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
