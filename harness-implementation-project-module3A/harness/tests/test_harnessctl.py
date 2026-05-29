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
            self.assertNotIn("hookSpecificOutput", out)

            run(root, "new", "--id", "WU-STOP-REVIEW", "--title", "Stop Review", "--type", "bugfix", "--risk", "medium")
            fill_contract(root, "WU-STOP-REVIEW")
            (root / "src").mkdir(exist_ok=True)
            (root / "src" / "stop_review.py").write_text("value = 1\n", encoding="utf-8")
            run(root, "evidence", "--id", "WU-STOP-REVIEW", "--claim", "EV1", "--type", "test", "--result", "pass", "--command", "true", "--command-log-ref", ".harness/work-units/active/WU-STOP-REVIEW/evidence/artifacts/test.log")
            proc = subprocess.run([sys.executable, str(hook)], cwd=root, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
            out = json.loads(proc.stdout)
            self.assertEqual(out["decision"], "block")
            self.assertIn("close review gate", out["reason"])

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
            self.assertIn("must cite fresh evidence receipt IDs", proc.stdout)

            run(root, "submit-review", "--id", "WU-REVIEW", "--mode", "close", "--decision", "PASS", "--reviewer-role", "reviewer-agent", "--builder-role", "agent", "--independence-level", "fresh_context", "--evidence-ref", receipt_id)
            proc = run(root, "check", "--id", "WU-REVIEW", "--gate", "review", "--strict")
            self.assertIn('"decision": "PASS"', proc.stdout)
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
            proc = run(root, "check", "--id", "WU-CLARIFY", "--gate", "spec", "--strict", check=False)
            self.assertEqual(proc.returncode, 2)
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
