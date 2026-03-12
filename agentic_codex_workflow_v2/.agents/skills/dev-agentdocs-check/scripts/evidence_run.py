#!/usr/bin/env python3
"""Run a verification command and capture a reproducible evidence bundle.

Creates (V2 preferred): .agentdocs/tasks/<task-id>/evidence/<phase>/<timestamp>/
Legacy fallback:        .agentdocs/evidence/<task-id>/<phase>/<timestamp>/
  - meta.json
  - stdout.txt
  - stderr.txt

This is intentionally minimal and offline-friendly.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(cwd: Path) -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(cwd), stderr=subprocess.DEVNULL)
        return out.decode().strip()
    except Exception:
        return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", required=True, help="Workflow path (used to locate repo root & task_id)")
    ap.add_argument("--phase", required=True, help="Phase label, e.g., P1")
    ap.add_argument("--task-id", default="", help="Override task_id (optional)")
    ap.add_argument("--cwd", default=".", help="Command working directory (relative to repo root)")
    ap.add_argument("--out", default="", help="Optional: write bundle path to this file")
    ap.add_argument("--result", choices=["AUTO", "PASS", "FAIL", "DEGRADED"], default="AUTO")
    ap.add_argument("--why", default="", help="Required when --result DEGRADED")
    ap.add_argument("--instead", default="", help="Required when --result DEGRADED")
    ap.add_argument("--to-run-later", default="", help="Required when --result DEGRADED")
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to run (prefix with --)")
    args = ap.parse_args()

    wf = Path(args.workflow).resolve()
    if not wf.exists():
        print(f"ERROR: workflow not found: {wf}")
        sys.exit(2)

    # Determine repo root
    root = wf
    while root.name != ".agentdocs" and root.parent != root:
        root = root.parent
    if root.name == ".agentdocs":
        repo = root.parent
    elif (wf.parents[1] / ".agentdocs").exists():
        repo = wf.parents[1]
    else:
        repo = wf.parent

    wf_text = wf.read_text(encoding="utf-8")
    task_id = args.task_id
    if not task_id:
        for line in wf_text.splitlines():
            if line.startswith("task_id:"):
                task_id = line.split(":", 1)[1].strip()
                break
    if not task_id:
        task_id = dt.datetime.now().strftime("%y%m%d%H%M")

    if not args.cmd or (len(args.cmd) == 1 and args.cmd[0] == "--"):
        print("ERROR: missing command. Example: evidence_run.py --workflow ... --phase P1 -- pytest -q")
        sys.exit(2)

    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]

    cwd = (repo / args.cwd).resolve()
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    if wf.parent.name == task_id and wf.parent.parent.name == "tasks":
        bundle = repo / ".agentdocs" / "tasks" / task_id / "evidence" / args.phase / ts
    else:
        bundle = repo / ".agentdocs" / "evidence" / task_id / args.phase / ts
    bundle.mkdir(parents=True, exist_ok=True)

    stdout_p = bundle / "stdout.txt"
    stderr_p = bundle / "stderr.txt"

    started = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

    print(f"[evidence] running: {' '.join(cmd)}")
    print(f"[evidence] cwd: {cwd}")
    print(f"[evidence] bundle: {bundle}")

    proc = subprocess.Popen(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = proc.communicate()
    stdout_p.write_text(out, encoding="utf-8")
    stderr_p.write_text(err, encoding="utf-8")

    ended = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

    if args.result == "DEGRADED":
        missing = [label for label, value in {"why": args.why, "instead": args.instead, "to_run_later": args.to_run_later}.items() if not value.strip()]
        if missing:
            print(f"ERROR: --result DEGRADED requires: {', '.join(missing)}")
            sys.exit(2)

    if args.result == "AUTO":
        final_result = "PASS" if proc.returncode == 0 else "FAIL"
    else:
        final_result = args.result

    meta: Dict[str, Any] = {
        "command": cmd,
        "cwd": str(cwd.relative_to(repo)) if str(cwd).startswith(str(repo)) else str(cwd),
        "started_at": started,
        "ended_at": ended,
        "exit_code": proc.returncode,
        "result": final_result,
        "git_head": git_head(cwd),
        "stdout": {"path": str(stdout_p.relative_to(repo)), "sha256": sha256_file(stdout_p)},
        "stderr": {"path": str(stderr_p.relative_to(repo)), "sha256": sha256_file(stderr_p)},
    }
    if final_result == "DEGRADED":
        meta.update(
            {
                "why": args.why,
                "instead": args.instead,
                "to_run_later": args.to_run_later,
            }
        )

    (bundle / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"[evidence] exit_code={proc.returncode}")
    print(f"[evidence] result={final_result}")
    print(f"[evidence] meta: {bundle / 'meta.json'}")

    if args.out:
        Path(args.out).write_text(str(bundle.relative_to(repo)).replace("\\", "/") + "\n", encoding="utf-8")

    sys.exit(0 if final_result in {"PASS", "DEGRADED"} else 1)


if __name__ == "__main__":
    main()
