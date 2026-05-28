#!/usr/bin/env python3
"""Copy selected harness profiles into another repository."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil

COMMON_PATHS = [
    "AGENTS.md",
    "CLAUDE.md",
    "docs/harness/README.md",
    "docs/harness/workflow.md",
    "docs/harness/risk-gates.md",
    "docs/harness/platform-adapters.md",
    "harness/cli",
    "harness/hooks",
    "harness/schemas",
    "harness/templates",
]

THIN_SKILLS = [
    "skills/harness-clarify",
    "skills/harness-evidence",
    "skills/harness-handoff",
]

CONTROLLED_PATHS = [
    "harness/tests",
    ".github/workflows/harness-checks.yml",
    "Makefile",
]

CONTROLLED_SKILLS = [
    "skills/harness-clarify",
    "skills/harness-compound",
    "skills/harness-evidence",
    "skills/harness-ground",
    "skills/harness-handoff",
    "skills/harness-review",
    "skills/harness-spec",
    "skills/harness-tdd",
    "skills/harness-waiver",
]

GITHUB_SKILL = "skills/harness-github"
CODEX_PATHS = [".agents/skills", ".codex", "docs/harness/platform-adapters.md"]
CLAUDE_PATHS = [".claude", "docs/harness/platform-adapters.md"]

PROFILES = {
    "thin": COMMON_PATHS + THIN_SKILLS,
    "controlled": COMMON_PATHS + CONTROLLED_PATHS + CONTROLLED_SKILLS,
    "codex": COMMON_PATHS + CONTROLLED_PATHS + CONTROLLED_SKILLS + CODEX_PATHS,
    "claude": COMMON_PATHS + CONTROLLED_PATHS + CONTROLLED_SKILLS + CLAUDE_PATHS,
    "full": COMMON_PATHS + CONTROLLED_PATHS + CONTROLLED_SKILLS + [GITHUB_SKILL] + CODEX_PATHS + CLAUDE_PATHS + ["examples"],
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


def copy_path(src_root: Path, dst_root: Path, rel: str, force: bool, dry_run: bool) -> str:
    src = src_root / rel
    dst = dst_root / rel
    if not src.exists():
        return f"missing {rel}"
    if dst.exists():
        if not force:
            note = "merge-sensitive; " if rel in MERGE_SENSITIVE_PATHS or rel.split("/", 1)[0] in {".codex", ".claude"} else ""
            return f"skip existing {rel} ({note}use --force to replace)"
        if dry_run:
            return f"would replace {rel}"
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    elif dry_run:
        return f"would copy {rel}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
    return f"copied {rel}"


def profile_paths(profile: str, include_github: bool) -> list[str]:
    paths = list(PROFILES[profile])
    if include_github and GITHUB_SKILL not in paths:
        paths.append(GITHUB_SKILL)
    return sorted(dict.fromkeys(paths))


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
    for rel in profile_paths(args.profile, args.include_github):
        print(copy_path(src_root, dst_root, rel, args.force, args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
