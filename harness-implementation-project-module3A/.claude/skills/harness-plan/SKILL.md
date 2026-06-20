---
name: harness-plan
description: Produce the local repository-grounded technical design and TDD plan for an approved spec, then route it through the persistent reviewer track before implementation.
---

# Harness Plan

The plan is an untracked intermediate artifact at `.harness/work-units/active/<WU-ID>/plan.md`.

1. Read `docs/spec/<WU-ID>.md` and inspect current code, tests, runtime, local rules, and Git/GitHub context.
2. Fill `plan.md` with repository grounding, architecture tradeoffs, a behavior-to-file change map, and bounded implementation slices.
3. For each required evidence claim, include:
   - RED command;
   - expected reason for RED failure;
   - GREEN command;
   - final/broader validation;
   - negative or boundary cases.
4. State assumptions, risks, replan conditions, and reviewer focus items.
5. Do not edit product code before plan review passes.
6. Request plan review with a stable reviewer identity and the real reviewer session when available:

```bash
python3 harness/cli/harnessctl.py request-review --id <WU-ID> --mode plan --reviewer-id <REVIEWER-ID> --reviewer-session <REVIEW-SESSION> --planner-id <PLANNER-ID> --planner-session <PLANNER-SESSION>
```

The same review track and reviewer identity must be reused for close review. A new local plan can be reconstructed from the tracked spec and repository if `.harness` is lost.
