from __future__ import annotations

import contextlib
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from types import SimpleNamespace

from harness.cli import harnessctl

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_ctl(root: Path, *args: str, check: bool = True) -> SimpleNamespace:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = harnessctl.main(["--root", str(root), *args])
    result = SimpleNamespace(returncode=code, stdout=stdout.getvalue(), stderr=stderr.getvalue())
    if check and code != 0:
        raise AssertionError(f"command failed: {args}\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return proc.stdout.strip()


def make_repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="harness-v2-test-"))
    git(root, "init")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "user.name", "Harness Test")
    (root / "src").mkdir()
    (root / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "verify_behavior.py").write_text(
        "from pathlib import Path\n"
        "raise SystemExit(0 if 'VALUE = 2' in Path('src/app.py').read_text() else 7)\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("fixture\n", encoding="utf-8")
    shutil.copytree(PROJECT_ROOT / "harness", root / "harness", ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"))
    (root / ".gitignore").write_text(".harness/\n", encoding="utf-8")
    (root / "docs" / "spec").mkdir(parents=True, exist_ok=True)
    git(root, "add", ".")
    git(root, "commit", "-m", "fixture")
    return root


def valid_spec(wu_id: str, risk: str = "medium", command: str | None = None) -> str:
    command = command or shlex.join([sys.executable, "tests/verify_behavior.py"])
    return f'''# Feature Spec: {wu_id} — Test behavior

```yaml
id: "{wu_id}"
title: "Test behavior"
type: "bugfix"
risk: "{risk}"
```

## Intent

Correct one bounded behavior in the fixture.

## Expected Outcome

- The target behavior is observable and correct.

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
  claim: The targeted behavior passes.
  command: {command}

## Stop conditions

### Success

- EV1 passes after the implementation change.

### Blocked

- The implementation would need to modify secrets/**.

## Clarification record

- user_confirmed: yes
- repo_grounded: yes
- key_decisions: Keep the change inside src/** and verify EV1.
- remaining_assumptions: none

## Open questions

- none

## Context pointers

- src/app.py

## Delivery tracking

- issue: none
- branch: none
- pull_request: none

## Risk notes

- No material risk beyond the local behavior.
'''


def valid_plan(wu_id: str) -> str:
    return f'''# Technical Plan: {wu_id} — Test behavior

## Repository grounding

- Read src/app.py and the fixture validation path.

## Architecture and tradeoffs

Change the smallest implementation surface. A broader refactor was rejected because it adds no value.

## Change map

- src/app.py → update the bounded value → satisfy the approved behavior.

## TDD behavior slices

- id: B1
  claim_ref: EV1
  behavior: Target behavior is corrected.
  red_command: python3 -c "raise SystemExit(1)"
  expected_red_reason: The old behavior remains.
  green_command: python3 -c "raise SystemExit(0)"
  allowed_paths: src/**

## Verification

- Execute EV1 through harnessctl verify after the implementation change.

## Risks and replan conditions

- Stop if the write boundary must expand.

## Reviewer focus

- Recheck scope, evidence freshness, and that the implementation matches this plan.
'''


class HarnessV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = make_repo()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))

    def create_valid_wu(self, wu_id: str = "WU-1", risk: str = "medium") -> Path:
        run_ctl(self.root, "new", "--id", wu_id, "--title", "Test behavior", "--type", "bugfix", "--risk", risk)
        spec = self.root / "docs" / "spec" / f"{wu_id}.md"
        spec.write_text(valid_spec(wu_id, risk), encoding="utf-8")
        run_ctl(self.root, "approve-spec", "--id", wu_id, "--approved-by", "human:owner", "--approval-ref", "user-confirmation:test")
        wu = self.root / ".harness" / "work-units" / "active" / wu_id
        (wu / "plan.md").write_text(valid_plan(wu_id), encoding="utf-8")
        return wu

    def plan_approve(
        self,
        wu_id: str = "WU-1",
        reviewer: str = "reviewer-1",
        session: str = "review-session-plan",
        planner: str = "planner-1",
        planner_session: str = "planner-session",
    ) -> str:
        request = json.loads(
            run_ctl(
                self.root,
                "request-review",
                "--id",
                wu_id,
                "--mode",
                "plan",
                "--reviewer-id",
                reviewer,
                "--reviewer-session",
                session,
                "--planner-id",
                planner,
                "--planner-session",
                planner_session,
            ).stdout
        )
        run_ctl(self.root, "submit-review", "--id", wu_id, "--request-id", request["request_id"], "--mode", "plan", "--decision", "PASS", "--reviewer-id", reviewer, "--reviewer-session", session)
        return request["request_id"]

    def start_and_verify(self, wu_id: str = "WU-1") -> str:
        run_ctl(self.root, "start-work", "--id", wu_id, "--builder-id", "worker-1", "--builder-session", "worker-session")
        (self.root / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        receipt = json.loads(run_ctl(self.root, "verify", "--id", wu_id, "--claim", "EV1", "--phase", "final").stdout)
        return receipt["receipt_id"]

    def test_new_tracks_only_spec_and_ignores_runtime(self) -> None:
        run_ctl(self.root, "new", "--id", "WU-A", "--title", "A")
        self.assertTrue((self.root / "docs/spec/WU-A.md").exists())
        self.assertTrue((self.root / ".harness/work-units/active/WU-A/plan.md").exists())
        self.assertIn(".harness/", (self.root / ".gitignore").read_text(encoding="utf-8"))
        status = git(self.root, "status", "--short", "--untracked-files=all")
        self.assertIn("docs/spec/WU-A.md", status)
        self.assertNotIn(".harness/", status)

    def test_spec_cannot_be_approved_with_placeholders(self) -> None:
        run_ctl(self.root, "new", "--id", "WU-B", "--title", "B")
        proc = run_ctl(self.root, "approve-spec", "--id", "WU-B", "--approved-by", "human:owner", "--approval-ref", "user-confirmation:test", check=False)
        self.assertEqual(2, proc.returncode)
        self.assertIn("placeholder", proc.stderr.lower())

    def test_material_spec_change_invalidates_plan_approval(self) -> None:
        wu = self.create_valid_wu("WU-C")
        self.plan_approve("WU-C")
        spec = self.root / "docs/spec/WU-C.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace("Correct one bounded behavior", "Correct one materially changed behavior"), encoding="utf-8")
        run_ctl(self.root, "amend", "--id", "WU-C", "--reason", "Product intent changed", "--summary", "Changed target behavior", "--actor", "human:owner", "--approval-ref", "user-confirmation:amend")
        state = json.loads((wu / "state.json").read_text(encoding="utf-8"))
        self.assertEqual("spec_approved", state["status"])
        self.assertEqual("", state["plan_approved_hash"])

    def test_start_work_requires_passing_plan_review(self) -> None:
        self.create_valid_wu("WU-D")
        proc = run_ctl(self.root, "start-work", "--id", "WU-D", "--builder-id", "worker", check=False)
        self.assertEqual(2, proc.returncode)
        self.plan_approve("WU-D")
        run_ctl(self.root, "start-work", "--id", "WU-D", "--builder-id", "worker", "--builder-session", "s-worker")

    def test_worker_must_differ_from_plan_reviewer(self) -> None:
        self.create_valid_wu("WU-D2")
        self.plan_approve("WU-D2", reviewer="reviewer-A", session="review-session", planner="planner-A", planner_session="planner-session")
        same_identity = run_ctl(self.root, "start-work", "--id", "WU-D2", "--builder-id", "reviewer-A", "--builder-session", "worker-session", check=False)
        self.assertEqual(2, same_identity.returncode)
        same_session = run_ctl(self.root, "start-work", "--id", "WU-D2", "--builder-id", "worker-A", "--builder-session", "review-session", check=False)
        self.assertEqual(2, same_session.returncode)
        planner_identity = run_ctl(self.root, "start-work", "--id", "WU-D2", "--builder-id", "planner-A", "--builder-session", "worker-session", check=False)
        self.assertEqual(2, planner_identity.returncode)
        planner_session = run_ctl(self.root, "start-work", "--id", "WU-D2", "--builder-id", "worker-A", "--builder-session", "planner-session", check=False)
        self.assertEqual(2, planner_session.returncode)

    def test_plan_reviewer_must_differ_from_planner(self) -> None:
        self.create_valid_wu("WU-D3")
        same_identity = run_ctl(
            self.root,
            "request-review",
            "--id",
            "WU-D3",
            "--mode",
            "plan",
            "--reviewer-id",
            "planner-A",
            "--reviewer-session",
            "review-session",
            "--planner-id",
            "planner-A",
            "--planner-session",
            "planner-session",
            check=False,
        )
        self.assertEqual(2, same_identity.returncode)
        same_session = run_ctl(
            self.root,
            "request-review",
            "--id",
            "WU-D3",
            "--mode",
            "plan",
            "--reviewer-id",
            "reviewer-A",
            "--reviewer-session",
            "shared-session",
            "--planner-id",
            "planner-A",
            "--planner-session",
            "shared-session",
            check=False,
        )
        self.assertEqual(2, same_session.returncode)

    def test_verify_executes_command_and_derives_result(self) -> None:
        self.create_valid_wu("WU-E")
        self.plan_approve("WU-E")
        run_ctl(self.root, "start-work", "--id", "WU-E", "--builder-id", "worker", "--builder-session", "s-worker")
        bad = run_ctl(self.root, "verify", "--id", "WU-E", "--claim", "EV1", "--phase", "final", check=False)
        self.assertEqual(2, bad.returncode)
        receipt = json.loads(bad.stdout)
        self.assertEqual("fail", receipt["result"])
        self.assertEqual(7, receipt["exit_code"])
        self.assertTrue((self.root / receipt["command_log_ref"]).exists())
        self.assertTrue(receipt["command_log_hash"])
        (self.root / "src/app.py").write_text("VALUE = 2\n", encoding="utf-8")
        good = json.loads(run_ctl(self.root, "verify", "--id", "WU-E", "--claim", "EV1", "--phase", "final").stdout)
        self.assertEqual("pass", good["result"])
        self.assertEqual("controller_executed_command", good["observation"])

    def test_final_verification_rejects_command_not_in_spec(self) -> None:
        self.create_valid_wu("WU-E2")
        self.plan_approve("WU-E2")
        run_ctl(self.root, "start-work", "--id", "WU-E2", "--builder-id", "worker", "--builder-session", "s-worker")
        proc = run_ctl(
            self.root, "verify", "--id", "WU-E2", "--claim", "EV1", "--phase", "final",
            "--", sys.executable, "-c", "raise SystemExit(0)", check=False
        )
        self.assertEqual(2, proc.returncode)
        self.assertIn("exactly match", proc.stderr)

    def test_tdd_red_accepts_expected_nonzero_only(self) -> None:
        self.create_valid_wu("WU-F")
        self.plan_approve("WU-F")
        run_ctl(self.root, "start-work", "--id", "WU-F", "--builder-id", "worker", "--builder-session", "s-worker")
        red = json.loads(run_ctl(self.root, "verify", "--id", "WU-F", "--claim", "EV1", "--phase", "red", "--expect", "fail", "--", sys.executable, "-c", "raise SystemExit(1)").stdout)
        self.assertEqual("pass", red["result"])
        gate = run_ctl(self.root, "check", "--id", "WU-F", "--gate", "verification", "--strict", check=False)
        self.assertEqual(2, gate.returncode)
        self.assertIn("missing", gate.stdout.lower())
        wrong = run_ctl(self.root, "verify", "--id", "WU-F", "--claim", "EV1", "--phase", "red", "--expect", "fail", "--", sys.executable, "-c", "raise SystemExit(0)", check=False)
        self.assertEqual(2, wrong.returncode)

    def test_evidence_becomes_stale_after_implementation_change(self) -> None:
        self.create_valid_wu("WU-G")
        self.plan_approve("WU-G")
        self.start_and_verify("WU-G")
        self.assertEqual(0, run_ctl(self.root, "check", "--id", "WU-G", "--gate", "verification", "--strict").returncode)
        (self.root / "src/app.py").write_text("VALUE = 3\n", encoding="utf-8")
        stale = run_ctl(self.root, "check", "--id", "WU-G", "--gate", "verification", "--strict", check=False)
        self.assertEqual(2, stale.returncode)
        self.assertIn("stale", stale.stdout.lower())

    def test_skipped_evidence_blocks_without_waiver(self) -> None:
        self.create_valid_wu("WU-H")
        self.plan_approve("WU-H")
        run_ctl(self.root, "start-work", "--id", "WU-H", "--builder-id", "worker", "--builder-session", "s-worker")
        run_ctl(self.root, "record-skipped", "--id", "WU-H", "--claim", "EV1", "--reason", "Tool unavailable", "--replacement", "none", "--risk-impact", "unknown", "--owner", "human:owner")
        state = json.loads((self.root / ".harness/work-units/active/WU-H/state.json").read_text(encoding="utf-8"))
        self.assertEqual("blocked", state["status"])
        self.assertNotIn("waiver", harnessctl.build_parser().format_help().lower())

    def test_close_review_reuses_plan_reviewer_track(self) -> None:
        wu = self.create_valid_wu("WU-I")
        self.plan_approve("WU-I", reviewer="reviewer-A")
        receipt_id = self.start_and_verify("WU-I")
        wrong = run_ctl(self.root, "request-review", "--id", "WU-I", "--mode", "close", "--reviewer-id", "reviewer-B", "--reviewer-session", "review-close", check=False)
        self.assertEqual(2, wrong.returncode)
        request = json.loads(run_ctl(self.root, "request-review", "--id", "WU-I", "--mode", "close", "--reviewer-id", "reviewer-A", "--reviewer-session", "review-close").stdout)
        run_ctl(self.root, "submit-review", "--id", "WU-I", "--request-id", request["request_id"], "--mode", "close", "--decision", "PASS", "--reviewer-id", "reviewer-A", "--reviewer-session", "review-close", "--evidence-ref", receipt_id)
        result = json.loads(run_ctl(self.root, "finalize-check", "--id", "WU-I", "--strict").stdout)
        self.assertIn(result["decision"], {"PASS", "WARN"})
        track = json.loads((wu / "reviews/track.json").read_text(encoding="utf-8"))
        self.assertEqual("reviewer-A", track["reviewer_id"])
        self.assertTrue(track.get("plan_review_id"))
        self.assertTrue(track.get("close_review_id"))

    def test_builder_cannot_submit_close_review(self) -> None:
        self.create_valid_wu("WU-J")
        self.plan_approve("WU-J", reviewer="reviewer-A")
        receipt_id = self.start_and_verify("WU-J")
        request = json.loads(run_ctl(self.root, "request-review", "--id", "WU-J", "--mode", "close", "--reviewer-id", "reviewer-A", "--reviewer-session", "review-close").stdout)
        # The review track is still reviewer-A; trying to impersonate the worker is rejected.
        proc = run_ctl(self.root, "submit-review", "--id", "WU-J", "--request-id", request["request_id"], "--mode", "close", "--decision", "PASS", "--reviewer-id", "worker-1", "--reviewer-session", "worker-session", "--evidence-ref", receipt_id, check=False)
        self.assertEqual(2, proc.returncode)

    def test_resume_rebuilds_local_runtime_from_tracked_spec(self) -> None:
        self.create_valid_wu("WU-K")
        shutil.rmtree(self.root / ".harness")
        run_ctl(self.root, "resume", "--id", "WU-K")
        state = json.loads((self.root / ".harness/work-units/active/WU-K/state.json").read_text(encoding="utf-8"))
        self.assertEqual("spec_approved", state["status"])
        self.assertEqual([], state["latest_evidence_refs"])
        self.assertTrue((self.root / ".harness/work-units/active/WU-K/plan.md").exists())
        self.assertEqual(0, run_ctl(self.root, "check", "--id", "WU-K", "--gate", "spec", "--strict").returncode)

    def test_phase_policy_blocks_product_write_during_clarification(self) -> None:
        run_ctl(self.root, "new", "--id", "WU-L", "--title", "L")
        sys.path.insert(0, str(self.root / "harness/hooks"))
        try:
            import policy_common  # type: ignore
            decision, _ = policy_common.phase_write_policy(self.root, {"tool_name": "Write", "tool_input": {"file_path": "src/app.py"}})
            self.assertEqual("deny", decision)
            allowed, _ = policy_common.phase_write_policy(self.root, {"tool_name": "Write", "tool_input": {"file_path": "docs/spec/WU-L.md"}})
            self.assertEqual("allow", allowed)
        finally:
            sys.path.pop(0)
            sys.modules.pop("policy_common", None)

    def test_phase_policy_parses_apply_patch_and_blocks_shell_mutation(self) -> None:
        run_ctl(self.root, "new", "--id", "WU-L2", "--title", "L2")
        sys.path.insert(0, str(self.root / "harness/hooks"))
        try:
            import policy_common  # type: ignore
            patch_event = {"tool_name": "apply_patch", "tool_input": {"command": "*** Begin Patch\n*** Update File: src/app.py\n*** End Patch"}}
            decision, _ = policy_common.phase_write_policy(self.root, patch_event)
            self.assertEqual("deny", decision)
            shell_event = {"tool_name": "Bash", "tool_input": {"command": "printf x > src/app.py"}}
            shell_decision, _ = policy_common.phase_command_policy(self.root, shell_event)
            self.assertEqual("deny", shell_decision)
        finally:
            sys.path.pop(0)
            sys.modules.pop("policy_common", None)

    def test_workspace_current_pointer_is_namespaced(self) -> None:
        with mock.patch.dict(os.environ, {"HARNESS_SESSION_ID": "session-a"}, clear=False):
            run_ctl(self.root, "new", "--id", "WU-M", "--title", "M")
            pointer_a = harnessctl.current_file(self.root)
        with mock.patch.dict(os.environ, {"HARNESS_SESSION_ID": "session-b"}, clear=False):
            pointer_b = harnessctl.current_file(self.root)
        self.assertIn(".harness/runtime/", pointer_a.as_posix())
        self.assertNotEqual(pointer_a, pointer_b)
        self.assertEqual("WU-M", pointer_a.read_text(encoding="utf-8").strip())
        self.assertFalse(pointer_b.exists())

    def test_tampered_tracked_spec_recovers_to_clarification(self) -> None:
        self.create_valid_wu("WU-M2")
        spec = self.root / "docs/spec/WU-M2.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace("Correct one bounded behavior", "Unapproved changed behavior"), encoding="utf-8")
        shutil.rmtree(self.root / ".harness")
        result = json.loads(run_ctl(self.root, "resume", "--id", "WU-M2").stdout)
        self.assertEqual("clarifying", result["status"])
        state = json.loads((self.root / ".harness/work-units/active/WU-M2/state.json").read_text(encoding="utf-8"))
        self.assertEqual("clarifying", state["status"])
        ci = run_ctl(self.root, "ci", "--strict", check=False)
        self.assertEqual(2, ci.returncode)
        self.assertIn("approval", ci.stdout.lower())

    def test_handoff_resumes_only_through_checked_worker_path(self) -> None:
        self.create_valid_wu("WU-M3")
        self.plan_approve("WU-M3", reviewer="reviewer-A", session="review-plan")
        run_ctl(self.root, "start-work", "--id", "WU-M3", "--builder-id", "worker-A", "--builder-session", "worker-old")
        run_ctl(self.root, "handoff", "--id", "WU-M3", "--next-safe-action", "Continue implementation in a fresh worker session.")
        parser_help = harnessctl.build_parser().format_help()
        self.assertNotIn("set-state", parser_help)
        self.assertIn("resume-work", parser_help)
        run_ctl(self.root, "resume-work", "--id", "WU-M3", "--builder-id", "worker-A", "--builder-session", "worker-new")
        state = json.loads((self.root / ".harness/work-units/active/WU-M3/state.json").read_text(encoding="utf-8"))
        self.assertEqual("running", state["status"])
        self.assertEqual("worker-new", state["builder_session_id"])

    def test_skill_and_hook_layout_is_consistent(self) -> None:
        result = run_ctl(PROJECT_ROOT, "check", "--gate", "skills", "--strict")
        self.assertEqual(0, result.returncode)
        codex = json.loads((PROJECT_ROOT / ".codex/hooks.json").read_text(encoding="utf-8"))["hooks"]
        claude = json.loads((PROJECT_ROOT / ".claude/settings.json").read_text(encoding="utf-8"))["hooks"]
        for hooks in (codex, claude):
            self.assertIn("PreCompact", hooks)
            self.assertIn("PostCompact", hooks)
            self.assertIn("Stop", hooks)
            self.assertNotIn("SessionStart", hooks)
            self.assertNotIn("PreToolUse", hooks)
            self.assertNotIn("SubagentStart", hooks)
            self.assertNotIn("UserPromptSubmit", hooks)
            self.assertNotIn("PostToolBatch", hooks)
            self.assertNotIn("TaskCompleted", hooks)
        self.assertNotIn("PermissionRequest", codex)

    def test_adoption_installs_current_skill_layout_and_tracks_assets(self) -> None:
        target = Path(tempfile.mkdtemp(prefix="harness-adopt-test-"))
        self.addCleanup(lambda: shutil.rmtree(target, ignore_errors=True))
        git(target, "init")
        (target / "README.md").write_text("target\n", encoding="utf-8")
        proc = subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts/adopt.py"), "install", str(target), "--profile", "codex", "--no-doctor"], cwd=PROJECT_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertTrue((target / ".agents/skills/harness-clarify/SKILL.md").exists())
        self.assertFalse((target / ".codex/skills").exists())
        self.assertTrue((target / "docs/spec/README.md").exists())
        self.assertEqual([".harness/"], [line for line in (target / ".gitignore").read_text(encoding="utf-8").splitlines() if line])
        self.assertIn("only .harness runtime is ignored", proc.stdout)

        claude_target = Path(tempfile.mkdtemp(prefix="harness-adopt-claude-test-"))
        self.addCleanup(lambda: shutil.rmtree(claude_target, ignore_errors=True))
        git(claude_target, "init")
        (claude_target / "README.md").write_text("target\n", encoding="utf-8")
        subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts/adopt.py"), "install", str(claude_target), "--profile", "claude", "--no-doctor"], cwd=PROJECT_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertTrue((claude_target / ".claude/skills/harness-clarify/SKILL.md").exists())
        self.assertTrue((claude_target / ".claude/settings.json").exists())
        self.assertFalse((claude_target / ".agents").exists())
        self.assertEqual([".harness/"], [line for line in (claude_target / ".gitignore").read_text(encoding="utf-8").splitlines() if line])


if __name__ == "__main__":
    unittest.main()
