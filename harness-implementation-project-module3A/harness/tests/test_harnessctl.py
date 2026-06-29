from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from harness.cli import harnessctl
from harness.core import contracts as contract_core
from harness.core import plans as plan_core

PROJECT_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("HARNESS_GIT_TIMEOUT_SECONDS", "2")


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
    root = Path(tempfile.mkdtemp(prefix="harness-v3-test-"))
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
    (root / "tests" / "red_behavior.py").write_text(
        "from pathlib import Path\n"
        "old = 'VALUE = 1' in Path('src/app.py').read_text()\n"
        "print('OLD_BEHAVIOR_PRESENT' if old else 'NEW_BEHAVIOR_PRESENT')\n"
        "raise SystemExit(1 if old else 0)\n",
        encoding="utf-8",
    )
    (root / "tests" / "verify_arg.py").write_text(
        "import sys\n"
        "expected = 'M10 CodexAdapter minimal completes bounded run'\n"
        "raise SystemExit(0 if sys.argv[1:] == [expected] else 9)\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("fixture\n", encoding="utf-8")
    (root / ".gitignore").write_text(".harness/\n", encoding="utf-8")
    (root / "docs" / "spec").mkdir(parents=True, exist_ok=True)
    git(root, "add", ".")
    git(root, "commit", "-m", "fixture")
    return root


def valid_contract(wu_id: str, risk: str = "medium", *, quoted: bool = False) -> dict:
    final_argv = (
        [sys.executable, "tests/verify_arg.py", "M10 CodexAdapter minimal completes bounded run"]
        if quoted
        else [sys.executable, "tests/verify_behavior.py"]
    )
    return {
        "schema_version": contract_core.SCHEMA_VERSION,
        "id": wu_id,
        "title": "Test behavior",
        "type": "bugfix",
        "risk": risk,
        "approval": {
            "status": "draft",
            "approved_by": "",
            "approved_at": "",
            "approval_ref": "",
            "approved_content_hash": "",
        },
        "intent": "Correct one bounded behavior in the fixture.",
        "expected_outcomes": ["The target behavior is observable and correct."],
        "non_goals": ["Do not change unrelated modules."],
        "scope": {
            "likely_changed_areas": ["src/**"],
            "write_boundary": ["src/**"],
            "out_of_bounds": ["secrets/**"],
        },
        "required_evidence": [
            {"id": "EV1", "claim": "The targeted behavior passes.", "check_id": "check.ev1"}
        ],
        "verification": {
            "checks": {
                "check.ev1": {"runner": "exec", "argv": final_argv, "cwd": ".", "timeout_seconds": 60},
                "check.red": {"runner": "exec", "argv": [sys.executable, "tests/red_behavior.py"], "cwd": ".", "timeout_seconds": 60},
            }
        },
        "stop_conditions": {
            "success": ["EV1 passes after the implementation change."],
            "blocked": ["The implementation would need to modify secrets/**."],
        },
        "clarification": {
            "user_confirmed": True,
            "repo_grounded": True,
            "key_decisions": ["Keep the change inside src/** and verify EV1."],
            "remaining_assumptions": ["none"],
        },
        "open_questions": ["none"],
        "context_pointers": ["src/app.py", "tests/verify_behavior.py"],
        "delivery": {"issue": "", "branch": "", "pull_request": "", "required_checks": []},
        "risk_notes": ["No material risk beyond the local behavior."],
    }


def valid_spec(wu_id: str, risk: str = "medium", *, quoted: bool = False) -> str:
    return contract_core.render_spec(valid_contract(wu_id, risk, quoted=quoted), "User walked through and approved the bounded fixture behavior.")


def valid_plan(wu_id: str, *, expected_red_regex: str = "OLD_BEHAVIOR_PRESENT") -> str:
    plan = {
        "schema_version": plan_core.SCHEMA_VERSION,
        "work_unit_id": wu_id,
        "title": "Test behavior",
        "repository_grounding": ["Read src/app.py and the executable fixture checks."],
        "architecture_and_tradeoffs": "Change the smallest implementation surface; reject a broad refactor because it adds no value.",
        "change_map": [{"path": "src/app.py", "change": "Update the bounded value.", "reason": "Satisfy approved behavior."}],
        "behavior_slices": [
            {
                "id": "B1",
                "claim_ref": "EV1",
                "behavior": "Target behavior is corrected.",
                "test_paths": ["tests/red_behavior.py", "tests/verify_behavior.py"],
                "oracle": "The RED check emits the old-behavior signature and fails before the implementation; EV1 passes only after VALUE is corrected.",
                "red": {
                    "check_id": "check.red",
                    "expected_failure": {"kind": "exit_nonzero", "exit_codes": [1], "combined_regex": [expected_red_regex]},
                },
                "green": {"check_id": "check.ev1"},
                "allowed_paths": ["src/**"],
            }
        ],
        "acceptance_evidence": [
            {
                "claim_ref": "EV1",
                "check_id": "check.ev1",
                "level": "functional",
                "justification": "The final executable behavior check proves the user-visible bounded outcome rather than only an internal helper.",
            }
        ],
        "verification_notes": ["Execute EV1 through the controller after implementation."],
        "risks_and_replan_conditions": ["Stop if the write boundary must expand."],
        "reviewer_focus": ["Recheck scope, evidence freshness, and the TDD oracle."],
    }
    return plan_core.render_plan(plan)


class HarnessV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = make_repo()
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))

    def create_valid_wu(self, wu_id: str = "WU-1", risk: str = "medium", *, quoted: bool = False, red_regex: str = "OLD_BEHAVIOR_PRESENT") -> Path:
        run_ctl(self.root, "new", "--id", wu_id, "--title", "Test behavior", "--type", "bugfix", "--risk", risk)
        spec = self.root / "docs" / "spec" / f"{wu_id}.md"
        spec.write_text(valid_spec(wu_id, risk, quoted=quoted), encoding="utf-8")
        run_ctl(self.root, "approve-spec", "--id", wu_id, "--approved-by", "human:owner", "--approval-ref", "user-confirmation:test")
        wu = self.root / ".harness" / "work-units" / "active" / wu_id
        (wu / "plan.md").write_text(valid_plan(wu_id, expected_red_regex=red_regex), encoding="utf-8")
        return wu

    def plan_approve(self, wu_id: str = "WU-1", *, reviewer: str = "reviewer-1", session: str = "review-session", planner: str = "planner-1", planner_session: str = "planner-session") -> str:
        request = json.loads(
            run_ctl(
                self.root,
                "request-review", "--id", wu_id, "--mode", "plan",
                "--reviewer-id", reviewer, "--reviewer-session", session,
                "--planner-id", planner, "--planner-session", planner_session,
            ).stdout
        )
        run_ctl(
            self.root,
            "submit-review", "--id", wu_id, "--request-id", request["request_id"], "--mode", "plan", "--decision", "PASS",
            "--reviewer-id", reviewer, "--reviewer-session", session,
        )
        return request["request_id"]

    def start_and_verify(self, wu_id: str = "WU-1") -> str:
        run_ctl(self.root, "start-work", "--id", wu_id, "--builder-id", "worker-1", "--builder-session", "worker-session")
        (self.root / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        receipt = json.loads(run_ctl(self.root, "verify", "--id", wu_id, "--claim", "EV1", "--phase", "final").stdout)
        return receipt["receipt_id"]

    def close_approve(self, wu_id: str, receipt_id: str, *, reviewer: str = "reviewer-1", session: str = "review-session") -> str:
        request = json.loads(run_ctl(self.root, "request-review", "--id", wu_id, "--mode", "close", "--reviewer-id", reviewer, "--reviewer-session", session).stdout)
        verdict = json.loads(
            run_ctl(
                self.root,
                "submit-review", "--id", wu_id, "--request-id", request["request_id"], "--mode", "close", "--decision", "PASS",
                "--reviewer-id", reviewer, "--reviewer-session", session, "--evidence-ref", receipt_id,
            ).stdout
        )
        return verdict["review_id"]

    def test_new_tracks_only_spec_and_ignores_runtime(self) -> None:
        run_ctl(self.root, "new", "--id", "WU-A", "--title", "A")
        self.assertTrue((self.root / "docs/spec/WU-A.md").exists())
        self.assertTrue((self.root / ".harness/work-units/active/WU-A/plan.md").exists())
        status = git(self.root, "status", "--short", "--untracked-files=all")
        self.assertIn("docs/spec/WU-A.md", status)
        self.assertNotIn(".harness/", status)

    def test_spec_cannot_be_approved_with_placeholders(self) -> None:
        run_ctl(self.root, "new", "--id", "WU-B", "--title", "B")
        result = run_ctl(self.root, "approve-spec", "--id", "WU-B", "--approved-by", "human:owner", "--approval-ref", "user-confirmation:test", check=False)
        self.assertEqual(2, result.returncode)
        self.assertIn("placeholder", result.stderr.lower())

    def test_empty_open_questions_approves(self) -> None:
        # An empty open_questions list means "no questions" and must pass
        # approval without forcing the author to write ["none"].
        contract = valid_contract("WU-EMPTYQ", "medium")
        contract["open_questions"] = []
        run_ctl(self.root, "new", "--id", "WU-EMPTYQ", "--title", "Empty questions")
        spec = self.root / "docs/spec/WU-EMPTYQ.md"
        spec.write_text(contract_core.render_spec(contract, "No open questions remain."), encoding="utf-8")
        result = run_ctl(self.root, "approve-spec", "--id", "WU-EMPTYQ", "--approved-by", "human:owner", "--approval-ref", "user-confirmation:test", check=False)
        self.assertEqual(0, result.returncode)

    def test_material_spec_change_invalidates_plan_review(self) -> None:
        wu = self.create_valid_wu("WU-C")
        self.plan_approve("WU-C")
        spec = self.root / "docs/spec/WU-C.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace("Correct one bounded behavior", "Correct one materially changed behavior"), encoding="utf-8")
        run_ctl(self.root, "amend", "--id", "WU-C", "--reason", "Product intent changed", "--summary", "Changed target", "--actor", "human:owner", "--approval-ref", "user-confirmation:amend")
        state = json.loads((wu / "state.json").read_text(encoding="utf-8"))
        self.assertEqual("spec_approved", state["status"])
        self.assertEqual("", state["plan_approved_hash"])
        self.assertFalse((wu / "reviews/track.json").exists())

    def test_start_work_requires_plan_review_and_role_separation(self) -> None:
        self.create_valid_wu("WU-D")
        self.assertEqual(2, run_ctl(self.root, "start-work", "--id", "WU-D", "--builder-id", "worker", "--builder-session", "worker-session", check=False).returncode)
        self.plan_approve("WU-D", reviewer="reviewer-A", session="review-session", planner="planner-A", planner_session="planner-session")
        self.assertEqual(2, run_ctl(self.root, "start-work", "--id", "WU-D", "--builder-id", "reviewer-A", "--builder-session", "worker-session", check=False).returncode)
        self.assertEqual(2, run_ctl(self.root, "start-work", "--id", "WU-D", "--builder-id", "worker", "--builder-session", "review-session", check=False).returncode)
        run_ctl(self.root, "start-work", "--id", "WU-D", "--builder-id", "worker", "--builder-session", "worker-session")

    def test_plan_reviewer_must_differ_from_planner(self) -> None:
        self.create_valid_wu("WU-D2")
        same_identity = run_ctl(self.root, "request-review", "--id", "WU-D2", "--mode", "plan", "--reviewer-id", "planner-A", "--reviewer-session", "review", "--planner-id", "planner-A", "--planner-session", "planner", check=False)
        same_session = run_ctl(self.root, "request-review", "--id", "WU-D2", "--mode", "plan", "--reviewer-id", "reviewer-A", "--reviewer-session", "shared", "--planner-id", "planner-A", "--planner-session", "shared", check=False)
        self.assertEqual(2, same_identity.returncode)
        self.assertEqual(2, same_session.returncode)

    def test_structured_argv_preserves_embedded_space_argument(self) -> None:
        self.create_valid_wu("WU-Q", quoted=True)
        self.plan_approve("WU-Q")
        run_ctl(self.root, "start-work", "--id", "WU-Q", "--builder-id", "worker", "--builder-session", "worker-session")
        receipt = json.loads(run_ctl(self.root, "verify", "--id", "WU-Q", "--claim", "EV1", "--phase", "final").stdout)
        self.assertEqual("pass", receipt["result"])
        self.assertEqual("M10 CodexAdapter minimal completes bounded run", receipt["argv"][-1])
        explicit = json.loads(
            run_ctl(
                self.root, "verify", "--id", "WU-Q", "--claim", "EV1", "--phase", "final", "--",
                sys.executable, "tests/verify_arg.py", "M10 CodexAdapter minimal completes bounded run",
            ).stdout
        )
        self.assertEqual(receipt["argv"], explicit["argv"])

    def test_final_verification_is_controller_executed_and_exact(self) -> None:
        self.create_valid_wu("WU-E")
        self.plan_approve("WU-E")
        run_ctl(self.root, "start-work", "--id", "WU-E", "--builder-id", "worker", "--builder-session", "worker-session")
        bad = run_ctl(self.root, "verify", "--id", "WU-E", "--claim", "EV1", "--phase", "final", check=False)
        self.assertEqual(2, bad.returncode)
        receipt = json.loads(bad.stdout)
        self.assertEqual("fail", receipt["result"])
        self.assertEqual("controller_executed_check", receipt["observation"])
        mismatch = run_ctl(self.root, "verify", "--id", "WU-E", "--claim", "EV1", "--phase", "final", "--", sys.executable, "-c", "raise SystemExit(0)", check=False)
        self.assertEqual(2, mismatch.returncode)
        self.assertIn("exactly match", mismatch.stderr)
        (self.root / "src/app.py").write_text("VALUE = 2\n", encoding="utf-8")
        good = json.loads(run_ctl(self.root, "verify", "--id", "WU-E", "--claim", "EV1", "--phase", "final").stdout)
        self.assertEqual("pass", good["result"])
        self.assertTrue((self.root / good["command_log_ref"]).exists())

    def test_tdd_red_requires_declared_failure_reason(self) -> None:
        self.create_valid_wu("WU-F")
        self.plan_approve("WU-F")
        run_ctl(self.root, "start-work", "--id", "WU-F", "--builder-id", "worker", "--builder-session", "worker-session")
        red = json.loads(run_ctl(self.root, "verify", "--id", "WU-F", "--claim", "EV1", "--phase", "red", "--behavior", "B1").stdout)
        self.assertEqual("pass", red["result"])
        self.assertEqual("declared_red_failure", red["expected_outcome"])
        self.assertEqual(2, run_ctl(self.root, "check", "--id", "WU-F", "--gate", "verification", "--strict", check=False).returncode)

        self.create_valid_wu("WU-F2", red_regex="THIS_SIGNATURE_IS_ABSENT")
        self.plan_approve("WU-F2")
        run_ctl(self.root, "start-work", "--id", "WU-F2", "--builder-id", "worker2", "--builder-session", "worker-session2")
        wrong = run_ctl(self.root, "verify", "--id", "WU-F2", "--claim", "EV1", "--phase", "red", "--behavior", "B1", check=False)
        self.assertEqual(2, wrong.returncode)
        self.assertIn("THIS_SIGNATURE_IS_ABSENT", wrong.stdout)

    def test_evidence_becomes_stale_after_implementation_change(self) -> None:
        self.create_valid_wu("WU-G")
        self.plan_approve("WU-G")
        self.start_and_verify("WU-G")
        self.assertEqual(0, run_ctl(self.root, "check", "--id", "WU-G", "--gate", "verification", "--strict").returncode)
        (self.root / "src/app.py").write_text("VALUE = 3\n", encoding="utf-8")
        stale = run_ctl(self.root, "check", "--id", "WU-G", "--gate", "verification", "--strict", check=False)
        self.assertEqual(2, stale.returncode)
        self.assertIn("stale", stale.stdout.lower())

    def test_skipped_evidence_blocks_and_is_not_waiver(self) -> None:
        self.create_valid_wu("WU-H")
        self.plan_approve("WU-H")
        run_ctl(self.root, "start-work", "--id", "WU-H", "--builder-id", "worker", "--builder-session", "worker-session")
        receipt = json.loads(run_ctl(self.root, "record-skipped", "--id", "WU-H", "--claim", "EV1", "--reason", "Tool unavailable", "--replacement", "none", "--risk-impact", "unknown", "--owner", "human:owner").stdout)
        self.assertEqual("skipped", receipt["result"])
        state = json.loads((self.root / ".harness/work-units/active/WU-H/state.json").read_text(encoding="utf-8"))
        self.assertEqual("blocked", state["status"])
        self.assertNotIn("waiver", harnessctl.build_parser().format_help().lower())

    def test_close_review_requires_same_reviewer_logical_session(self) -> None:
        wu = self.create_valid_wu("WU-I")
        self.plan_approve("WU-I", reviewer="reviewer-A", session="review-session")
        receipt_id = self.start_and_verify("WU-I")
        wrong_identity = run_ctl(self.root, "request-review", "--id", "WU-I", "--mode", "close", "--reviewer-id", "reviewer-B", "--reviewer-session", "review-session", check=False)
        wrong_session = run_ctl(self.root, "request-review", "--id", "WU-I", "--mode", "close", "--reviewer-id", "reviewer-A", "--reviewer-session", "another-session", check=False)
        self.assertEqual(2, wrong_identity.returncode)
        self.assertEqual(2, wrong_session.returncode)
        self.close_approve("WU-I", receipt_id, reviewer="reviewer-A", session="review-session")
        result = json.loads(run_ctl(self.root, "finalize-check", "--id", "WU-I", "--strict").stdout)
        self.assertIn(result["decision"], {"PASS", "WARN"})
        track = json.loads((wu / "reviews/track.json").read_text(encoding="utf-8"))
        self.assertEqual("review-session", track["logical_reviewer_session_id"])
        self.assertTrue(track["plan_review_id"])
        self.assertTrue(track["close_review_id"])

    def test_builder_cannot_submit_close_review(self) -> None:
        self.create_valid_wu("WU-J")
        self.plan_approve("WU-J", reviewer="reviewer-A", session="review-session")
        receipt_id = self.start_and_verify("WU-J")
        request = json.loads(run_ctl(self.root, "request-review", "--id", "WU-J", "--mode", "close", "--reviewer-id", "reviewer-A", "--reviewer-session", "review-session").stdout)
        result = run_ctl(self.root, "submit-review", "--id", "WU-J", "--request-id", request["request_id"], "--mode", "close", "--decision", "PASS", "--reviewer-id", "worker-1", "--reviewer-session", "worker-session", "--evidence-ref", receipt_id, check=False)
        self.assertEqual(2, result.returncode)

    def test_reviewer_takeover_is_explicit_and_requires_new_plan_review(self) -> None:
        wu = self.create_valid_wu("WU-T")
        self.plan_approve("WU-T", reviewer="reviewer-A", session="review-A")
        run_ctl(self.root, "reviewer-takeover", "--id", "WU-T", "--new-reviewer-id", "reviewer-B", "--new-reviewer-session", "review-B", "--reason", "Original session unavailable", "--approved-by", "human:owner", "--approval-ref", "incident:1")
        state = json.loads((wu / "state.json").read_text(encoding="utf-8"))
        track = json.loads((wu / "reviews/track.json").read_text(encoding="utf-8"))
        self.assertEqual("planning", state["status"])
        self.assertEqual("", state["plan_approved_hash"])
        self.assertEqual(2, track["generation"])
        self.assertEqual("", track["plan_review_id"])

    def test_close_review_invalidated_by_post_review_commit(self) -> None:
        self.create_valid_wu("WU-HEAD")
        self.plan_approve("WU-HEAD")
        receipt_id = self.start_and_verify("WU-HEAD")
        self.close_approve("WU-HEAD", receipt_id)
        git(self.root, "add", "docs/spec/WU-HEAD.md", "src/app.py")
        git(self.root, "commit", "-m", "post review commit")
        result = run_ctl(self.root, "check", "--id", "WU-HEAD", "--gate", "review", "--strict", check=False)
        self.assertEqual(2, result.returncode)
        self.assertIn("HEAD changed", result.stdout)

    def test_resume_session_and_reconstruct_are_distinct(self) -> None:
        self.create_valid_wu("WU-K")
        run_ctl(self.root, "resume-session", "--id", "WU-K")
        shutil.rmtree(self.root / ".harness")
        self.assertEqual(2, run_ctl(self.root, "resume", "--id", "WU-K", check=False).returncode)
        result = json.loads(run_ctl(self.root, "reconstruct", "--id", "WU-K").stdout)
        self.assertEqual("reconstruction_not_continuation", result["recovery"])
        state = json.loads((self.root / ".harness/work-units/active/WU-K/state.json").read_text(encoding="utf-8"))
        self.assertEqual("spec_approved", state["status"])
        self.assertEqual([], state["latest_evidence_refs"])

    def test_tampered_spec_reconstructs_to_clarification(self) -> None:
        self.create_valid_wu("WU-K2")
        spec = self.root / "docs/spec/WU-K2.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace("Correct one bounded behavior", "Unapproved behavior"), encoding="utf-8")
        shutil.rmtree(self.root / ".harness")
        result = json.loads(run_ctl(self.root, "reconstruct", "--id", "WU-K2").stdout)
        self.assertEqual("clarifying", result["status"])

    def test_checkpoint_is_fresh_and_handoff_is_derived(self) -> None:
        wu = self.create_valid_wu("WU-R")
        self.plan_approve("WU-R")
        run_ctl(self.root, "start-work", "--id", "WU-R", "--builder-id", "worker", "--builder-session", "worker-session")
        result = json.loads(run_ctl(self.root, "checkpoint", "--id", "WU-R", "--reason", "pre_compact").stdout)
        self.assertEqual("pre_compact", result["checkpoint"]["reason"])
        self.assertEqual("worker-session", result["checkpoint"]["builder_session_id"])
        run_ctl(self.root, "handoff", "--id", "WU-R", "--next-safe-action", "Resume TDD in a fresh worker session.")
        text = (wu / "handoff.md").read_text(encoding="utf-8")
        self.assertIn("Recovery checkpoint", text)
        self.assertIn("Resume TDD", text)


    def test_controller_shell_exception_rejects_compound_command(self) -> None:
        run_ctl(self.root, "new", "--id", "WU-POLICY", "--title", "Policy")
        sys.path.insert(0, str(PROJECT_ROOT / "harness/hooks"))
        try:
            import policy_common  # type: ignore
            event = {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "python3 harness/cli/harnessctl.py status --id WU-POLICY; printf x > src/app.py"
                },
            }
            decision, reason = policy_common.phase_command_policy(self.root, event)
            self.assertEqual("deny", decision)
            self.assertIn("blocked", reason.lower())
            self.assertTrue(
                policy_common._is_single_controller_command(
                    "python3 harness/cli/harnessctl.py handoff --id WU-POLICY --next-safe-action 'inspect; do not edit'"
                )
            )
            self.assertFalse(
                policy_common._is_single_controller_command(
                    "python3 harness/cli/harnessctl.py status --id WU-POLICY && touch src/app.py"
                )
            )
        finally:
            sys.path.pop(0)
            sys.modules.pop("policy_common", None)

    def test_repository_identity_is_shared_but_workspace_identity_isolated(self) -> None:
        from harness.core.repository import RepoSnapshot

        linked = self.root.parent / f"{self.root.name}-linked"
        self.addCleanup(lambda: shutil.rmtree(linked, ignore_errors=True))
        git(self.root, "worktree", "add", "-b", "linked-test", str(linked), "HEAD")
        main = RepoSnapshot.capture(self.root)
        other = RepoSnapshot.capture(linked)
        self.assertEqual(main.repository_id, other.repository_id)
        self.assertNotEqual(main.workspace_id, other.workspace_id)

    def test_phase_policy_blocks_product_write_before_implementation(self) -> None:
        run_ctl(self.root, "new", "--id", "WU-L", "--title", "L")
        sys.path.insert(0, str(PROJECT_ROOT / "harness/hooks"))
        try:
            import policy_common  # type: ignore
            decision, _ = policy_common.phase_write_policy(self.root, {"tool_name": "Write", "tool_input": {"file_path": "src/app.py"}})
            allowed, _ = policy_common.phase_write_policy(self.root, {"tool_name": "Write", "tool_input": {"file_path": "docs/spec/WU-L.md"}})
            self.assertEqual("deny", decision)
            self.assertEqual("allow", allowed)
        finally:
            sys.path.pop(0)
            sys.modules.pop("policy_common", None)

    def test_workspace_pointer_and_binding_are_not_global(self) -> None:
        with mock.patch.dict(os.environ, {"HARNESS_SESSION_ID": "session-a"}, clear=False):
            run_ctl(self.root, "new", "--id", "WU-M", "--title", "M")
            pointer_a = harnessctl.current_file(self.root)
        with mock.patch.dict(os.environ, {"HARNESS_SESSION_ID": "session-b"}, clear=False):
            pointer_b = harnessctl.current_file(self.root)
        self.assertNotEqual(pointer_a, pointer_b)
        self.assertFalse(pointer_b.exists())
        git(self.root, "switch", "-c", "other-branch")
        result = run_ctl(self.root, "workspace-check", "--id", "WU-M", check=False)
        self.assertEqual(2, result.returncode)
        self.assertFalse(json.loads(result.stdout)["checks"]["branch"])

    def test_goal_projection_cannot_complete_or_archive_work_unit(self) -> None:
        wu = self.create_valid_wu("WU-GOAL")
        self.plan_approve("WU-GOAL")
        before = json.loads((wu / "state.json").read_text(encoding="utf-8"))["status"]
        goal = json.loads(run_ctl(self.root, "goal-export", "--id", "WU-GOAL", "--thread-ref", "thread-123").stdout)
        after = json.loads((wu / "state.json").read_text(encoding="utf-8"))["status"]
        self.assertEqual("harness_controller_not_goal_completion", goal["acceptance_authority"])
        self.assertEqual(before, after)
        self.assertEqual("ready", after)

    def test_dispatch_review_dry_run_does_not_mutate_state(self) -> None:
        wu = self.create_valid_wu("WU-DISPATCH")
        before = json.loads((wu / "state.json").read_text(encoding="utf-8"))["status"]
        result = json.loads(run_ctl(self.root, "dispatch-review", "--id", "WU-DISPATCH", "--mode", "plan", "--platform", "codex", "--dry-run").stdout)
        after = json.loads((wu / "state.json").read_text(encoding="utf-8"))["status"]
        self.assertFalse(result["state_changed"])
        self.assertEqual(before, after)
        self.assertIn("exec", result["command"])


    def test_dispatch_worker_dry_run_does_not_mutate_state(self) -> None:
        wu = self.create_valid_wu("WU-WORKER-DISPATCH")
        self.plan_approve("WU-WORKER-DISPATCH")
        before = json.loads((wu / "state.json").read_text(encoding="utf-8"))["status"]
        result = json.loads(
            run_ctl(
                self.root,
                "dispatch-worker",
                "--id",
                "WU-WORKER-DISPATCH",
                "--platform",
                "codex",
                "--dry-run",
            ).stdout
        )
        after = json.loads((wu / "state.json").read_text(encoding="utf-8"))["status"]
        self.assertFalse(result["state_changed"])
        self.assertEqual(before, after)
        self.assertIn("workspace-write", result["command"])

    def test_platform_commands_encode_role_and_resume_semantics(self) -> None:
        from harness.platforms import adapters

        prompt = self.root / "prompt.md"
        schema = self.root / "schema.json"
        prompt.write_text("do work", encoding="utf-8")
        schema.write_text("{}", encoding="utf-8")
        review_resume = adapters.review_command(
            "codex", prompt_file=prompt, schema_file=schema, cwd=self.root, session_id="thread-1"
        )
        review_fresh = adapters.review_command(
            "codex", prompt_file=prompt, schema_file=schema, cwd=self.root
        )
        worker_resume = adapters.worker_command(
            "codex", prompt_file=prompt, schema_file=schema, cwd=self.root, session_id="thread-2"
        )
        worker = adapters.worker_command(
            "claude", prompt_file=prompt, schema_file=schema, cwd=self.root, session_id="session-1"
        )
        self.assertEqual(["exec", "resume", "thread-1"], review_resume[1:4])
        self.assertNotIn("--sandbox", review_resume)
        self.assertIn("--sandbox", review_fresh)
        self.assertIn("read-only", review_fresh)
        self.assertEqual(["exec", "resume", "thread-2"], worker_resume[1:4])
        self.assertNotIn("--sandbox", worker_resume)
        self.assertIn("harness-worker", worker)
        self.assertIn("--resume", worker)
        self.assertIn("session-1", worker)
        schema_arg = worker[worker.index("--json-schema") + 1]
        self.assertEqual("{}", schema_arg)
        self.assertNotEqual(str(schema), schema_arg)

    def test_console_entry_point_targets_main(self) -> None:
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('[project.scripts]', pyproject)
        self.assertIn('harnessctl = "harness.cli.harnessctl:main"', pyproject)

    def test_hook_subcommand_supports_compaction_and_stop(self) -> None:
        parser = harnessctl.build_parser()
        for name in ("pre-compact", "post-compact", "stop"):
            args = parser.parse_args(["hook", name])
            self.assertEqual("hook_dispatch", args.func.__name__)

    def test_context_router_treats_codex_pr_explorer_as_reviewer(self) -> None:
        run_ctl(self.root, "new", "--id", "WU-HOOK", "--title", "Hook")
        sys.path.insert(0, str(PROJECT_ROOT))
        try:
            from harness.hooks import context_router  # type: ignore

            message = context_router.context(
                self.root,
                "SubagentStart",
                {"platform": "codex", "session_id": "subagent-session-1", "agent_type": "pr_explorer", "cwd": str(self.root)},
            )
            self.assertIn("reviewer (read-only)", message)
            binding = harnessctl.session_core.latest(self.root, "WU-HOOK", "reviewer")
            self.assertEqual("codex", binding["platform"])
            self.assertEqual("subagent-session-1", binding["session_id"])
        finally:
            sys.path.pop(0)
            sys.modules.pop("harness.hooks.context_router", None)

    def test_codex_goal_bootstrap_uses_persisted_app_server_state(self) -> None:
        from harness.platforms import adapters

        fake = self.root / "fake-codex"
        fake.write_text(
            """#!/usr/bin/env python3
import json
import sys

for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params", {})
    if request_id is None:
        continue
    if method == "initialize":
        result = {"userAgent": "fake"}
    elif method == "thread/start":
        result = {"thread": {"id": "thr-created", "sessionId": "thr-created"}}
    elif method == "thread/resume":
        thread_id = params["threadId"]
        result = {"thread": {"id": thread_id, "sessionId": thread_id}}
    elif method == "thread/goal/set":
        result = {"goal": {
            "threadId": params["threadId"],
            "objective": params["objective"],
            "status": params["status"],
            "tokenBudget": params["tokenBudget"],
            "tokensUsed": 0,
            "timeUsedSeconds": 0,
        }}
    else:
        print(json.dumps({"id": request_id, "error": {"message": "unsupported"}}), flush=True)
        continue
    print(json.dumps({"id": request_id, "result": result}), flush=True)
""",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        created = adapters.ensure_codex_goal(
            cwd=self.root,
            objective="Implement WU with fresh evidence",
            executable=str(fake),
            timeout_seconds=5,
        )
        self.assertEqual("thr-created", created.thread_id)
        self.assertEqual("Implement WU with fresh evidence", created.goal["objective"])
        resumed = adapters.ensure_codex_goal(
            cwd=self.root,
            objective="Continue WU with fresh evidence",
            session_id="thr-existing",
            executable=str(fake),
            timeout_seconds=5,
        )
        self.assertEqual("thr-existing", resumed.thread_id)
        self.assertEqual(40000, resumed.goal["tokenBudget"])

    def test_route_selects_plan_and_close_review_automatically(self) -> None:
        self.create_valid_wu("WU-ROUTE")
        decision = json.loads(run_ctl(self.root, "route", "--id", "WU-ROUTE", "--platform", "codex").stdout)
        self.assertEqual("native_plan_review", decision["action"])
        self.assertFalse(decision["automatic"])
        self.plan_approve("WU-ROUTE")
        ready = json.loads(run_ctl(self.root, "route", "--id", "WU-ROUTE", "--platform", "codex").stdout)
        self.assertEqual("native_worker", ready["action"])
        self.assertFalse(ready["automatic"])
        self.start_and_verify("WU-ROUTE")
        close = json.loads(run_ctl(self.root, "route", "--id", "WU-ROUTE", "--platform", "codex").stdout)
        self.assertEqual("native_close_review", close["action"])

    def test_claude_route_keeps_controller_dispatch(self) -> None:
        self.create_valid_wu("WU-ROUTE-CLAUDE")
        decision = json.loads(run_ctl(self.root, "route", "--id", "WU-ROUTE-CLAUDE", "--platform", "claude").stdout)
        self.assertEqual("dispatch_plan_review", decision["action"])
        self.assertTrue(decision["automatic"])

    def test_plan_must_cover_every_required_evidence_claim(self) -> None:
        run_ctl(self.root, "new", "--id", "WU-COVERAGE", "--title", "Coverage", "--type", "feature", "--risk", "medium")
        contract = valid_contract("WU-COVERAGE")
        contract["required_evidence"].append({"id": "EV2", "claim": "A second behavior is covered.", "check_id": "check.ev2"})
        contract["verification"]["checks"]["check.ev2"] = {
            "runner": "exec",
            "argv": [sys.executable, "tests/verify_behavior.py"],
            "cwd": ".",
            "timeout_seconds": 60,
        }
        spec = self.root / "docs/spec/WU-COVERAGE.md"
        spec.write_text(contract_core.render_spec(contract), encoding="utf-8")
        run_ctl(self.root, "approve-spec", "--id", "WU-COVERAGE", "--approved-by", "human:owner", "--approval-ref", "test:coverage")
        wu = self.root / ".harness/work-units/active/WU-COVERAGE"
        (wu / "plan.md").write_text(valid_plan("WU-COVERAGE"), encoding="utf-8")
        result = run_ctl(self.root, "check", "--id", "WU-COVERAGE", "--gate", "plan", "--strict", check=False)
        self.assertEqual(2, result.returncode)
        self.assertIn("EV2", result.stdout)
        self.assertIn("not covered", result.stdout)

    def test_github_delivery_gate_binds_pr_head_and_required_checks(self) -> None:
        wu = self.create_valid_wu("WU-GITHUB")
        self.plan_approve("WU-GITHUB")
        receipt = self.start_and_verify("WU-GITHUB")
        self.close_approve("WU-GITHUB", receipt)
        run_ctl(
            self.root,
            "delivery-link",
            "--id",
            "WU-GITHUB",
            "--pull-request",
            "123",
            "--required-check",
            "test",
        )
        snapshot = {
            "schema_version": harnessctl.GITHUB_SCHEMA,
            "work_unit_id": "WU-GITHUB",
            "number": 123,
            "state": "OPEN",
            "headRefOid": git(self.root, "rev-parse", "HEAD"),
            "normalized_checks": [
                {"name": "test", "status": "COMPLETED", "outcome": "SUCCESS", "successful": True}
            ],
        }
        harnessctl.write_json(wu / "github" / "pull-request.json", snapshot)
        passed = json.loads(run_ctl(self.root, "check", "--id", "WU-GITHUB", "--gate", "delivery", "--strict").stdout)
        self.assertEqual("PASS", passed["decision"])
        snapshot["normalized_checks"][0].update({"outcome": "FAILURE", "successful": False})
        harnessctl.write_json(wu / "github" / "pull-request.json", snapshot)
        blocked = run_ctl(self.root, "check", "--id", "WU-GITHUB", "--gate", "delivery", "--strict", check=False)
        self.assertEqual(2, blocked.returncode)
        self.assertIn("not successful", blocked.stdout)

    def test_forced_archive_requires_auditable_human_override(self) -> None:
        self.create_valid_wu("WU-FORCE")
        denied = run_ctl(self.root, "archive", "--id", "WU-FORCE", "--force", check=False)
        self.assertEqual(2, denied.returncode)
        self.assertIn("requires --reason", denied.stderr)
        result = json.loads(
            run_ctl(
                self.root,
                "archive",
                "--id",
                "WU-FORCE",
                "--force",
                "--reason",
                "Close abandoned local experiment",
                "--approved-by",
                "human:owner",
                "--approval-ref",
                "issue:123#comment-9",
            ).stdout
        )
        self.assertTrue(result["forced"])
        override = self.root / ".harness/work-units/archive/WU-FORCE/reviews/archive-override.json"
        self.assertTrue(override.exists())
        self.assertEqual("human:owner", json.loads(override.read_text(encoding="utf-8"))["approved_by"])

    def test_adoption_upgrade_updates_only_unmodified_managed_assets(self) -> None:
        target = Path(tempfile.mkdtemp(prefix="harness-upgrade-target-"))
        source = Path(tempfile.mkdtemp(prefix="harness-upgrade-source-")) / "source"
        self.addCleanup(lambda: shutil.rmtree(target, ignore_errors=True))
        self.addCleanup(lambda: shutil.rmtree(source.parent, ignore_errors=True))
        git(target, "init")
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts/adopt.py"), "install", str(target), "--profile", "codex", "--no-doctor"],
            cwd=PROJECT_ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertTrue((target / ".harness-adoption.json").exists())
        shutil.copytree(
            PROJECT_ROOT,
            source,
            ignore=shutil.ignore_patterns(".git", ".harness", "__pycache__", "*.pyc", "*.zip"),
        )
        source_doc = source / "docs/harness/README.md"
        source_doc.write_text(source_doc.read_text(encoding="utf-8") + "\nupgrade-probe-v1\n", encoding="utf-8")
        upgraded = subprocess.run(
            [sys.executable, str(source / "scripts/adopt.py"), "upgrade", str(target), "--no-doctor"],
            cwd=source,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(0, upgraded.returncode, upgraded.stderr)
        target_doc = target / "docs/harness/README.md"
        self.assertIn("upgrade-probe-v1", target_doc.read_text(encoding="utf-8"))
        target_doc.write_text(target_doc.read_text(encoding="utf-8") + "local-edit\n", encoding="utf-8")
        source_doc.write_text(source_doc.read_text(encoding="utf-8") + "upgrade-probe-v2\n", encoding="utf-8")
        source_skill = source / ".agents/skills/harness-clarify/SKILL.md"
        target_skill = target / ".agents/skills/harness-clarify/SKILL.md"
        source_skill.write_text(source_skill.read_text(encoding="utf-8") + "\natomic-upgrade-probe\n", encoding="utf-8")
        blocked = subprocess.run(
            [sys.executable, str(source / "scripts/adopt.py"), "upgrade", str(target), "--no-doctor"],
            cwd=source,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(2, blocked.returncode)
        self.assertIn("locally modified", blocked.stderr)
        self.assertIn("local-edit", target_doc.read_text(encoding="utf-8"))
        self.assertNotIn("atomic-upgrade-probe", target_skill.read_text(encoding="utf-8"))

        reinstall = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts/adopt.py"), "install", str(target), "--profile", "codex", "--no-doctor"],
            cwd=PROJECT_ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(2, reinstall.returncode)
        self.assertIn("use 'check' or 'upgrade'", reinstall.stderr)

    def test_release_package_is_deterministic_and_excludes_runtime(self) -> None:
        output_dir = Path(tempfile.mkdtemp(prefix="harness-package-test-"))
        self.addCleanup(lambda: shutil.rmtree(output_dir, ignore_errors=True))
        archives = [output_dir / "a.zip", output_dir / "b.zip"]
        for archive in archives:
            subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "scripts/package.py"), "--output", str(archive)],
                cwd=PROJECT_ROOT,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        self.assertEqual(archives[0].read_bytes(), archives[1].read_bytes())
        import zipfile
        with zipfile.ZipFile(archives[0]) as zipped:
            names = zipped.namelist()
        self.assertTrue(any(name.endswith("/PACKAGE-MANIFEST.json") for name in names))
        self.assertFalse(any("/.harness/" in name or "__pycache__" in name or name.endswith(".pyc") or name.endswith("/.harness-adoption.json") for name in names))

    def test_skill_and_hook_layout_is_consistent(self) -> None:
        self.assertEqual(0, run_ctl(PROJECT_ROOT, "check", "--gate", "skills", "--strict").returncode)
        codex = json.loads((PROJECT_ROOT / ".codex/hooks.json").read_text(encoding="utf-8"))["hooks"]
        claude = json.loads((PROJECT_ROOT / ".claude/settings.json").read_text(encoding="utf-8"))["hooks"]
        for hooks in (codex, claude):
            self.assertIn("PreToolUse", hooks)
            self.assertIn("PreCompact", hooks)
            self.assertIn("PostCompact", hooks)
            self.assertIn("Stop", hooks)

    def test_adoption_installs_current_assets_and_only_ignores_runtime(self) -> None:
        target = Path(tempfile.mkdtemp(prefix="harness-adopt-test-"))
        self.addCleanup(lambda: shutil.rmtree(target, ignore_errors=True))
        git(target, "init")
        (target / "README.md").write_text("target\n", encoding="utf-8")
        proc = subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts/adopt.py"), "install", str(target), "--profile", "codex", "--no-doctor"], cwd=PROJECT_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertTrue((target / ".agents/skills/harness-clarify/SKILL.md").exists())
        self.assertTrue((target / "docs/spec/README.md").exists())
        self.assertFalse((target / "harness/tests").exists())
        self.assertEqual(
            [".harness/", "docs/harness/", "harness/", "harnessctl", ".codex", ".claude"],
            [line for line in (target / ".gitignore").read_text(encoding="utf-8").splitlines() if line],
        )
        self.assertIn("harness-owned local assets are added to .gitignore", proc.stdout)

    def test_adoption_install_uses_target_safe_ci_assets(self) -> None:
        target = Path(tempfile.mkdtemp(prefix="harness-adopt-ci-test-"))
        self.addCleanup(lambda: shutil.rmtree(target, ignore_errors=True))
        git(target, "init")
        (target / "README.md").write_text("target\n", encoding="utf-8")
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts/adopt.py"), "install", str(target), "--profile", "codex", "--no-doctor"],
            cwd=PROJECT_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        makefile = (target / "Makefile").read_text(encoding="utf-8")
        workflow = (target / ".github/workflows/harness-checks.yml").read_text(encoding="utf-8")
        self.assertNotIn("scripts/package.py", makefile)
        self.assertNotIn("release:", makefile)
        self.assertIn("./harnessctl", makefile)
        self.assertNotIn("unittest discover -s harness/tests", workflow)
        self.assertIn("./harnessctl", workflow)
        self.assertTrue((target / "harnessctl").exists())
        proc = subprocess.run(
            ["make", "check"],
            cwd=target,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(0, proc.returncode, proc.stderr)

    def test_thin_shared_codex_profile_installs_minimal_tracked_surface(self) -> None:
        target = Path(tempfile.mkdtemp(prefix="harness-thin-codex-test-"))
        self.addCleanup(lambda: shutil.rmtree(target, ignore_errors=True))
        git(target, "init")
        (target / "README.md").write_text("target\n", encoding="utf-8")
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts/adopt.py"), "install", str(target), "--profile", "thin-shared-codex", "--no-doctor"],
            cwd=PROJECT_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertTrue((target / "harness.lock").exists())
        self.assertTrue((target / "harness/project.yaml").exists())
        self.assertTrue((target / ".codex/hooks.json").exists())
        self.assertTrue((target / ".agents/skills/harness-clarify/SKILL.md").exists())
        self.assertFalse((target / "harness/cli").exists())
        self.assertFalse((target / "harness/core").exists())
        self.assertFalse((target / "skills").exists())
        hooks = json.loads((target / ".codex/hooks.json").read_text(encoding="utf-8"))["hooks"]
        self.assertEqual({"PreCompact", "PostCompact", "Stop"}, set(hooks))
        commands = json.dumps(hooks, ensure_ascii=False)
        self.assertIn("harnessctl hook pre-compact", commands)
        self.assertIn("harnessctl hook post-compact", commands)
        self.assertIn("harnessctl hook stop", commands)

    def test_thin_shared_claude_profile_installs_minimal_tracked_surface(self) -> None:
        target = Path(tempfile.mkdtemp(prefix="harness-thin-claude-test-"))
        self.addCleanup(lambda: shutil.rmtree(target, ignore_errors=True))
        git(target, "init")
        (target / "README.md").write_text("target\n", encoding="utf-8")
        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts/adopt.py"), "install", str(target), "--profile", "thin-shared-claude", "--no-doctor"],
            cwd=PROJECT_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        self.assertTrue((target / "harness.lock").exists())
        self.assertTrue((target / "harness/project.yaml").exists())
        self.assertTrue((target / ".claude/settings.json").exists())
        self.assertTrue((target / ".claude/skills/harness-clarify/SKILL.md").exists())
        self.assertFalse((target / "harness/hooks").exists())
        self.assertFalse((target / "skills").exists())
        settings = json.loads((target / ".claude/settings.json").read_text(encoding="utf-8"))
        self.assertEqual({"PreCompact", "PostCompact", "Stop"}, set(settings["hooks"]))
        commands = json.dumps(settings["hooks"], ensure_ascii=False)
        self.assertIn("harnessctl hook pre-compact", commands)
        self.assertIn("harnessctl hook post-compact", commands)
        self.assertIn("harnessctl hook stop", commands)

    def test_release_verify_runs_thin_shared_adoption_smoke(self) -> None:
        output_dir = Path(tempfile.mkdtemp(prefix="harness-package-verify-test-"))
        self.addCleanup(lambda: shutil.rmtree(output_dir, ignore_errors=True))
        archive = output_dir / "verify.zip"
        proc = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts/package.py"), "--output", str(archive), "--verify", "--skip-tests"],
            cwd=PROJECT_ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["verified"])
        self.assertEqual(str(archive), payload["archive"])


if __name__ == "__main__":
    unittest.main()
