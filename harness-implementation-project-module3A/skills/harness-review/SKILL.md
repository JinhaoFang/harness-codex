---
name: harness-review
description: Perform plan and close review on one persistent review track, using the tracked spec, local plan, current repository/diff, tests, and controller evidence rather than builder narrative. Use before build and before integration.
---

# Harness Review

Reviewer is read-only. The builder must fix findings; the reviewer does not silently patch the implementation.

## Plan review

Read the tracked spec, local plan, current code/tests/runtime, scope, and risk. Reject ungrounded architecture, missing behavior coverage, weak failure oracles, or hidden scope expansion.

```bash
python3 harness/cli/harnessctl.py request-review --id <WU-ID> --mode plan --reviewer-id <REVIEWER-ID> --reviewer-session <REVIEW-SESSION> --planner-id <PLANNER-ID> --planner-session <PLANNER-SESSION>
python3 harness/cli/harnessctl.py submit-review --id <WU-ID> --request-id <REQUEST> --mode plan --reviewer-id <REVIEWER-ID> --reviewer-session <REVIEW-SESSION> --decision PASS
```

## Close review

Reuse the same reviewer identity and review track. Preserve prior risks and assumptions, but re-ground from current code, diff, tests, and evidence to avoid defending the original plan.

```bash
python3 harness/cli/harnessctl.py request-review --id <WU-ID> --mode close --reviewer-id <REVIEWER-ID> --reviewer-session <SESSION>
python3 harness/cli/harnessctl.py submit-review --id <WU-ID> --request-id <REQUEST> --mode close --reviewer-id <REVIEWER-ID> --reviewer-session <SESSION> --decision PASS
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate review --strict
```

Use `CHANGES_REQUESTED`, `BLOCKED`, or `NEEDS_HUMAN_GATE` honestly. High/critical close review requires a distinct reviewer session or human gate.
