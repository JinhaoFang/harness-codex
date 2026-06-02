#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

sys.dont_write_bytecode = True

from hook_sound import play as play_hook_sound


def root() -> Path:
    found = find_harness_root(Path.cwd().resolve()) or find_harness_root(Path(__file__).resolve().parents[2])
    if found:
        return found
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except FileNotFoundError:
        pass
    return Path.cwd()


def find_harness_root(start: Path) -> Optional[Path]:
    cur = start if start.is_dir() else start.parent
    while True:
        if (cur / ".harness" / "config.json").exists() and (cur / "harness" / "cli" / "harnessctl.py").exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent


def current_work_unit_id(base: Path) -> Optional[str]:
    cur = base / ".harness" / "current"
    if not cur.exists():
        return None
    wu_id = cur.read_text(encoding="utf-8").strip()
    return wu_id or None


def lifecycle_path(path: str) -> bool:
    return path.startswith(".harness/")


def has_changed_files(base: Path, wu_id: str) -> bool:
    try:
        status = subprocess.run(["git", "status", "--short"], cwd=base, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
        status_paths = []
        for line in status.stdout.splitlines():
            if not line.strip():
                continue
            path = line[3:].strip()
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            status_paths.append(path)
        if any(not lifecycle_path(path) for path in status_paths):
            return True
        state_path = base / ".harness" / "work-units" / "active" / wu_id / "state.json"
        base_commit = ""
        if state_path.exists():
            try:
                base_commit = json.loads(state_path.read_text(encoding="utf-8")).get("base_commit", "")
            except json.JSONDecodeError:
                base_commit = ""
        if base_commit:
            committed = subprocess.run(["git", "diff", "--name-only", f"{base_commit}..HEAD"], cwd=base, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
            return any(not lifecycle_path(path.strip()) for path in committed.stdout.splitlines() if path.strip())
        return False
    except FileNotFoundError:
        return False


def controller_gate(base: Path, wu_id: str, gate: str) -> tuple[bool, str, dict[str, Any]]:
    ctl = base / "harness" / "cli" / "harnessctl.py"
    if not ctl.exists():
        return False, f"Missing harness controller CLI; cannot verify {gate} gate.", {}
    proc = subprocess.run(
        [sys.executable, str(ctl), "--root", str(base), "check", "--id", wu_id, "--gate", gate, "--strict"],
        cwd=base,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode == 0:
        try:
            obj = json.loads(proc.stdout)
            decision = obj.get("decision")
            # WARN can mean a scoped waiver is present; do not block stop, but surface it.
            if decision in {"PASS", "WARN"}:
                reason = "; ".join(obj.get("warnings", [])) if decision == "WARN" else ""
                return True, reason, obj
        except json.JSONDecodeError:
            return False, f"Controller returned non-JSON {gate} output.", {}
    reason = proc.stdout.strip() or proc.stderr.strip() or f"{gate} gate blocked."
    try:
        obj = json.loads(proc.stdout)
    except json.JSONDecodeError:
        obj = {}
    return False, reason, obj


def controller_finalize(base: Path, wu_id: str) -> tuple[bool, str, dict[str, Any]]:
    ctl = base / "harness" / "cli" / "harnessctl.py"
    if not ctl.exists():
        return False, "Missing harness controller CLI; cannot run finalize-check.", {}
    proc = subprocess.run(
        [sys.executable, str(ctl), "--root", str(base), "finalize-check", "--id", wu_id, "--strict"],
        cwd=base,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    try:
        obj = json.loads(proc.stdout)
    except json.JSONDecodeError:
        obj = {}
    if proc.returncode == 0 and obj.get("decision") in {"PASS", "WARN"}:
        reason = "; ".join(obj.get("warnings", [])) if obj.get("decision") == "WARN" else ""
        return True, reason, obj
    reason = proc.stdout.strip() or proc.stderr.strip() or "finalize-check blocked."
    return False, reason, obj


def summarize_controller_block(obj: dict[str, Any], fallback: str) -> str:
    reasons = [str(x) for x in obj.get("blocking_reasons", []) if str(x).strip()]
    if not reasons:
        return fallback
    if len(reasons) == 1:
        return reasons[0]
    return f"{reasons[0]} (+{len(reasons) - 1} more)"


def stop_block(reason: str, gate: str, wu_id: str, next_action: str) -> None:
    command = f"python3 harness/cli/harnessctl.py check --id {wu_id} --gate {gate} --strict"
    stop_block_with_command(reason, wu_id, command, next_action)


def stop_block_with_command(reason: str, wu_id: str, command: str, next_action: str) -> None:
    msg = (
        f"Stop blocked for active Work Unit {wu_id}: {reason} "
        f"Next action: {next_action} Then run "
        f"`{command}`."
    )
    print(json.dumps({"decision": "block", "reason": msg}))


def main() -> int:
    base = root()
    wu_id = current_work_unit_id(base)
    if not wu_id:
        play_hook_sound("complete")
        return 0
    if not has_changed_files(base, wu_id):
        play_hook_sound("complete")
        return 0
    finalize_ok, finalize_reason, finalize_obj = controller_finalize(base, wu_id)
    if finalize_ok:
        play_hook_sound("complete")
        return 0
    if finalize_obj:
        summary = summarize_controller_block(finalize_obj, finalize_reason)
        command = f"python3 harness/cli/harnessctl.py finalize-check --id {wu_id} --strict"
        if finalize_obj.get("rerun_evidence_required"):
            stop_block_with_command(
                f"verification gate is not satisfied because {summary}. Do not summarize as complete.",
                wu_id,
                command,
                "refresh only the evidence claims marked requires_rerun=true, or create a scoped human-approved waiver if the evidence cannot be produced.",
            )
            return 0
        if finalize_obj.get("review_required"):
            stop_block_with_command(
                f"review validity gate is not satisfied because {summary}. Do not stop after implementation evidence alone.",
                wu_id,
                command,
                "request the minimal review type required by review_required_reasons, then wait for the reviewer verdict.",
            )
            return 0
        surfaces = finalize_obj.get("surfaces", {})
        if surfaces.get("publication") == "required":
            stop_block_with_command(
                f"publication surface is not satisfied because {summary}. Do not rerun implementation close review for publication metadata alone.",
                wu_id,
                command,
                "record the missing GitHub publication evidence or request publication review for the cited publication receipt.",
            )
            return 0
        stop_block_with_command(
            f"finalize-check is not satisfied because {summary}. Do not summarize as complete.",
            wu_id,
            command,
            str(finalize_obj.get("required_next_action") or "fix the blocking reasons reported by finalize-check."),
        )
        return 0

    verification_ok, verification_reason, verification_obj = controller_gate(base, wu_id, "verification")
    if not verification_ok:
        summary = summarize_controller_block(verification_obj, verification_reason)
        stop_block(
            f"verification gate is not satisfied because {summary}. Do not summarize as complete.",
            "verification",
            wu_id,
            "record fresh claim-relative evidence for the changed implementation, or create a scoped human-approved waiver if the evidence cannot be produced.",
        )
        return 0

    review_ok, review_reason, review_obj = controller_gate(base, wu_id, "review")
    if review_ok:
        play_hook_sound("complete")
        return 0
    summary = summarize_controller_block(review_obj, review_reason)
    stop_block(
        f"verification is satisfied, but close review gate is not satisfied because {summary}. Do not stop after implementation evidence alone.",
        "review",
        wu_id,
        "request close review, start the reviewer subagent with contract/diff/evidence inputs, and wait for the reviewer verdict.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
