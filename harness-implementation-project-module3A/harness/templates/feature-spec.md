# Feature Spec: {{id}} — {{title}}

> Tracked product specification. The marked JSON block is the machine-readable Work Unit contract.

<!-- harness:work-unit-contract:start -->
```json
{
  "schema_version": "harness.work_unit_contract.v3",
  "id": "{{id}}",
  "title": "{{title}}",
  "type": "{{type}}",
  "risk": "{{risk}}",
  "approval": {
    "status": "draft",
    "approved_by": "",
    "approved_at": "",
    "approval_ref": "",
    "approved_content_hash": ""
  },
  "intent": "TBD: Describe the user or product problem without assuming the implementation.",
  "expected_outcomes": [
    "TBD: State the externally observable result."
  ],
  "non_goals": [
    "TBD: State what this Work Unit deliberately will not do."
  ],
  "scope": {
    "likely_changed_areas": [
      "app/**"
    ],
    "write_boundary": [
      "app/**",
      "components/**",
      "lib/**",
      "tests/**",
      "package.json"
    ],
    "out_of_bounds": [
      ".harness/**",
      ".git/**",
      "secrets/**"
    ]
  },
  "required_evidence": [
    {
      "id": "EV1",
      "claim": "TBD: State what must be proven.",
      "check_id": "check.ev1"
    }
  ],
  "verification": {
    "checks": {
      "check.ev1": {
        "runner": "exec",
        "argv": [
          "TBD"
        ],
        "cwd": ".",
        "timeout_seconds": 1800
      }
    }
  },
  "stop_conditions": {
    "success": [
      "TBD"
    ],
    "blocked": [
      "Material product intent remains ambiguous.",
      "Implementation must cross an out-of-bounds path.",
      "Required evidence cannot be produced without changing the approved spec."
    ]
  },
  "clarification": {
    "user_confirmed": false,
    "repo_grounded": false,
    "key_decisions": [],
    "remaining_assumptions": [
      "TBD"
    ]
  },
  "open_questions": [
    "TBD"
  ],
  "context_pointers": [
    "TBD"
  ],
  "delivery": {
    "issue": "",
    "branch": "",
    "pull_request": "",
    "required_checks": []
  },
  "risk_notes": [
    "TBD"
  ]
}
```
<!-- harness:work-unit-contract:end -->

## Product notes

Add walkthrough notes, examples, rejected alternatives, and rationale here. The contract block above remains authoritative.

`scope.likely_changed_areas` may be a high-level path hint, but `scope.write_boundary` and `scope.out_of_bounds` must be repo-relative path/glob patterns that the controller can match mechanically against changed files.
