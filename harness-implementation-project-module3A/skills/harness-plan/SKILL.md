---
name: harness-plan
description: Produce the local repository-grounded technical design and behavior-first TDD plan for an approved spec, then continue automatically into independent Plan Review.
---

# Harness Plan

The plan is an ignored intermediate artifact at `.harness/work-units/active/<WU-ID>/plan.md`.

1. Read the approved `docs/spec/<WU-ID>.md` and inspect current code, tests, runtime, local rules, and Git/GitHub context.
2. Define the smallest architecture and change map that satisfies the approved behavior; record rejected broader alternatives.
3. Cover every required evidence claim with one or more behavior slices containing test paths, observable oracle, RED check, expected RED reason, GREEN check, allowed paths, risks, and replan conditions.
4. Explicitly define `acceptance_evidence` for the final claim validation. State which level proves the user-visible result for this task: `unit`, `integration`, `functional`, `e2e`, `acceptance`, `smoke`, `build`, `lint`, `typecheck`, or `runtime`.
5. Do not treat static or internal-only checks as automatically sufficient. If the user-facing outcome needs browser/page/interaction proof, the final acceptance evidence must say so.
6. Do not edit product code before Plan Review passes. The plan may not rewrite intent or expand scope.
7. Run the plan gate, then continue without pausing for an operator handoff. For Codex, use native reviewer orchestration; for Claude/manual adapter flows, continue with the controller dispatcher:

```bash
harnessctl check --id <WU-ID> --gate plan --strict
harnessctl route --id <WU-ID> --platform codex
harnessctl advance \
  --id <WU-ID> --platform claude \
  --reviewer-id <REVIEWER-ID> \
  --planner-id <PLANNER-ID> --planner-session <PLANNER-SESSION> \
  --builder-id <WORKER-ID>
```

Codex must stop rather than guess on ambiguity, scope amendment, risk/human gate, missing evidence, or requested rework, and resume the same logical Reviewer session for Close Review. Claude's `advance` path preserves the same stop conditions. When using Codex, follow `docs/harness/codex-native-subagents.md` for the exact parent/reviewer/worker sequence.
