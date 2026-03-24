---
name: tdd
description: use for every code-bearing development task or subtask so implementation happens test-first via red-green-refactor, without turning TDD into a runtime gate or binding it to the stage definition itself.
---

# tdd

Use TDD as an implementation method overlay, not as task truth.

## What fits fusion

- TDD is a method, not a stage and not a gate.
- TDD must not redefine Goal truth, Process truth, review verdicts, or completion truth.
- `plan.md`, `workflow.md`, subtask pack, reviews, and evidence remain the source of task state.
- For code-bearing development work, TDD is mandatory as the method layer.
- If TDD exposes a plan or interface problem, return to planning instead of silently drifting the scope.

## Use when

- the task changes observable behavior and that behavior can be locked with a real test
- any code-bearing development subtask enters implementation
- a bug fix needs a regression test before code changes
- the public interface and target behavior are already clear enough from the plan, pack, or current bug reproduction

## Do not use when

- the work is primarily migration, architecture, documentation, repo surgery, UI exploration, or operations work where a red test is not the right leading signal
- the interface or behavior is still ambiguous at Goal truth level
- the only possible tests would be tightly coupled to implementation details
- inventing a new test harness would itself exceed the approved scope

## Read first

1. active subtask pack
2. relevant `plan.md` acceptance / verification / subtask `Verify`
3. current `workflow.md`
4. the minimum code and tests needed for the target behavior

## Core principles

- Test behavior through public interfaces, not implementation details.
- Prefer integration-style tests that survive internal refactors.
- Write vertical slices, not horizontal batches.
- Mock only at system boundaries.
- Refactor only after the current slice is green.

## Anti-pattern to avoid

Do not write "all tests first, then all code."

That creates tests for imagined structure rather than verified behavior.
Use one tracer bullet at a time:

```text
RED   -> write one failing behavior test
GREEN -> write the minimum code to pass it
REFACTOR -> simplify only after green
```

## Test design rules

- Test WHAT the caller or user observes, not HOW internals collaborate.
- Prefer public API, command, request, or behavior checks over private helpers.
- One test should lock one behavior slice.
- A test that breaks on harmless refactor is probably too coupled.
- If you must choose, prefer fewer high-signal behavior tests over many brittle implementation tests.

## Mocking rules

- Mock only system boundaries: external APIs, time, randomness, filesystem when necessary, and sometimes the database when a real test database is not practical.
- Do not mock your own modules, internal collaborators, or private control flow.
- If mocking your own code seems necessary, the interface is probably wrong or the slice is too low-level.

## Interface pressure from TDD

When TDD pushes on design, prefer interfaces that are easier to verify:

- accept dependencies instead of constructing them internally
- return explicit results instead of hiding everything in side effects
- keep the public surface small
- make boundary adapters narrow and concrete

If those changes exceed the frozen write boundary or change approved behavior, reopen planning instead of "sneaking in" interface redesign.

## Recommended loop

1. Pick the next observable behavior from the subtask goal, `Acceptance`, `Verify`, or a concrete bug reproduction.
2. RED: write the smallest failing test that proves the behavior is not yet true.
3. GREEN: implement the minimum code needed to make that single test pass.
4. RE-RUN: run the real verification command, not only the new test.
5. REFACTOR: remove duplication and deepen modules only after green.
6. RECORD: capture meaningful verification as evidence.

## Required test shape

Every code-bearing development subtask must have:

- at least one real red-green behavior slice through a public interface
- a passing rerun of the same behavior after the implementation change
- the broader verification command from `Verify`, when one exists in the pack or plan
- a regression test first when the task is fixing a bug

Use this decision pattern:

```text
code-bearing development task
    |
    +-- bug fix? -------------------------- yes -> regression test is mandatory
    |
    +-- public behavior changes? ---------- yes -> behavior/integration test is mandatory
    |
    +-- interface or schema changes? ------ yes -> add contract coverage
    |
    +-- error handling or edges changed? -- yes -> add error/boundary coverage
    |
    `-- user-visible multi-step flow? ----- yes -> add e2e/behavior check
```

## Test types by scenario

- Behavior / integration tests: default first choice. Prefer these as the primary TDD proof because they exercise real code paths through public APIs, commands, requests, jobs, or service facades.
- Regression tests: mandatory for bug fixes. The first red test should reproduce the bug through the closest stable public interface.
- Contract / schema tests: required when the task changes API payloads, CLI output contracts, file formats, serialization, event payloads, or other externally consumed shapes.
- Error-path tests: required when the task changes validation, retries, fallback logic, exception mapping, permission checks, or dependency-failure behavior.
- Boundary / edge-case tests: required when logic depends on empty input, duplicates, thresholds, ordering, idempotency, pagination, time windows, or retry counts.
- State-transition tests: required when the task changes lifecycle state, workflow state, status machines, reopen/archive semantics, or rollback behavior.
- E2E / end-to-end behavior checks: required when completion depends on multiple components or a user-visible flow rather than one isolated module boundary.
- Pure domain unit tests: acceptable when behavior is naturally expressed at a stable module boundary such as a pure function or deep domain module, but they do not replace higher-level behavior coverage when a public interface exists.
- Snapshot tests: secondary signal only. They may detect broad output drift, but they are not the primary TDD proof of correctness.

## Per-cycle checklist

```text
[ ] test describes behavior, not implementation
[ ] test uses a public interface
[ ] code is minimal for this slice
[ ] no speculative abstractions were added
[ ] current verification command is known
```

## Evidence and handoff

- Passing tests do not replace evidence capture or close review.
- Record both the red proof and the green proof when practical, so later review can confirm the TDD path instead of inferring it.
- After a meaningful green state, use `$evidence-capture` or the controller directly.
- When implementation is ready, return to the implementation-stage handoff in `$execute-subtask`.

## Escalate when

- the planned `Verify` cannot be realized as a real test or executable behavior check
- you need to change a public interface that was not frozen in the plan
- the only test path depends on private internals or brittle call-order assertions
- a failing test reveals the real requirement is different from the approved goal truth

## Do not

- do not treat TDD as mandatory for non-development subtasks
- do not let TDD replace planning, review, or evidence
- do not bulk-write tests for future slices
- do not let low-level unit tests replace required behavior, contract, or e2e coverage when the task risk lives above that layer
- do not anchor tests to private methods, call counts, or internal collaborator wiring
- do not refactor while RED
