#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


def root() -> Path:
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except FileNotFoundError:
        pass
    return Path.cwd()


def current_work_unit_id(base: Path) -> Optional[str]:
    cur = base / ".harness" / "current"
    if not cur.exists():
        return None
    wu_id = cur.read_text(encoding="utf-8").strip()
    return wu_id or None


def has_changed_files(base: Path, wu_id: str) -> bool:
    try:
        status = subprocess.run(["git", "status", "--short"], cwd=base, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
        if status.stdout.strip():
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
            return bool(committed.stdout.strip())
        return False
    except FileNotFoundError:
        return False


def controller_gate(base: Path, wu_id: str, gate: str) -> tuple[bool, str]:
    ctl = base / "harness" / "cli" / "harnessctl.py"
    if not ctl.exists():
        return False, f"Missing harness controller CLI; cannot verify {gate} gate."
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
                return True, reason
        except json.JSONDecodeError:
            return False, f"Controller returned non-JSON {gate} output."
    reason = proc.stdout.strip() or proc.stderr.strip() or f"{gate} gate blocked."
    return False, reason


def main() -> int:
    base = root()
    wu_id = current_work_unit_id(base)
    if not wu_id:
        return 0
    if not has_changed_files(base, wu_id):
        return 0
    verification_ok, verification_reason = controller_gate(base, wu_id, "verification")
    if not verification_ok:
        msg = (
            f"Active Work Unit {wu_id} has repository changes but the verification gate is not satisfied. "
            "Do not summarize as complete. Record fresh claim-relative evidence or create a scoped waiver, then run "
            f"`python3 harness/cli/harnessctl.py check --id {wu_id} --gate verification --strict`. "
            + verification_reason
        )
        print(json.dumps({"decision": "block", "reason": msg}))
        return 0

    review_ok, review_reason = controller_gate(base, wu_id, "review")
    if review_ok:
        return 0
    msg = (
        f"Active Work Unit {wu_id} has verified repository changes but the close review gate is not satisfied. "
        "Do not stop after implementation evidence alone. Request or submit the required close review, then run "
        f"`python3 harness/cli/harnessctl.py check --id {wu_id} --gate review --strict`. "
        + review_reason
    )
    print(json.dumps({"decision": "block", "reason": msg}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
