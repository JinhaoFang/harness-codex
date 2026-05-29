#!/usr/bin/env python3
"""Copy selected harness profiles into another repository."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
from typing import Union

PathSpec = Union[str, tuple[str, str]]

ADOPTION_DOCS: list[PathSpec] = [
    ("harness/templates/adoption/AGENTS.md", "AGENTS.md"),
    ("harness/templates/adoption/CLAUDE.md", "CLAUDE.md"),
]

COMMON_PATHS: list[PathSpec] = [
    *ADOPTION_DOCS,
    "docs/harness/README.md",
    "docs/harness/workflow.md",
    "docs/harness/risk-gates.md",
    "harness/cli",
    "harness/hooks",
    "harness/schemas",
    "harness/templates",
]

CONTROLLED_PATHS: list[PathSpec] = [
    "harness/tests",
    ".github/workflows/harness-checks.yml",
    "Makefile",
]

CODEX_PATHS: list[PathSpec] = [".agents/skills", ".codex", "docs/harness/platform-adapters.md"]
CLAUDE_PATHS: list[PathSpec] = [".claude", "docs/harness/platform-adapters.md"]

PROFILES = {
    "thin": COMMON_PATHS,
    "controlled": COMMON_PATHS + CONTROLLED_PATHS,
    "codex": COMMON_PATHS + CONTROLLED_PATHS + CODEX_PATHS,
    "claude": COMMON_PATHS + CONTROLLED_PATHS + CLAUDE_PATHS,
    "full": COMMON_PATHS + CONTROLLED_PATHS + CODEX_PATHS + CLAUDE_PATHS + ["examples"],
}

MERGE_SENSITIVE_PATHS = {
    ".codex",
    ".claude",
    ".agents/skills",
    ".github/workflows/harness-checks.yml",
    "AGENTS.md",
    "CLAUDE.md",
    "Makefile",
}


def split_path_spec(spec: PathSpec) -> tuple[str, str]:
    if isinstance(spec, tuple):
        return spec
    return spec, spec


def path_spec_key(spec: PathSpec) -> str:
    _src, dst = split_path_spec(spec)
    return dst


def copy_path(src_root: Path, dst_root: Path, spec: PathSpec, force: bool, dry_run: bool) -> str:
    src_rel, dst_rel = split_path_spec(spec)
    src = src_root / src_rel
    dst = dst_root / dst_rel
    if not src.exists():
        return f"missing {src_rel}"
    if dst.exists():
        if not force:
            note = "merge-sensitive; " if dst_rel in MERGE_SENSITIVE_PATHS or dst_rel.split("/", 1)[0] in {".codex", ".claude"} else ""
            return f"skip existing {dst_rel} ({note}use --force to replace)"
        if dry_run:
            return f"would replace {dst_rel}"
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    elif dry_run:
        return f"would copy {dst_rel}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    if src_rel != dst_rel:
        return f"copied {src_rel} -> {dst_rel}"
    return f"copied {dst_rel}"


def skill_paths(src_root: Path) -> list[PathSpec]:
    skills_root = src_root / "skills"
    if not skills_root.exists():
        return []
    return [str(path.relative_to(src_root)) for path in sorted(skills_root.iterdir(), key=lambda p: p.name)]


def profile_paths(src_root: Path, profile: str, include_github: bool) -> list[PathSpec]:
    paths = list(PROFILES[profile])
    paths.extend(skill_paths(src_root))
    if include_github:
        # Kept for CLI compatibility. GitHub skill is now part of the canonical
        # skills catalog copied by every profile.
        pass
    deduped = list(dict.fromkeys(paths))
    return sorted(deduped, key=path_spec_key)


def main() -> int:
    parser = argparse.ArgumentParser(description="Adopt the coding-agent harness into another repository.")
    parser.add_argument("target", type=Path)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="thin", help="Adoption profile. Defaults to thin.")
    parser.add_argument("--include-github", action="store_true", help="Also copy the GitHub collaboration skill.")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    src_root = Path(__file__).resolve().parents[1]
    dst_root = args.target.resolve()
    print(f"adopting profile={args.profile} into {dst_root}")
    if args.profile in {"codex", "claude", "full"}:
        print("note: platform adapter files can conflict with existing project settings; prefer merge review over blind --force.")
    for rel in profile_paths(src_root, args.profile, args.include_github):
        print(copy_path(src_root, dst_root, rel, args.force, args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
