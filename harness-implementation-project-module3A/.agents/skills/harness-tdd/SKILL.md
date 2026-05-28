---
name: harness-tdd
description: Apply behavior-first test-driven development to a bounded coding Work Unit. Use for feature implementation, bug fixes, behavior changes, public interface/schema changes, lifecycle state changes, error handling, permissions, or any task whose correctness should be proven with red/green/refactor evidence.
---

# Harness TDD

Drive implementation through one behavior slice at a time. Tests are evidence candidates; they do not replace final evidence receipts or review.

## Inputs required

- Work Unit ID and contract.
- Acceptance criterion or behavior claim.
- Target verification command.
- Allowed test and implementation paths from the write boundary.

If any required input is missing, stop and ask for the missing field or return to `harness-clarify` / `harness-spec`.

## Cycle

1. **RED**: write one test for one observable behavior through a public interface.
2. Run the targeted command and confirm the test fails for the expected reason.
3. **GREEN**: implement the minimum vertical slice needed for that test.
4. Re-run the same command and confirm it passes.
5. Run broader verification required by the Work Unit when relevant.
6. **REFACTOR** only while green; re-run verification after each meaningful refactor.
7. Record evidence with `harness-evidence` or `harnessctl evidence`.

## Test selection

- Bug fix: first test reproduces the bug.
- Public behavior: behavior or integration test through stable interface.
- API / CLI / schema: contract test for externally consumed shape.
- Error or permission change: negative/error-path tests.
- State machine or lifecycle: state-transition tests.
- Multi-component user flow: e2e or equivalent runtime behavior check.

## Hard rules

- One test slice at a time; do not bulk-write imagined future tests.
- Prefer state/behavior assertions over internal call-count or private-method assertions.
- Do not refactor while RED.
- Do not make Green changes outside the Work Unit boundary.
- Do not call skipped tests pass.
- If the planned test cannot be made real, stop and update the evidence plan or request a waiver.
