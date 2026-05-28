# Work Unit Contract: WU-EXAMPLE

```yaml
id: "WU-EXAMPLE"
title: "Fix login redirect after expired session"
type: "bugfix"
risk: "medium"
status: "specified"
```

## Intent

When a user with an expired session attempts to access a protected route, redirect them to login and return them to the original route after authentication.

## Expected Outcome

- Expired sessions redirect to `/login?next=<original-path>`.
- Successful re-login returns to the original protected route.
- Existing valid-session behavior is unchanged.

## Non-goals

- Do not redesign the auth provider.
- Do not change billing or permissions logic.

## Scope

### Likely changed areas

- src/auth/**
- tests/auth/**

### Write boundary

- src/auth/**
- tests/auth/**

### Out of bounds

- src/billing/**
- infra/**
- migrations/**

## Required evidence

- id: EV1
  claim: expired session redirect behavior is covered by regression test
  command: pytest tests/auth/test_redirect.py
  required_for_completion: true
- id: EV2
  claim: existing auth behavior still passes
  command: pytest tests/auth
  required_for_completion: true

## Stop conditions

### Success

- EV1 and EV2 pass after final diff.
- Close review passes.

### Blocked

- Need to touch billing/permission logic.
- Existing tests conflict with product intent.

## Open questions

- none

## Context pointers

- src/auth/session.py
- tests/auth/test_redirect.py
- docs/auth-flow.md

## Risk notes

Medium risk because auth behavior is user-visible, but no permission model change is intended.
