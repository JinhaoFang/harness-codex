---
name: contract-artifacts
description: use when codex needs durable business, api, or ui contract documents that should outlive a single task plan and remain reusable across tasks. do not use for routine task-local planning; `plan.md` stays the goal truth for the current task.
---

# contract-artifacts

Create long-lived contract docs only when the repo needs them.

## Purpose
Use this skill when a business/API/UI contract should be versioned and reviewed independently from one task.

## Read first
- current `plan.md`
- current `workflow.md`
- the minimum code/tests/docs that prove the contract is real
- `docs/contracts/README.md`

## Decision rule
Create a durable contract artifact only if **at least one** is true:
- multiple future tasks will depend on it
- multiple reviewers or teams need a stable reference
- the contract should remain meaningful after the current task closes
- the plan would become bloated by carrying this detail forever

Otherwise, keep the information in `plan.md` only.

## Output locations
- business/product contract -> `docs/contracts/prd/<feature>.md`
- api/interface contract -> `docs/contracts/api/<feature>.md`
- ui/interaction contract -> `docs/contracts/ui/<feature>.md`

## Writing rules
- keep the document durable and reusable
- record contracts, not workflow history
- reference plan/task ids instead of copying the whole plan
- prefer minimal templates from `docs/contracts/templates/*`
- do not duplicate review verdicts, evidence logs, or execution steps

## Do not
- do not make contract docs mandatory for every task
- do not copy `plan.md` verbatim into `docs/contracts/*`
- do not store process truth here
