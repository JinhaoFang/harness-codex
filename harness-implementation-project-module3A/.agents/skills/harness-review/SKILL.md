---
name: harness-review
description: Perform plan, close, risk, security, or architecture review from fresh inputs. Use before implementation for plan sufficiency, before completion for close review, when evidence is skipped, when scope drift is suspected, or when high/critical risk requires independent review or human gate.
---

# Harness Review

Review judges sufficiency; it does not manufacture evidence.

## Primary inputs

Use only these as review truth:

- Work Unit Contract (`contract.md`), read directly;
- proposed execution plan for plan review;
- current diff for close review;
- relevant code/tests/runtime surfaces;
- evidence receipts;
- waivers;
- scope and risk boundary.

Do not use builder narrative, chat transcript, compressed briefing, or unverified summary as the primary input.

## Plan review checks

Before implementation, check:

- Contract is locked and spec gate passed.
- Intent, expected outcome, non-goals, scope, required evidence, and stop conditions are concrete.
- Open questions are resolved or explicitly escalated.
- Proposed plan is grounded in current repo truth and context pointers.
- Plan does not cross out-of-bounds paths.
- Plan has verification steps tied to required evidence.
- Findings are concrete and actionable.

For medium or higher risk, running requires passing plan review. For high or critical risk, use independent review or human gate.

## Close review checks

Before acceptance, check:

- Scope matches contract.
- Required evidence is fresh, claim-relative, and covers the current diff or equivalent artifact.
- Skipped checks have scoped waiver or required human gate.
- Risk boundary was not crossed without approval.
- Tests are behavior-oriented and cover the risk surface.
- Findings are concrete and actionable.
- Passing close review cites the fresh evidence receipt IDs that support every required evidence claim for medium or higher risk.

## Commands

Plan review:

```bash
python3 harness/cli/harnessctl.py request-review --id <WU-ID> --mode plan --reviewer-role reviewer-agent
python3 harness/cli/harnessctl.py submit-review --id <WU-ID> --mode plan --decision PASS --reviewer-role reviewer-agent --independence-level fresh_context
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate plan-review --strict
```

Close review:

```bash
python3 harness/cli/harnessctl.py request-review --id <WU-ID> --mode close --reviewer-role reviewer-agent
python3 harness/cli/harnessctl.py submit-review --id <WU-ID> --mode close --decision PASS --reviewer-role reviewer-agent --independence-level fresh_context --evidence-ref <EV-RECEIPT-ID>
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate review --strict
```

The builder must not write the close review verdict for its own work. A PASS without `--evidence-ref <EV-RECEIPT-ID>` is not acceptable for medium or higher risk close review.
