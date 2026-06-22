# Codex Native Subagent Protocol

This playbook defines the Codex-specific delivery protocol when the parent Codex session uses native subagents instead of controller-managed `dispatch-review` / `dispatch-worker`.

The controller remains lifecycle authority. Native subagents own execution turns; `harnessctl` owns session binding, review requests/verdicts, evidence, and final gates.

## Roles

| Role | Native agent type | Sandbox | Authority |
|---|---|---|---|
| Parent conductor | main Codex session | workspace-write | route work, spawn/resume agents, call controller lifecycle commands |
| Plan/Close reviewer | `pr_explorer` or project reviewer agent | read-only | inspect repo truth and submit review verdicts only |
| Worker | `worker` or project worker agent | workspace-write | implement plan, run `harnessctl verify`, never submit review verdicts |

## Non-negotiable rules

- The parent session never treats a spawned agent's narrative as acceptance truth.
- Reviewer is read-only and must never edit implementation files.
- Worker must not submit review verdicts.
- Plan Review and Close Review must reuse the same logical reviewer session unless `reviewer-takeover` is explicitly recorded.
- Fresh pass evidence must still come from `harnessctl verify`.

## Session binding

Native Codex subagents are trusted by the controller only after their real session is bound to the active Work Unit.

Preferred path:

1. Spawn or resume the native subagent.
2. Let the `SubagentStart` hook persist the observed binding automatically.
3. If the hook did not persist the binding, call:

```bash
harnessctl bind-session \
  --id <WU-ID> \
  --role <reviewer|worker> \
  --platform codex \
  --session-id <SUBAGENT-SESSION-ID> \
  --agent-id <OPTIONAL-AGENT-ID> \
  --agent-type <pr_explorer|worker|custom-agent-name>
```

Use `bind-session` before `request-review`, `start-work`, or `resume-work` whenever the controller cannot already resolve the platform-observed role session.

## Parent conductor sequence

1. Clarify and approve the tracked Spec.
2. Complete the local plan.
3. Run:

```bash
harnessctl check --id <WU-ID> --gate plan --strict
harnessctl route --id <WU-ID> --platform codex
```

4. Spawn or resume the native reviewer subagent for Plan Review.
5. Ensure the reviewer session is bound.
6. Create the review request:

```bash
harnessctl request-review --id <WU-ID> --mode plan \
  --reviewer-id <REVIEWER-ID> --reviewer-session <LOGICAL-REVIEWER-SESSION> \
  --planner-id <PLANNER-ID> --planner-session <PLANNER-SESSION>
```

7. Wait for the reviewer result, then submit the verdict from that same reviewer session.
8. If plan review passes, spawn or resume the worker subagent.
9. Ensure the worker session is bound, then start work:

```bash
harnessctl start-work --id <WU-ID> \
  --builder-id <WORKER-ID> --builder-session <LOGICAL-WORKER-SESSION>
```

10. Let the worker drive RED/GREEN/final evidence through the controller, following the plan's `acceptance_evidence` levels for final claim proof.
11. When final evidence is fresh, route again:

```bash
harnessctl route --id <WU-ID> --platform codex
```

12. Resume the same reviewer subagent for Close Review.
13. Submit close review from the same logical reviewer session.
14. Run:

```bash
harnessctl finalize-check --id <WU-ID> --strict
```

## Reviewer protocol

### Plan Review

1. Read the tracked Spec, local plan, current code/tests/runtime, and relevant diff.
2. Re-ground from repository truth, not planner narrative.
3. Return only findings/rework/decision.
4. Submit:

```bash
harnessctl submit-review --id <WU-ID> --request-id <RR> --mode plan \
  --decision <PASS|CHANGES_REQUESTED|REJECTED|BLOCKED|NEEDS_HUMAN_GATE> \
  --reviewer-id <REVIEWER-ID> --reviewer-session <LOGICAL-REVIEWER-SESSION> \
  --finding "<finding>" --required-rework "<rework>"
```

### Close Review

1. Resume the exact same reviewer logical session from Plan Review.
2. Re-read current code, diff, receipts, and tests.
3. Do not defend the old plan; validate the current result.
4. Submit:

```bash
harnessctl submit-review --id <WU-ID> --request-id <RR> --mode close \
  --decision <PASS|CHANGES_REQUESTED|REJECTED|BLOCKED|NEEDS_HUMAN_GATE> \
  --reviewer-id <REVIEWER-ID> --reviewer-session <LOGICAL-REVIEWER-SESSION> \
  --evidence-ref <RECEIPT-ID>
```

If the original reviewer session is unrecoverable, stop and use `reviewer-takeover`. Never silently switch reviewer sessions.

## Worker protocol

1. Read the approved Spec and local plan.
2. Stay inside the approved write boundary.
3. Run behavior-first TDD through the controller:

```bash
harnessctl verify --id <WU-ID> --claim <EV-ID> --phase red
harnessctl verify --id <WU-ID> --claim <EV-ID> --phase green
harnessctl verify --id <WU-ID> --claim <EV-ID> --phase final
```

4. Do not edit the approved Spec or plan during implementation.
5. Do not submit review verdicts.
6. If the worker session changes, bind it again before `resume-work`.

## Multi-agent tool usage pattern

Recommended parent-session pattern:

1. `spawn_agent` for the reviewer or worker when no usable session exists.
2. `resume_agent` when the prior native agent was intentionally closed but should continue.
3. `send_input` to continue or redirect a still-open agent.
4. `wait_agent` whenever the next lifecycle step depends on that agent's result. In normal delivery, this means waiting for the reviewer before submitting a verdict and waiting for the worker before routing to Close Review. Timeout sets 30 mins by default！
5. `close_agent` once the agent is done and no longer needed.

Prefer one long-lived reviewer agent per Work Unit and one worker agent per active implementation stream. Avoid spawning multiple write-capable workers for the same file set.

## Failure handling

- Missing or conflicting reviewer session: stop and fix binding before review commands.
- Missing or conflicting worker session: stop and fix binding before `start-work` or `resume-work`.
- Reviewer session changed after Plan Review: use `reviewer-takeover`.
- Worker changes after evidence or close review: rerun fresh evidence and review.
- Hook failed to bind the session: use `bind-session` explicitly rather than guessing.
