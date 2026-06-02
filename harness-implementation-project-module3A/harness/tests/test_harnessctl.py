import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import shutil
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace

from harness.cli import harnessctl

os.environ.setdefault("HARNESS_HOOK_SOUND", "0")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CTL = PROJECT_ROOT / "harness" / "cli" / "harnessctl.py"


def run(root, *args, check=True):
    if os.environ.get("HARNESS_TEST_TRACE"):
        print("RUNCTL", args, flush=True)
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = harnessctl.main(["--root", str(root), *args])
    proc = SimpleNamespace(returncode=code, stdout=stdout.getvalue(), stderr=stderr.getvalue())
    if check and proc.returncode != 0:
        raise AssertionError(f"command failed: {args}\nstdout={proc.stdout}\nstderr={proc.stderr}")
    return proc


def make_repo():
    tmp = Path(tempfile.mkdtemp(prefix="harness-test-"))
    subprocess.run(["git", "init"], cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=10)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, check=True, timeout=10)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp, check=True, timeout=10)
    (tmp / "README.md").write_text("test\n", encoding="utf-8")
    # Copy only the runtime assets needed by harnessctl and hooks; do not copy the
    # test suite into the fixture repo because untracked test files make git status
    # and diff checks noisy.
    subprocess.run(["cp", "-R", str(PROJECT_ROOT / "harness"), str(tmp / "harness")], check=True, timeout=10)
    subprocess.run(["rm", "-rf", str(tmp / "harness" / "tests"), str(tmp / "harness" / "__pycache__"), str(tmp / "harness" / "cli" / "__pycache__"), str(tmp / "harness" / "hooks" / "__pycache__")], check=False, timeout=10)
    (tmp / "AGENTS.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp, check=True, timeout=10)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=10)
    return tmp


def set_required_evidence(root, wu_id, ids):
    contract = root / ".harness" / "work-units" / "active" / wu_id / "contract.md"
    text = contract.read_text(encoding="utf-8")
    block = "## Required evidence\n\n" + "\n".join(
        f"- id: {ev_id}\n  claim: {ev_id} claim\n  command: true\n  required_for_completion: true"
        for ev_id in ids
    ) + "\n\n## Stop conditions"
    start = text.index("## Required evidence")
    end = text.index("## Stop conditions")
    contract.write_text(text[:start] + block + text[end + len("## Stop conditions"):], encoding="utf-8")


def set_scope(root, wu_id, write_boundary, out_of_bounds):
    contract = root / ".harness" / "work-units" / "active" / wu_id / "contract.md"
    text = contract.read_text(encoding="utf-8")
    block = "## Scope\n\n### Likely changed areas\n\n- " + "\n- ".join(write_boundary or ["none"]) + "\n\n### Write boundary\n\n" + "\n".join(f"- {x}" for x in write_boundary) + "\n\n### Out of bounds\n\n" + "\n".join(f"- {x}" for x in out_of_bounds) + "\n\n## Required evidence"
    start = text.index("## Scope")
    end = text.index("## Required evidence")
    contract.write_text(text[:start] + block + text[end + len("## Required evidence"):], encoding="utf-8")


def fill_contract(root, wu_id, risk="medium", open_questions="none"):
    contract = root / ".harness" / "work-units" / "active" / wu_id / "contract.md"
    body = f"""# Work Unit Contract: {wu_id}

```yaml
id: "{wu_id}"
title: "Test"
type: "bugfix"
risk: "{risk}"
```

## Intent

Fix a bounded test behavior.

## Expected Outcome

- Observable behavior is corrected.

## Non-goals

- Do not change unrelated modules.

## Scope

### Likely changed areas

- src/**

### Write boundary

- src/**

### Out of bounds

- secrets/**

## Required evidence

- id: EV1
  claim: Targeted test passes.
  command: python3 -m unittest
  required_for_completion: true

## Stop conditions

### Success

- EV1 passes after the change.

### Blocked

- Scope needs to cross secrets/**.

## Clarification record

- user_confirmed: yes
- repo_grounded: yes
- user_intent_confidence: 95
- project_reality_confidence: 95
- key_decisions: Test behavior and evidence surface are confirmed.
- remaining_assumptions: none

## Open questions

- {open_questions}

## Context pointers

- contract.md
- src/**

## Risk notes

- Medium risk because it changes behavior.
"""
    contract.write_text(body, encoding="utf-8")


class HarnessCtlTests(unittest.TestCase):
    def test_controller_evidence_review_and_hook_gates(self):
        root = make_repo()
        try:
            run(root, "init")
            gitignore = root / ".gitignore"
            self.assertEqual(gitignore.read_text(encoding="utf-8").splitlines().count(".harness/"), 1)
            run(root, "init")
            self.assertEqual(gitignore.read_text(encoding="utf-8").splitlines().count(".harness/"), 1)
            run(root, "new", "--id", "WU-1", "--title", "Test", "--type", "bugfix", "--risk", "low")
            set_required_evidence(root, "WU-1", ["EV1", "EV2"])

            run(root, "evidence", "--id", "WU-1", "--claim", "EV1", "--type", "test", "--result", "pass", "--command", "true")
            proc = run(root, "check", "--id", "WU-1", "--gate", "verification", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("EV2", proc.stdout)

            run(root, "waiver", "--id", "WU-1", "--approved-by", "human:owner@example.com", "--requirement", "EV2", "--reason", "Cannot run", "--replacement-evidence", "Manual inspection", "--risk-accepted", "Temporary risk")
            proc = run(root, "check", "--id", "WU-1", "--gate", "verification", "--strict")
            self.assertIn('"decision": "WARN"', proc.stdout)
            self.assertIn("scoped waiver", proc.stdout)

            run(root, "new", "--id", "WU-2", "--title", "Wrong claim", "--type", "bugfix", "--risk", "low")
            set_required_evidence(root, "WU-2", ["EV1"])
            run(root, "evidence", "--id", "WU-2", "--claim", "EVX", "--type", "test", "--result", "pass", "--command", "true")
            proc = run(root, "check", "--id", "WU-2", "--gate", "verification", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("Missing fresh pass evidence for required claim EV1", proc.stdout)
            self.assertIn("non-contract claim EVX", proc.stdout)

            (root / "README.md").write_text("changed\n", encoding="utf-8")
            hook = root / "harness" / "hooks" / "stop_without_evidence.py"
            proc = subprocess.run([sys.executable, str(hook)], cwd=root, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            out = json.loads(proc.stdout)
            self.assertEqual(out["decision"], "block")
            self.assertIn("verification gate", out["reason"])
            self.assertIn("Next action:", out["reason"])
            self.assertIn("requires_rerun=true", out["reason"])
            self.assertNotIn("hookSpecificOutput", out)

            run(root, "new", "--id", "WU-STOP-REVIEW", "--title", "Stop Review", "--type", "bugfix", "--risk", "medium")
            fill_contract(root, "WU-STOP-REVIEW")
            (root / "src").mkdir(exist_ok=True)
            (root / "src" / "stop_review.py").write_text("value = 1\n", encoding="utf-8")
            run(root, "evidence", "--id", "WU-STOP-REVIEW", "--claim", "EV1", "--type", "test", "--result", "pass", "--command", "true", "--command-log-ref", ".harness/work-units/active/WU-STOP-REVIEW/evidence/artifacts/test.log")
            proc = subprocess.run([sys.executable, str(hook)], cwd=root, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            out = json.loads(proc.stdout)
            self.assertEqual(out["decision"], "block")
            self.assertIn("review validity gate", out["reason"])
            self.assertIn("minimal review type", out["reason"])

            with self.assertRaises(harnessctl.HarnessError) as ctx:
                harnessctl.submit_review(argparse.Namespace(
                    root=root, id="WU-2", request_id=None, mode="close", decision="PASS",
                    reviewer_role="agent", builder_role="agent", independence_level="fresh_context",
                    evidence_ref=None, finding=None, required_rework=None,
                ))
            self.assertIn("builder", str(ctx.exception).lower())
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_codex_hook_json_shapes(self):
        root = make_repo()
        try:
            pre_tool = root / "harness" / "hooks" / "pre_tool_use_policy.py"
            event = {"tool_name": "bash", "tool_input": {"command": "git reset --hard"}}
            proc = subprocess.run([sys.executable, str(pre_tool)], cwd=root, input=json.dumps(event), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            out = json.loads(proc.stdout)
            self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PreToolUse")
            self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

            event = {"tool_name": "bash", "tool_input": {"command": "npm publish"}}
            proc = subprocess.run([sys.executable, str(pre_tool), "--platform", "codex"], cwd=root, input=json.dumps(event), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            out = json.loads(proc.stdout)
            self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PreToolUse")
            self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
            self.assertIn("must not emit ask", out["hookSpecificOutput"]["permissionDecisionReason"])

            proc = subprocess.run([sys.executable, str(pre_tool), "--platform", "claude"], cwd=root, input=json.dumps(event), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            out = json.loads(proc.stdout)
            self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")

            permission = root / "harness" / "hooks" / "permission_request_policy.py"
            proc = subprocess.run([sys.executable, str(permission)], cwd=root, input=json.dumps(event), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            self.assertEqual(proc.stdout, "")

            event = {"tool_name": "bash", "tool_input": {"command": "git status --short"}}
            proc = subprocess.run([sys.executable, str(pre_tool)], cwd=root, input=json.dumps(event), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            self.assertEqual(proc.stdout, "")

            stop = root / "harness" / "hooks" / "stop_without_evidence.py"
            proc = subprocess.run([sys.executable, str(stop)], cwd=root, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            self.assertEqual(proc.stdout, "")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_hooks_find_harness_root_inside_outer_git_repo(self):
        outer = Path(tempfile.mkdtemp(prefix="harness-outer-"))
        try:
            subprocess.run(["git", "init"], cwd=outer, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=10)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=outer, check=True, timeout=10)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=outer, check=True, timeout=10)
            root = outer / "nested"
            root.mkdir()
            (root / "README.md").write_text("test\n", encoding="utf-8")
            subprocess.run(["cp", "-R", str(PROJECT_ROOT / "harness"), str(root / "harness")], check=True, timeout=10)
            subprocess.run(["rm", "-rf", str(root / "harness" / "tests"), str(root / "harness" / "__pycache__"), str(root / "harness" / "cli" / "__pycache__"), str(root / "harness" / "hooks" / "__pycache__")], check=False, timeout=10)
            (root / "AGENTS.md").write_text("test\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=outer, check=True, timeout=10)
            subprocess.run(["git", "commit", "-m", "init"], cwd=outer, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=10)

            run(root, "init")
            run(root, "new", "--id", "WU-NESTED-HOOK", "--title", "Nested Hook", "--type", "test", "--risk", "low")
            context = root / "harness" / "hooks" / "context_router.py"
            proc = subprocess.run([sys.executable, str(context), "SubagentStart"], cwd=root, text=True, input=json.dumps({"agent_type": "harness_reviewer"}), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            out = json.loads(proc.stdout)
            self.assertIn("active Work Unit WU-NESTED-HOOK", out["hookSpecificOutput"]["additionalContext"])
            self.assertIn("Reviewer must not ask", out["hookSpecificOutput"]["additionalContext"])
        finally:
            shutil.rmtree(outer, ignore_errors=True)

    def test_scope_gate_catches_committed_out_of_bounds_diff(self):
        root = make_repo()
        try:
            run(root, "init")
            run(root, "new", "--id", "WU-SCOPE", "--title", "Scope", "--type", "bugfix", "--risk", "low")
            set_scope(root, "WU-SCOPE", ["src/**"], ["secrets/**"])
            (root / "secrets").mkdir()
            (root / "secrets" / "prod.txt").write_text("do not touch\n", encoding="utf-8")
            subprocess.run(["git", "add", "secrets/prod.txt"], cwd=root, check=True, timeout=10)
            subprocess.run(["git", "commit", "-m", "test: committed out of bounds"], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=10)

            proc = run(root, "check", "--id", "WU-SCOPE", "--gate", "scope", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("Changed out-of-bounds path: secrets/prod.txt", proc.stdout)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_medium_evidence_requires_reviewable_support(self):
        root = make_repo()
        try:
            run(root, "init")
            run(root, "new", "--id", "WU-EVIDENCE", "--title", "Evidence", "--type", "bugfix", "--risk", "medium")
            set_required_evidence(root, "WU-EVIDENCE", ["EV1"])
            run(root, "evidence", "--id", "WU-EVIDENCE", "--claim", "EV1", "--type", "test", "--result", "pass", "--command", "true")
            proc = run(root, "check", "--id", "WU-EVIDENCE", "--gate", "verification", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("command text alone is not enough", proc.stdout)

            run(root, "new", "--id", "WU-EVIDENCE-2", "--title", "Evidence 2", "--type", "bugfix", "--risk", "medium")
            set_required_evidence(root, "WU-EVIDENCE-2", ["EV1"])
            run(root, "evidence", "--id", "WU-EVIDENCE-2", "--claim", "EV1", "--type", "test", "--result", "pass", "--command", "true", "--command-log-ref", ".harness/work-units/active/WU-EVIDENCE-2/evidence/artifacts/test.log")
            proc = run(root, "check", "--id", "WU-EVIDENCE-2", "--gate", "verification", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_medium_review_pass_must_cite_fresh_evidence_refs(self):
        root = make_repo()
        try:
            run(root, "init")
            run(root, "new", "--id", "WU-REVIEW", "--title", "Review", "--type", "bugfix", "--risk", "medium")
            set_required_evidence(root, "WU-REVIEW", ["EV1"])
            receipt_proc = run(root, "evidence", "--id", "WU-REVIEW", "--claim", "EV1", "--type", "test", "--result", "pass", "--command", "true", "--command-log-ref", ".harness/work-units/active/WU-REVIEW/evidence/artifacts/test.log")
            receipt_id = json.loads(receipt_proc.stdout)["receipt_id"]

            run(root, "submit-review", "--id", "WU-REVIEW", "--mode", "close", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context")
            proc = run(root, "check", "--id", "WU-REVIEW", "--gate", "review", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("must cite an evidence snapshot or receipt ID at least once", proc.stdout)

            run(root, "submit-review", "--id", "WU-REVIEW", "--mode", "close", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context", "--evidence-ref", receipt_id)
            proc = run(root, "check", "--id", "WU-REVIEW", "--gate", "review", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)
            state = json.loads((root / ".harness" / "work-units" / "active" / "WU-REVIEW" / "state.json").read_text(encoding="utf-8"))
            self.assertIn("Archive locally", state["next_safe_action"])
            self.assertIn("follow-up Work Unit", state["next_safe_action"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_non_implementation_context_change_does_not_stale_verified_work(self):
        root = make_repo()
        try:
            run(root, "init")
            run(root, "new", "--id", "WU-LIFECYCLE", "--title", "Lifecycle", "--type", "bugfix", "--risk", "medium")
            fill_contract(root, "WU-LIFECYCLE")
            run(root, "lock", "--id", "WU-LIFECYCLE", "--status", "ready")
            run(root, "submit-review", "--id", "WU-LIFECYCLE", "--mode", "plan", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context")

            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("value = 1\n", encoding="utf-8")
            receipt_proc = run(root, "evidence", "--id", "WU-LIFECYCLE", "--claim", "EV1", "--type", "test", "--result", "pass", "--command", "true", "--command-log-ref", ".harness/work-units/active/WU-LIFECYCLE/evidence/artifacts/test.log")
            receipt_id = json.loads(receipt_proc.stdout)["receipt_id"]
            run(root, "submit-review", "--id", "WU-LIFECYCLE", "--mode", "close", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context", "--evidence-ref", receipt_id)

            subprocess.run(["git", "add", "src/app.py"], cwd=root, check=True, timeout=10)
            subprocess.run(["git", "commit", "-m", "feat: implement work unit"], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=10)
            proc = run(root, "check", "--id", "WU-LIFECYCLE", "--gate", "verification", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)
            self.assertIn('"status": "equivalent_pass"', proc.stdout)
            proc = run(root, "check", "--id", "WU-LIFECYCLE", "--gate", "review", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)

            run(root, "handoff", "--id", "WU-LIFECYCLE", "--next-safe-action", "Archive after merge.")
            subprocess.run(["git", "add", "-f", ".harness/work-units/active/WU-LIFECYCLE"], cwd=root, check=True, timeout=10)
            subprocess.run(["git", "commit", "-m", "chore: record work unit handoff"], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=10)

            proc = run(root, "check", "--id", "WU-LIFECYCLE", "--gate", "verification", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)
            self.assertIn('"status": "equivalent_pass"', proc.stdout)
            proc = run(root, "check", "--id", "WU-LIFECYCLE", "--gate", "review", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)

            hook = root / "harness" / "hooks" / "stop_without_evidence.py"
            proc = subprocess.run([sys.executable, str(hook)], cwd=root, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            self.assertEqual(proc.stdout, "")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_validate_gate_checks_artifact_shape_and_cross_refs(self):
        root = make_repo()
        try:
            run(root, "init")
            proc = run(root, "validate", "--all", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)

            run(root, "new", "--id", "WU-VALID", "--title", "Validate", "--type", "bugfix", "--risk", "medium")
            set_required_evidence(root, "WU-VALID", ["EV1"])
            receipt_proc = run(root, "evidence", "--id", "WU-VALID", "--claim", "EV1", "--type", "test", "--result", "pass", "--command", "true", "--command-log-ref", ".harness/work-units/active/WU-VALID/evidence/artifacts/test.log")
            receipt_id = json.loads(receipt_proc.stdout)["receipt_id"]
            run(root, "waiver", "--id", "WU-VALID", "--approved-by", "human:owner@example.com", "--requirement", "EV2", "--reason", "Cannot run", "--replacement-evidence", "Manual", "--risk-accepted", "Temporary")
            run(root, "submit-review", "--id", "WU-VALID", "--mode", "close", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context", "--evidence-ref", receipt_id)
            proc = run(root, "validate", "--id", "WU-VALID", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)

            wu_path = root / ".harness" / "work-units" / "active" / "WU-VALID"
            state_path = wu_path / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["status"] = "impossible"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            proc = run(root, "validate", "--id", "WU-VALID", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("state.json: status must be one of", proc.stdout)

            state["status"] = "draft"
            state_path.write_text(json.dumps(state), encoding="utf-8")
            receipts = wu_path / "evidence" / "receipts.jsonl"
            receipts.write_text(receipts.read_text(encoding="utf-8") + "{broken json\n", encoding="utf-8")
            proc = run(root, "validate", "--id", "WU-VALID", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("receipts.jsonl", proc.stdout)

            lines = receipts.read_text(encoding="utf-8").splitlines()
            receipts.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
            verdict = next((wu_path / "reviews").glob("verdict-*.json"))
            obj = json.loads(verdict.read_text(encoding="utf-8"))
            obj["evidence_refs"] = ["ev-does-not-exist"]
            verdict.write_text(json.dumps(obj), encoding="utf-8")
            proc = run(root, "validate", "--id", "WU-VALID", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("references missing evidence receipt ev-does-not-exist", proc.stdout)

            obj["evidence_refs"] = [receipt_id]
            verdict.write_text(json.dumps(obj), encoding="utf-8")
            waiver = next((wu_path / "waivers").glob("waiver-*.json"))
            waiver_obj = json.loads(waiver.read_text(encoding="utf-8"))
            waiver_obj["approved_by"] = "agent"
            waiver.write_text(json.dumps(waiver_obj), encoding="utf-8")
            proc = run(root, "validate", "--id", "WU-VALID", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("approved_by must start with human:", proc.stdout)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_ci_gate_runs_lifecycle_checks_for_changed_active_work_unit(self):
        root = make_repo()
        try:
            run(root, "init")
            proc = run(root, "ci", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)
            subprocess.run(["git", "add", ".gitignore"], cwd=root, check=True, timeout=10)
            subprocess.run(["git", "commit", "-m", "test: ignore harness runtime state"], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=10)

            proc = run(root, "ci", "--strict", "--require-active", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("requires at least one active Work Unit", proc.stdout)

            run(root, "new", "--id", "WU-CI", "--title", "CI", "--type", "bugfix", "--risk", "medium")
            fill_contract(root, "WU-CI")
            run(root, "lock", "--id", "WU-CI", "--status", "ready")
            run(root, "submit-review", "--id", "WU-CI", "--mode", "plan", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context")
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("value = 1\n", encoding="utf-8")

            proc = run(root, "ci", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("WU-CI verification: Missing fresh pass evidence for required claim EV1", proc.stdout)
            self.assertIn("WU-CI review: medium risk requires a passing close review verdict", proc.stdout)

            receipt_proc = run(root, "evidence", "--id", "WU-CI", "--claim", "EV1", "--type", "test", "--result", "pass", "--command", "true", "--command-log-ref", ".harness/work-units/active/WU-CI/evidence/artifacts/test.log")
            receipt_id = json.loads(receipt_proc.stdout)["receipt_id"]
            proc = run(root, "ci", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("WU-CI review: medium risk requires a passing close review verdict", proc.stdout)

            run(root, "submit-review", "--id", "WU-CI", "--mode", "close", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context", "--evidence-ref", receipt_id)
            proc = run(root, "ci", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_spec_gate_blocks_unconfirmed_clarification_record(self):
        root = make_repo()
        try:
            run(root, "init")
            run(root, "new", "--id", "WU-CLARIFY", "--title", "Clarify", "--type", "bugfix", "--risk", "medium")
            fill_contract(root, "WU-CLARIFY")
            contract = root / ".harness" / "work-units" / "active" / "WU-CLARIFY" / "contract.md"
            contract.write_text(contract.read_text(encoding="utf-8").replace("user_confirmed: yes", "user_confirmed: no"), encoding="utf-8")
            proc = run(root, "check", "--id", "WU-CLARIFY", "--gate", "spec", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("user_confirmed", proc.stdout)

            contract.write_text(contract.read_text(encoding="utf-8").replace("user_confirmed: no", "user_confirmed: yes").replace("project_reality_confidence: 95", "project_reality_confidence: 90"), encoding="utf-8")
            proc = run(root, "check", "--id", "WU-CLARIFY", "--gate", "spec", "--strict")
            self.assertEqual(proc.returncode, 0)
            self.assertIn('"decision": "WARN"', proc.stdout)
            self.assertIn("project_reality_confidence", proc.stdout)

            contract.write_text(contract.read_text(encoding="utf-8").replace("project_reality_confidence: 90", "project_reality_confidence: 95"), encoding="utf-8")
            proc = run(root, "check", "--id", "WU-CLARIFY", "--gate", "spec", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_spec_gate_accepts_nested_list_contract_fields(self):
        root = make_repo()
        try:
            run(root, "init")
            run(root, "new", "--id", "WU-NESTED", "--title", "Nested", "--type", "bugfix", "--risk", "medium")
            fill_contract(root, "WU-NESTED")
            contract = root / ".harness" / "work-units" / "active" / "WU-NESTED" / "contract.md"
            text = contract.read_text(encoding="utf-8")
            text = text.replace(
                """## Required evidence

- id: EV1
  claim: Targeted test passes.
  command: python3 -m unittest
  required_for_completion: true
""",
                """## Required evidence

- id: EV1
  claim:
    - Targeted test passes.
  command:
    - python3 -m unittest
  required_for_completion: true
""",
            )
            text = text.replace(
                """## Clarification record

- user_confirmed: yes
- repo_grounded: yes
- user_intent_confidence: 95
- project_reality_confidence: 95
- key_decisions: Test behavior and evidence surface are confirmed.
- remaining_assumptions: none
""",
                """## Clarification record

- user_confirmed:
  - yes
- repo_grounded:
  - yes
- user_intent_confidence:
  - 95
- project_reality_confidence:
  - 95
- key_decisions:
  - Test behavior and evidence surface are confirmed.
- remaining_assumptions:
  - none
""",
            )
            contract.write_text(text, encoding="utf-8")

            proc = run(root, "check", "--id", "WU-NESTED", "--gate", "spec", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)
            items = harnessctl.required_evidence_items(root / ".harness" / "work-units" / "active" / "WU-NESTED")
            self.assertEqual(items[0]["claim"], "Targeted test passes.")
            self.assertEqual(items[0]["command"], "python3 -m unittest")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_spec_gate_accepts_natural_language_clarification_record(self):
        root = make_repo()
        try:
            run(root, "init")
            run(root, "new", "--id", "WU-CLARIFY-NL", "--title", "Clarify Natural", "--type", "bugfix", "--risk", "medium")
            fill_contract(root, "WU-CLARIFY-NL")
            contract = root / ".harness" / "work-units" / "active" / "WU-CLARIFY-NL" / "contract.md"
            text = contract.read_text(encoding="utf-8")
            text = text.replace("## Clarification record", "## Clarification Record")
            text = text.replace("- user_confirmed: yes", "- user_confirmed: yes, 2026-06-01: user confirmed the bounded behavior.")
            text = text.replace("- repo_grounded: yes", "- repo_grounded: yes, inspected current tests and source paths.")
            text = text.replace("- remaining_assumptions: none", "- remaining_assumptions: none; current repo conventions are sufficient.")
            contract.write_text(text, encoding="utf-8")

            proc = run(root, "check", "--id", "WU-CLARIFY-NL", "--gate", "spec", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_spec_gate_lock_and_running_require_ready_contract(self):
        root = make_repo()
        try:
            run(root, "init")
            run(root, "new", "--id", "WU-ALIGN", "--title", "Align", "--type", "bugfix", "--risk", "medium")

            proc = run(root, "check", "--id", "WU-ALIGN", "--gate", "spec", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("TBD/TODO", proc.stdout)

            proc = run(root, "lock", "--id", "WU-ALIGN", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("Cannot lock", proc.stderr)

            fill_contract(root, "WU-ALIGN")
            contract = root / ".harness" / "work-units" / "active" / "WU-ALIGN" / "contract.md"
            contract.write_text(contract.read_text(encoding="utf-8").replace('risk: "medium"\n', 'risk: "medium"\nstatus: "draft"\n'), encoding="utf-8")
            proc = run(root, "check", "--id", "WU-ALIGN", "--gate", "spec", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("state.json is the lifecycle authority", proc.stdout)
            contract.write_text(contract.read_text(encoding="utf-8").replace('status: "draft"\n', ''), encoding="utf-8")
            proc = run(root, "check", "--id", "WU-ALIGN", "--gate", "spec", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)

            proc = run(root, "set-state", "--id", "WU-ALIGN", "--status", "running", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("not locked", proc.stderr)

            run(root, "lock", "--id", "WU-ALIGN", "--status", "ready")
            proc = run(root, "set-state", "--id", "WU-ALIGN", "--status", "running", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("Plan review gate blocks running", proc.stderr)

            run(root, "submit-review", "--id", "WU-ALIGN", "--mode", "plan", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context")
            proc = run(root, "check", "--id", "WU-ALIGN", "--gate", "plan-review", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)
            proc = run(root, "set-state", "--id", "WU-ALIGN", "--status", "running")
            self.assertIn('"status": "running"', proc.stdout)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_locked_contract_change_requires_amendment_before_running(self):
        root = make_repo()
        try:
            run(root, "init")
            run(root, "new", "--id", "WU-AMEND", "--title", "Amend", "--type", "bugfix", "--risk", "medium")
            fill_contract(root, "WU-AMEND")
            run(root, "lock", "--id", "WU-AMEND", "--status", "ready")
            run(root, "submit-review", "--id", "WU-AMEND", "--mode", "plan", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context")

            contract = root / ".harness" / "work-units" / "active" / "WU-AMEND" / "contract.md"
            contract.write_text(contract.read_text(encoding="utf-8").replace("Observable behavior is corrected.", "Observable behavior and regression coverage are corrected."), encoding="utf-8")
            proc = run(root, "set-state", "--id", "WU-AMEND", "--status", "running", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("changed after lock", proc.stderr)

            run(root, "amend", "--id", "WU-AMEND", "--field", "success", "--reason", "Clarified expected outcome", "--summary", "Expected outcome now mentions regression coverage", "--actor", "human")
            run(root, "lock", "--id", "WU-AMEND", "--status", "ready")
            proc = run(root, "set-state", "--id", "WU-AMEND", "--status", "running", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("older contract", proc.stderr)

            run(root, "submit-review", "--id", "WU-AMEND", "--mode", "plan", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context")
            proc = run(root, "set-state", "--id", "WU-AMEND", "--status", "running")
            self.assertIn('"status": "running"', proc.stdout)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_no_impact_amendment_does_not_force_plan_rereview(self):
        root = make_repo()
        try:
            run(root, "init")
            run(root, "new", "--id", "WU-AMEND-NO-IMPACT", "--title", "Amend No Impact", "--type", "bugfix", "--risk", "medium")
            fill_contract(root, "WU-AMEND-NO-IMPACT")
            run(root, "lock", "--id", "WU-AMEND-NO-IMPACT", "--status", "ready")
            run(root, "submit-review", "--id", "WU-AMEND-NO-IMPACT", "--mode", "plan", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context")

            contract = root / ".harness" / "work-units" / "active" / "WU-AMEND-NO-IMPACT" / "contract.md"
            contract.write_text(contract.read_text(encoding="utf-8").replace("contract.md\n- src/**", "contract.md\n- README.md\n- src/**"), encoding="utf-8")
            run(root, "amend", "--id", "WU-AMEND-NO-IMPACT", "--field", "context", "--reason", "Added context pointer", "--summary", "Added README context pointer; no plan, scope, evidence, risk, success, or intent change", "--actor", "human", "--review-impact", "none")
            run(root, "lock", "--id", "WU-AMEND-NO-IMPACT", "--status", "ready")
            proc = run(root, "check", "--id", "WU-AMEND-NO-IMPACT", "--gate", "plan-review", "--strict")
            self.assertIn('"decision": "WARN"', proc.stdout)
            self.assertIn("declares no plan/review impact", proc.stdout)
            proc = run(root, "set-state", "--id", "WU-AMEND-NO-IMPACT", "--status", "running")
            self.assertIn('"status": "running"', proc.stdout)

            contract.write_text(contract.read_text(encoding="utf-8").replace("Observable behavior is corrected.", "Observable behavior and regression coverage are corrected."), encoding="utf-8")
            proc = run(root, "amend", "--id", "WU-AMEND-NO-IMPACT", "--field", "success", "--reason", "Changed success criteria", "--summary", "Success criteria now includes regression coverage", "--actor", "human", "--review-impact", "none", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("only allowed for context-only amendments", proc.stderr)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_collaboration_amendment_uses_publication_review_without_full_plan_rerun(self):
        root = make_repo()
        try:
            run(root, "init")
            run(root, "new", "--id", "WU-PUB", "--title", "Publication", "--type", "bugfix", "--risk", "medium")
            fill_contract(root, "WU-PUB")
            run(root, "lock", "--id", "WU-PUB", "--status", "ready")
            run(root, "submit-review", "--id", "WU-PUB", "--mode", "plan", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context")

            (root / "src").mkdir(exist_ok=True)
            (root / "src" / "feature.py").write_text("value = 1\n", encoding="utf-8")
            ev1 = json.loads(run(root, "evidence", "--id", "WU-PUB", "--claim", "EV1", "--type", "test", "--result", "pass", "--command", "true", "--command-log-ref", ".harness/work-units/active/WU-PUB/evidence/artifacts/ev1.log").stdout)["receipt_id"]
            run(root, "submit-review", "--id", "WU-PUB", "--mode", "close", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context", "--evidence-ref", ev1)

            set_required_evidence(root, "WU-PUB", ["EV1", "EV7"])
            run(root, "amend", "--id", "WU-PUB", "--field", "required_evidence", "--impact", "collaboration_only", "--reason", "Add GitHub collaboration", "--summary", "Add GitHub issue evidence without implementation changes", "--actor", "human")
            run(root, "lock", "--id", "WU-PUB", "--status", "ready")
            proc = run(root, "check", "--id", "WU-PUB", "--gate", "plan-review", "--strict")
            self.assertIn('"decision": "WARN"', proc.stdout)
            self.assertIn("plan re-review is not required", proc.stdout)

            proc = run(root, "check", "--id", "WU-PUB", "--gate", "review", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("EV7", proc.stdout)

            ev7 = json.loads(run(root, "evidence", "--id", "WU-PUB", "--claim", "EV7", "--type", "manual", "--result", "pass", "--command", "gh issue view 7 --json number,title,state,url,body", "--artifact-uri", "https://github.com/example/repo/issues/7").stdout)["receipt_id"]
            run(root, "submit-review", "--id", "WU-PUB", "--mode", "publication", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context", "--evidence-ref", ev7)
            proc = run(root, "check", "--id", "WU-PUB", "--gate", "review", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)

            # Refreshing existing implementation evidence after publication must not force
            # another reviewer/addendum run when implementation/scope/risk did not change.
            ev1_refreshed = json.loads(run(root, "evidence", "--id", "WU-PUB", "--claim", "EV1", "--type", "test", "--result", "pass", "--command", "true", "--command-log-ref", ".harness/work-units/active/WU-PUB/evidence/artifacts/ev1-refreshed.log").stdout)["receipt_id"]
            self.assertNotEqual(ev1, ev1_refreshed)
            proc = run(root, "check", "--id", "WU-PUB", "--gate", "verification", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)
            proc = run(root, "check", "--id", "WU-PUB", "--gate", "review", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)
            self.assertNotIn("does not cite latest fresh receipt", proc.stdout)
            self.assertNotIn("cites earlier receipt", proc.stdout)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_commit_and_receipt_refresh_do_not_require_close_addendum(self):
        root = make_repo()
        try:
            run(root, "init")
            run(root, "new", "--id", "WU-NO-ADDENDUM", "--title", "No Addendum", "--type", "bugfix", "--risk", "medium")
            fill_contract(root, "WU-NO-ADDENDUM")
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("value = 1\n", encoding="utf-8")
            ev1 = json.loads(run(root, "evidence", "--id", "WU-NO-ADDENDUM", "--claim", "EV1", "--type", "test", "--result", "pass", "--command", "true", "--command-log-ref", ".harness/work-units/active/WU-NO-ADDENDUM/evidence/artifacts/ev1.log").stdout)["receipt_id"]
            run(root, "submit-review", "--id", "WU-NO-ADDENDUM", "--mode", "close", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context", "--evidence-ref", ev1)

            subprocess.run(["git", "add", "src/app.py"], cwd=root, check=True, timeout=10)
            subprocess.run(["git", "commit", "-m", "feat: materialize reviewed diff"], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=10)

            ev1_refreshed = json.loads(run(root, "evidence", "--id", "WU-NO-ADDENDUM", "--claim", "EV1", "--type", "test", "--result", "pass", "--command", "true", "--command-log-ref", ".harness/work-units/active/WU-NO-ADDENDUM/evidence/artifacts/ev1-r2.log").stdout)["receipt_id"]
            self.assertNotEqual(ev1, ev1_refreshed)

            proc = run(root, "check", "--id", "WU-NO-ADDENDUM", "--gate", "review", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)
            self.assertNotIn("verification owns freshness", proc.stdout)
            self.assertNotIn("does not cite latest fresh receipt", proc.stdout)

            proc = run(root, "request-review", "--id", "WU-NO-ADDENDUM", "--mode", "close-addendum", "--reviewer-role", "reviewer-agent", check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("Close-addendum is not required", proc.stderr)

            out = json.loads(run(root, "finalize-check", "--id", "WU-NO-ADDENDUM", "--strict").stdout)
            self.assertTrue(out["do_not_request_review"])
            self.assertIn(out["decision"], {"PASS", "WARN"})

            hook = root / "harness" / "hooks" / "stop_without_evidence.py"
            proc = subprocess.run([sys.executable, str(hook)], cwd=root, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            self.assertEqual(proc.stdout, "")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_verification_gate_outputs_per_claim_minimal_plan(self):
        root = make_repo()
        try:
            run(root, "init")
            run(root, "new", "--id", "WU-EV-PLAN", "--title", "Evidence Plan", "--type", "bugfix", "--risk", "low")
            set_required_evidence(root, "WU-EV-PLAN", ["EV1", "EV2"])
            run(root, "evidence", "--id", "WU-EV-PLAN", "--claim", "EV1", "--type", "test", "--result", "pass", "--command", "true")
            out = json.loads(run(root, "check", "--id", "WU-EV-PLAN", "--gate", "verification", "--strict", check=False).stdout)
            self.assertEqual(out["decision"], "BLOCK")
            statuses = {x["claim"]: x for x in out["evidence_status"]}
            self.assertEqual(statuses["EV1"]["status"], "satisfied")
            self.assertEqual(statuses["EV2"]["status"], "missing")
            self.assertTrue(statuses["EV2"]["requires_rerun"])
            self.assertIn("EV2", statuses["EV2"]["minimal_next_action"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_platform_adapter_layouts(self):
        codex_config = tomllib.loads((PROJECT_ROOT / ".codex" / "config.toml").read_text(encoding="utf-8"))
        self.assertNotIn("agent", codex_config)

        self.assertEqual(["reviewer.toml", "worker.toml"], sorted(p.name for p in (PROJECT_ROOT / ".codex" / "agents").glob("*.toml")))
        self.assertEqual(["reviewer.md", "worker.md"], sorted(p.name for p in (PROJECT_ROOT / ".claude" / "agents").glob("*.md")))

        for path in (PROJECT_ROOT / ".codex" / "agents").glob("*.toml"):
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            for key in ["name", "model", "description", "sandbox_mode", "model_reasoning_effort", "developer_instructions"]:
                self.assertIn(key, data, path.name)
            self.assertNotIn("instructions", data, path.name)

        canonical = sorted(p.name for p in (PROJECT_ROOT / "skills").glob("harness-*"))
        self.assertTrue(canonical)
        for base in [PROJECT_ROOT / ".agents" / "skills", PROJECT_ROOT / ".claude" / "skills"]:
            self.assertEqual(canonical, sorted(p.name for p in base.glob("harness-*")))
            for skill in canonical:
                text = (base / skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn("name:", text, skill)
                self.assertIn("description:", text, skill)

        proc = run(PROJECT_ROOT, "check", "--gate", "skills", "--strict")
        self.assertIn('"decision": "PASS"', proc.stdout)

    def test_adopt_profiles_copy_expected_layers(self):
        def adopt(profile):
            target = Path(tempfile.mkdtemp(prefix=f"harness-adopt-{profile}-"))
            proc = subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "adopt.py"), str(target), "--profile", profile], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=30)
            return target, proc

        targets = []
        try:
            thin, thin_proc = adopt("thin")
            targets.append(thin)
            self.assertIn("profile=thin", thin_proc.stdout)
            self.assertTrue((thin / "AGENTS.md").exists())
            self.assertTrue((thin / "CLAUDE.md").exists())
            agents_text = (thin / "AGENTS.md").read_text(encoding="utf-8")
            claude_text = (thin / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("Clarify Before Spec", agents_text)
            self.assertIn(".harness/config.json", agents_text)
            self.assertIn(".harness/current", agents_text)
            self.assertIn(".harness/config.json", claude_text)
            self.assertIn(".harness/current", claude_text)
            self.assertNotIn("portable coding-agent harness implementation", agents_text)
            self.assertTrue((thin / "docs" / "harness" / "README.md").exists())
            self.assertTrue((thin / "docs" / "harness" / "workflow.md").exists())
            self.assertTrue((thin / "docs" / "harness" / "risk-gates.md").exists())
            self.assertFalse((thin / "docs" / "harness" / "platform-adapters.md").exists())
            self.assertFalse((thin / "docs" / "harness" / "mechanism-registry.yaml").exists())
            self.assertFalse((thin / "docs" / "harness" / "evaluation").exists())
            self.assertFalse((thin / "docs" / "harness" / "adoption-guide.md").exists())
            self.assertFalse((thin / "docs" / "harness" / "source-analysis.md").exists())
            self.assertTrue((thin / "harness" / "cli" / "harnessctl.py").exists())
            self.assertTrue((thin / "skills" / "harness-clarify" / "SKILL.md").exists())
            self.assertTrue((thin / "skills" / "harness-review" / "SKILL.md").exists())
            self.assertTrue((thin / "skills" / "harness-github" / "SKILL.md").exists())
            self.assertFalse((thin / ".codex").exists())
            self.assertFalse((thin / ".claude").exists())

            controlled, _ = adopt("controlled")
            targets.append(controlled)
            self.assertTrue((controlled / "harness" / "tests" / "test_harnessctl.py").exists())
            self.assertTrue((controlled / ".github" / "workflows" / "harness-checks.yml").exists())
            self.assertFalse((controlled / "docs" / "harness" / "platform-adapters.md").exists())
            self.assertFalse((controlled / "docs" / "harness" / "mechanism-registry.yaml").exists())
            self.assertFalse((controlled / "docs" / "harness" / "evaluation").exists())
            self.assertFalse((controlled / "docs" / "harness" / "adoption-guide.md").exists())
            self.assertTrue((controlled / "skills" / "harness-review" / "SKILL.md").exists())
            self.assertTrue((controlled / "skills" / "harness-spec" / "SKILL.md").exists())
            self.assertFalse((controlled / ".codex").exists())
            self.assertFalse((controlled / ".claude").exists())

            codex, codex_proc = adopt("codex")
            targets.append(codex)
            self.assertIn("platform adapter", codex_proc.stdout)
            self.assertTrue((codex / ".codex" / "agents" / "worker.toml").exists())
            self.assertTrue((codex / ".agents" / "skills" / "harness-review" / "SKILL.md").exists())
            self.assertTrue((codex / "docs" / "harness" / "platform-adapters.md").exists())
            self.assertFalse((codex / ".claude").exists())

            claude, claude_proc = adopt("claude")
            targets.append(claude)
            self.assertIn("platform adapter", claude_proc.stdout)
            self.assertTrue((claude / ".claude" / "settings.json").exists())
            self.assertTrue((claude / ".claude" / "skills" / "harness-review" / "SKILL.md").exists())
            self.assertTrue((claude / "docs" / "harness" / "platform-adapters.md").exists())
            self.assertFalse((claude / ".codex").exists())

            full, _ = adopt("full")
            targets.append(full)
            self.assertTrue((full / ".codex" / "agents" / "worker.toml").exists())
            self.assertTrue((full / ".claude" / "settings.json").exists())
            self.assertTrue((full / "skills" / "harness-github" / "SKILL.md").exists())
            self.assertTrue((full / "examples").exists())
        finally:
            for target in targets:
                shutil.rmtree(target, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
