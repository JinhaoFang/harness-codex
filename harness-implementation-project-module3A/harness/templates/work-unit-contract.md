# Work Unit Contract: {{id}}

```yaml
id: "{{id}}"
title: "{{title}}"
type: "{{type}}"
risk: "{{risk}}"
```

## Intent

TBD: What problem are we solving? Include the user's intent, not an implementation guess.

## Expected Outcome

- TBD: Observable result after this Work Unit is done.

## Non-goals

- TBD: Explicitly out of scope.

## Scope

### Likely changed areas

- TBD

### Write boundary

- TBD

### Out of bounds

- TBD
- Harness runtime state (`.harness/config.json`, `.harness/current`, and `.harness/work-units/**`) is controller-managed. Do not treat it as product scope unless this Work Unit explicitly changes harness behavior.

## Required evidence

- id: EV1
  claim: TBD
  command: TBD
  required_for_completion: true

## Stop conditions

### Success

- TBD

### Blocked

- Ambiguous intent that changes product behavior.
- Need to cross an out-of-bounds path.
- Required evidence cannot be produced and no waiver is available.

## Clarification record

- user_confirmed: no
- repo_grounded: no
- user_intent_confidence: TBD
- project_reality_confidence: TBD
- key_decisions: TBD
- remaining_assumptions: TBD

## Open questions

- TBD

## Context pointers

- TBD

## Risk notes

- TBD
