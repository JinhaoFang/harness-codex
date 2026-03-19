import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[1]
OLD_TIMESTAMP = "2000-01-01 00:00 +0000"


def build_complete_plan(task_id: str, title: str) -> str:
    return textwrap.dedent(
        f"""\
        ---
        task_id: {task_id}
        title: {title}
        status: draft
        updated_at: {OLD_TIMESTAMP}
        ---

        # Plan: {title}

        ## Goal

        - Problem: Verify runtime state synchronization.
        - Goal: Exercise plan and workflow state transitions in a two-subtask task.
        - Deliverable: Controller-generated task artifacts proving the runtime state behavior.
        - Observable effect: Workflow and plan frontmatter expose the current task and review state.
        - Demo sentence of success: The generated artifacts show whether status transitions remain accurate.
        - Why now: Regression coverage for runtime state signals.

        ## Non-goals

        - Changing business code.

        ## Acceptance

        - Success criteria: The task can reach plan review PASS, implementation, evidence capture, and close review PASS for S1 while S2 remains unfinished.
        - User-visible acceptance signal: The generated workflow and review artifacts show the current review state for S1 and the remaining work for S2.
        - Terminal completion definition: The runtime state can be checked directly from generated artifacts.
        - Not acceptable completion definitions: Inferring state from chat history instead of generated files.
        - Out-of-scope guardrail: No runtime source changes are made in the copied test workspace.

        ## Requirement split

        - User-confirmed requirements: Reproduce controller-driven state transitions for two subtasks.
        - Must-preserve requirements: Keep the test isolated to the copied runtime workspace.
        - Project / world constraints: World-grounded anchors must point to repo files, not `.agentdocs/*`.
        - You decide: Exact wording and evidence commands.

        ## World-grounded anchors

        > Only reference current repo files that already exist outside `.agentdocs/*`.

        - Code paths: `.codex/tools/agentctl.py`
        - Key symbols / entry points: `cmd_refresh_pack`, `cmd_request_review`, `cmd_submit_review`, `cmd_check_gate`, `cmd_archive`
        - Existing tests: `tests/test_agentctl_runtime.py`
        - Existing docs / source materials: `README.md`, `AGENTS.md`, `docs/agentic/reference/controller-commands.md`
        - Reusable existing mechanisms: controller task skeletons, structured review JSON, workflow state updates
        - Compatibility constraints: Review artifacts are written per subtask.

        ## Decision freeze

        - Frozen decisions: Use two subtasks so that one can pass close review while the other remains pending.
        - Open questions requiring escalation: N/A

        ## Boundaries

        - Write boundary: Temporary `.agentdocs/tasks/{task_id}/` artifacts in the copied workspace only.
        - Phase order / stage boundaries: Freeze Goal Truth -> Plan review -> Implementation -> Close review for S1; S2 remains pending.
        - Approval points: Plan review must pass before implementation; evidence must exist before close review.
        - Forbidden zones: Runtime source files in the original workspace.
        - Deletion / migration guardrails: N/A
        - Invariants: `plan.md` is Goal truth; `workflow.md` is Process truth; reviews remain per-subtask artifacts.

        ## Verification

        - Required checks: `refresh-pack`, `request-review`, `submit-review`, `check-gate`, `write-evidence`, `validate-refs`
        - Evidence to collect: review JSON files, evidence JSON files, plan frontmatter, workflow summary bullets
        - Reviewer recheck focus: plan frontmatter status sync and task-level close-ready aggregation

        ## Subtasks

        ### S1 - Verify the first subtask path

        - Goal: Move the first subtask through review, implementation-ready, evidence, and close review.
        - Expected effect: The workflow records a PASS close review for S1.
        - Depends on:
        - Preconditions: Discuss readiness is satisfied and the plan is complete.
        - Write boundary: Temporary task artifacts in the copied workspace only.
        - Verify: Run controller commands and inspect generated artifacts.
        - Review focus: Whether S1 completion is kept separate from overall task completion.

        ### S2 - Remain unfinished

        - Goal: Keep the second subtask pending.
        - Expected effect: The workflow still shows unfinished task-level close readiness.
        - Depends on: S1
        - Preconditions: S1 review artifacts exist.
        - Write boundary: No implementation or evidence for S2.
        - Verify: Confirm there is no close review artifact for S2.
        - Review focus: Whether the workflow still exposes S2 as pending.

        ## Rollback / migration

        - Rollback strategy: Delete the temporary copied workspace.
        - Migration notes: N/A
        """
    )


class AgentctlRuntimeTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.runtime_root = Path(self.tmpdir.name) / "runtime"
        shutil.copytree(SOURCE_ROOT, self.runtime_root)
        self.controller = self.runtime_root / ".codex" / "tools" / "agentctl.py"

        self.run_cmd("init-agentdocs")
        create_out = self.run_cmd("create-task", "--slug", "state-sync", "--title", "State sync")
        self.task_id = self.parse_task_id(create_out.stdout)
        self.task_dir = self.runtime_root / ".agentdocs" / "tasks" / self.task_id
        self.plan_path = self.task_dir / "plan.md"
        self.workflow_path = self.task_dir / "workflow.md"
        self.plan_path.write_text(build_complete_plan(self.task_id, "State sync"), encoding="utf-8")
        self.mark_discuss_ready()

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def run_cmd(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(self.controller), *args],
            cwd=self.runtime_root,
            text=True,
            capture_output=True,
            check=False,
        )
        if check and result.returncode != 0:
            raise AssertionError(
                f"command failed: {args}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def parse_task_id(self, stdout: str) -> str:
        for line in stdout.splitlines():
            if line.startswith("- task id: "):
                return line.split(": ", 1)[1].strip()
        raise AssertionError(f"task id not found in output:\n{stdout}")

    def parse_stdout_value(self, stdout: str, prefix: str) -> str:
        for line in stdout.splitlines():
            if line.startswith(prefix):
                return line.split(": ", 1)[1].strip()
        raise AssertionError(f"prefix not found in output ({prefix!r}):\n{stdout}")

    def mark_discuss_ready(self) -> None:
        args = [
            "update-current",
            "--task-id",
            self.task_id,
            "--current-gate",
            "Freeze Goal Truth",
            "--allowed-next-action",
            "plan-review",
            "--active-subtask",
            "S1",
            "--event",
            "test setup: discuss ready",
        ]
        for label in [
            "User understanding 95%=YES",
            "Project understanding 95%=YES",
            "Deliverable / effect clarified=YES",
            "Terminal completion definition locked=YES",
            "Phase order / stage boundaries clarified=YES",
            "Approval points clarified=YES",
            "Review-before-action constraints clarified=YES",
            "Source materials identified=YES",
            "Deletion / migration conditions clarified=N/A",
            "Open questions controlled=YES",
        ]:
            args.extend(["--set-bullet", label])
        self.run_cmd(*args)

    def latest_evidence_ref(self) -> str:
        evidence_paths = sorted((self.task_dir / "evidence").glob("*.json"))
        self.assertTrue(evidence_paths, "expected evidence json")
        return str(evidence_paths[-1].relative_to(self.runtime_root))

    def workflow_text(self) -> str:
        return self.workflow_path.read_text(encoding="utf-8")

    def plan_text(self) -> str:
        return self.plan_path.read_text(encoding="utf-8")

    def request_review(self, review_type: str, subtask: str) -> str:
        result = self.run_cmd(
            "request-review",
            "--task-id",
            self.task_id,
            "--review-type",
            review_type,
            "--subtask",
            subtask,
        )
        return self.parse_stdout_value(result.stdout, "- request id: ")

    def test_refresh_pack_freezes_plan_and_plan_review_approves_it(self) -> None:
        self.run_cmd("refresh-pack", "--task-id", self.task_id, "--subtask", "S1")
        plan_text = self.plan_text()
        self.assertIn("status: frozen", plan_text)
        self.assertNotIn(f"updated_at: {OLD_TIMESTAMP}", plan_text)

        plan_request_id = self.request_review("plan", "S1")
        workflow_text = self.workflow_text()
        self.assertIn("Plan review request status: PENDING", workflow_text)
        self.assertIn(f"Plan review request id: {plan_request_id}", workflow_text)
        self.assertIn("Plan review requested subtask: S1", workflow_text)

        result = self.run_cmd("check-gate", "--task-id", self.task_id, "--action", "implement", "--json", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("plan review request is pending", result.stdout)

        self.run_cmd(
            "submit-review",
            "--task-id",
            self.task_id,
            "--subtask",
            "S1",
            "--review-type",
            "plan",
            "--request-id",
            plan_request_id,
            "--reviewer-role",
            "plan_reviewer",
            "--decision",
            "PASS",
            "--plan-ref",
            f".agentdocs/tasks/{self.task_id}/plan.md",
            "--task-requirement",
            f".agentdocs/tasks/{self.task_id}/workflow.md",
            "--world-anchor",
            ".codex/tools/agentctl.py",
            "--material-accessed",
            ".codex/tools/agentctl.py",
            "--coverage-task-requirements",
            "FULL",
            "--coverage-goal-truth",
            "FULL",
            "--coverage-world-truth",
            "FULL",
            "--finding",
            "other:low:test plan review",
        )

        workflow_text = self.workflow_text()
        self.assertIn("Plan review request status: RESOLVED", workflow_text)
        plan_text = self.plan_text()
        self.assertIn("status: approved", plan_text)
        self.assertNotIn(f"updated_at: {OLD_TIMESTAMP}", plan_text)

    def test_submit_review_requires_pending_request(self) -> None:
        self.run_cmd("refresh-pack", "--task-id", self.task_id, "--subtask", "S1")

        result = self.run_cmd(
            "submit-review",
            "--task-id",
            self.task_id,
            "--subtask",
            "S1",
            "--review-type",
            "plan",
            "--request-id",
            "plan-missing-request",
            "--reviewer-role",
            "plan_reviewer",
            "--decision",
            "PASS",
            "--plan-ref",
            f".agentdocs/tasks/{self.task_id}/plan.md",
            "--task-requirement",
            f".agentdocs/tasks/{self.task_id}/workflow.md",
            "--world-anchor",
            ".codex/tools/agentctl.py",
            "--material-accessed",
            ".codex/tools/agentctl.py",
            "--coverage-task-requirements",
            "FULL",
            "--coverage-goal-truth",
            "FULL",
            "--coverage-world-truth",
            "FULL",
            "--finding",
            "other:low:test missing pending request",
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("without a pending review request", result.stderr)

    def test_archive_stays_blocked_until_all_subtasks_have_close_review_pass(self) -> None:
        self.run_cmd("refresh-pack", "--task-id", self.task_id, "--subtask", "S1")
        plan_request_id = self.request_review("plan", "S1")
        self.run_cmd(
            "submit-review",
            "--task-id",
            self.task_id,
            "--subtask",
            "S1",
            "--review-type",
            "plan",
            "--request-id",
            plan_request_id,
            "--reviewer-role",
            "plan_reviewer",
            "--decision",
            "PASS",
            "--plan-ref",
            f".agentdocs/tasks/{self.task_id}/plan.md",
            "--task-requirement",
            f".agentdocs/tasks/{self.task_id}/workflow.md",
            "--world-anchor",
            ".codex/tools/agentctl.py",
            "--material-accessed",
            ".codex/tools/agentctl.py",
            "--coverage-task-requirements",
            "FULL",
            "--coverage-goal-truth",
            "FULL",
            "--coverage-world-truth",
            "FULL",
            "--finding",
            "other:low:test plan review",
        )
        self.run_cmd(
            "update-current",
            "--task-id",
            self.task_id,
            "--current-gate",
            "Implementation",
            "--allowed-next-action",
            "close-review",
            "--active-subtask",
            "S1",
            "--event",
            "test setup: implementation ready for S1",
        )
        self.run_cmd(
            "write-evidence",
            "--task-id",
            self.task_id,
            "--subtask",
            "S1",
            "--kind",
            "test",
            "--result",
            "PASS",
            "--purpose",
            "temporary evidence for S1",
            "--command",
            f"{sys.executable} .codex/tools/agentctl.py validate-refs --task-id {self.task_id}",
            "--cwd",
            ".",
        )
        close_request_id = self.request_review("close", "S1")
        self.run_cmd(
            "submit-review",
            "--task-id",
            self.task_id,
            "--subtask",
            "S1",
            "--review-type",
            "close",
            "--request-id",
            close_request_id,
            "--reviewer-role",
            "close_reviewer",
            "--decision",
            "PASS",
            "--plan-ref",
            f".agentdocs/tasks/{self.task_id}/plan.md",
            "--task-requirement",
            f".agentdocs/tasks/{self.task_id}/workflow.md",
            "--code-path",
            ".codex/tools/agentctl.py",
            "--test",
            ".codex/tools/agentctl.py",
            "--evidence-ref",
            self.latest_evidence_ref(),
            "--material-accessed",
            ".codex/tools/agentctl.py",
            "--material-accessed",
            self.latest_evidence_ref(),
            "--coverage-goal-truth",
            "FULL",
            "--coverage-world-truth",
            "FULL",
            "--finding",
            "other:medium:test close review",
        )

        workflow_text = self.workflow_text()
        self.assertIn("Close review request status: RESOLVED", workflow_text)
        self.assertIn("Latest close review decision: PASS", workflow_text)
        self.assertIn("Close review subtask: S1", workflow_text)
        self.assertIn("Task close-ready: NO", workflow_text)
        self.assertIn("Pending close-review subtasks: S2", workflow_text)

        result = self.run_cmd("check-gate", "--task-id", self.task_id, "--action", "archive", "--json", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("pending S2", result.stdout)


if __name__ == "__main__":
    unittest.main()
