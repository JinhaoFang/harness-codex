# Selective source analysis

The implementation borrows mechanisms, not whole workflows. Each external pattern was retained only where it addresses a demonstrated failure mode.

## Matt Pocock skills

Useful patterns:

- one high-value clarification question at a time;
- recommend an answer instead of only asking open questions;
- inspect the repository when the answer already exists there;
- establish deterministic feedback loops before debugging;
- review a fixed diff rather than a builder narrative.

Adjustment here: grilling produces one tracked spec rather than an expanding family of context documents, and a phase policy prevents product implementation before approval.

## Trellis

Useful patterns:

- explicit Work Unit identity and lifecycle;
- local task/runtime state;
- worktree isolation;
- scripted atomic field updates;
- recoverable context pointers.

Adjustment here: injected workflow never outranks a role's explicit capability. Clarifier/planner cannot write product code, reviewer is read-only, and the active pointer is workspace-namespaced rather than repository-global.

## Superpowers

Useful patterns:

- baseline checks before isolated implementation;
- fresh-context review from spec/diff/code/evidence;
- spec-compliance review before code-quality judgment;
- behavior-first TDD.

Adjustment here: skills are task-routed rather than universally mandatory. The default resident roles are only worker and reviewer.

## Anthropic feature-dev

Useful patterns:

- repository exploration before architecture;
- explicit clarification;
- compare design alternatives;
- user approval before implementation.

Adjustment here: the cognitive workflow is backed by mechanical phase/write boundaries and a durable tracked spec. Large feature work must be decomposed rather than forcing every task through one long context.

## gstack

Useful patterns:

- real runtime/browser evidence;
- review freshness;
- command/tool auditability;
- strong GitHub shipping workflow.

Adjustment here: reviewer, fixer and integrator capabilities remain separate, and runtime identity includes workspace/worktree rather than only repository name.

## Bun

Useful patterns:

- Git, commits, PRs, CI and human review remain the core development process;
- tests must fail for the old behavior and pass for the intended implementation;
- assertions and test setup must be load-bearing;
- adversarial review can return patches/findings without taking branch ownership.

Adjustment here: RED and GREEN are captured by `harnessctl verify`, but the worker/reviewer must still inspect why RED failed. An exit code alone cannot prove test quality.

## Codex Goals

Useful patterns:

- explicit success, validation, checkpoint, budget and blocked conditions for long-running work;
- durable progress separate from conversational memory;
- terminal failures become visible blocked states instead of endless retries.

Adjustment here: a Goal is generated only after spec and plan approval and remains thread-scoped. Loss of a Goal is recoverable from the tracked spec and repository. Goal completion is never evidence or acceptance authority.

## Deliberately omitted

The default profile omits generic waiver machinery, tracked plan/state ledgers, stop-blocking hooks, universal skill checks, issue schedulers, resident planner/explorer/monitor agents and reviewer auto-fix behavior. None had enough demonstrated benefit for the maintenance and authority cost in this implementation.
