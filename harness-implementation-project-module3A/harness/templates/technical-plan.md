# Technical Plan: {{id}} — {{title}}

> Local, ignored intermediate artifact. The marked JSON block is controller-readable; reviewer notes outside it are optional context.

<!-- harness:execution-plan:start -->
```json
{
  "schema_version": "harness.execution_plan.v2",
  "work_unit_id": "{{id}}",
  "title": "{{title}}",
  "repository_grounding": [
    "TBD: Code, tests, runtime behavior, and local rules inspected."
  ],
  "architecture_and_tradeoffs": "TBD: Chosen design, rejected alternatives, and why this is the smallest appropriate change.",
  "change_map": [
    {
      "path": "TBD",
      "change": "TBD",
      "reason": "TBD"
    }
  ],
  "behavior_slices": [
    {
      "id": "B1",
      "claim_ref": "EV1",
      "behavior": "TBD",
      "test_paths": [
        "TBD"
      ],
      "oracle": "TBD: Explain why this assertion fails on old behavior and passes only on the required behavior.",
      "red": {
        "check_id": "check.ev1",
        "expected_failure": {
          "kind": "exit_nonzero",
          "combined_regex": [
            "TBD"
          ]
        }
      },
      "green": {
        "check_id": "check.ev1"
      },
      "allowed_paths": [
        "TBD"
      ]
    }
  ],
  "acceptance_evidence": [
    {
      "claim_ref": "EV1",
      "check_id": "check.ev1",
      "level": "functional",
      "justification": "TBD: Explain why this final check proves the user-visible outcome rather than only an internal implementation detail."
    }
  ],
  "verification_notes": [
    "TBD"
  ],
  "risks_and_replan_conditions": [
    "TBD"
  ],
  "reviewer_focus": [
    "TBD"
  ]
}
```
<!-- harness:execution-plan:end -->

## Reviewer notes

Add code anchors, rejected alternatives, and implementation discoveries here.
