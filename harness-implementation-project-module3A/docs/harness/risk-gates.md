# Risk gates

The default harness keeps one lifecycle but strengthens acceptance by risk.

| Risk | Minimum treatment |
|---|---|
| trivial | short spec may be enough; targeted self-check |
| low | approved spec, bounded diff, controller-observed evidence |
| medium | technical plan, plan review, separate worker, close review citing evidence |
| high | medium gates plus verified session separation, rollback design and accountable human gate for external effects |
| critical | do not rely on this local harness alone; require organization policy, protected environment, audit trail and explicit human authorization |

## Missing evidence

A missing required check is recorded with `record-skipped` and blocks. There is no generic waiver command in this profile because it had no demonstrated use and created an unsafe alternative completion path.

When the original evidence requirement is genuinely wrong, update the tracked spec, explain the tradeoff, obtain human reapproval, rebuild the plan as needed, and produce the new evidence. For urgent production risk acceptance, use the organization's existing incident/change-management approval rather than inventing an unauthenticated local waiver.

## Escalation triggers

Escalate before touching production data, tenant isolation, auth/permissions, credentials, billing, migrations, deployments, broad deletion, irreversible external effects, privacy/compliance, or customer-impacting operations.
