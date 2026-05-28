# Risk Gates

| Risk | Typical work | Required gates |
|---|---|---|
| trivial | comment, copy, small docs | self-check; evidence note if helpful |
| low | local bugfix or low-risk tests | Work Unit note; fresh evidence; scope self-check |
| medium | multi-file or user-visible behavior | Work Unit Contract; evidence receipts; close review; handoff |
| high | auth, permissions, billing, migration, security, broad refactor | contract risk section; rollback path; evidence receipts; independent review or human gate |
| critical | production data, external customer impact, compliance, irreversible operation | locked contract; blast radius; rollback proof; mandatory human approval; audit trail |

## Skipped evidence

Skipped evidence must include:

- skipped requirement;
- reason;
- replacement evidence;
- risk impact;
- owner or approver when risk is accepted;
- expiry or revisit condition.

Skipped checks must never be recorded as pass.

## High-risk triggers

Escalate when touching:

- production database operations;
- tenant isolation, RLS, auth, permission logic;
- secrets or credential rotation;
- billing/payment behavior;
- migrations, deployments, rollback paths;
- broad deletion or generated file replacement;
- customer-impacting behavior;
- privacy, legal, compliance, or audit surfaces.
