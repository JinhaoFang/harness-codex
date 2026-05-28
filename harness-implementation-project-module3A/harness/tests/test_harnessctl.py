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
status: "draft"
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

            with self.assertRaises(harnessctl.HarnessError) as ctx:
                harnessctl.submit_review(argparse.Namespace(
                    root=root, id="WU-2", request_id=None, mode="close", decision="PASS",
                    reviewer_role="agent", builder_role="agent", independence_level="fresh_context",
                    evidence_ref=None, finding=None, required_rework=None,
                ))
            self.assertIn("builder", str(ctx.exception).lower())
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


if __name__ == "__main__":
    unittest.main()
