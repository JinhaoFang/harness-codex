---
name: harness-review
description: Perform plan, close, close-addendum, publication, risk, security, or architecture review from fresh inputs. Use before implementation for plan sufficiency, before completion for close review, when evidence is skipped, when scope drift is suspected, or when high/critical risk requires independent review or human gate.
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

The reviewer should not stop to ask the user by default. If inputs are insufficient, return `CHANGES_REQUESTED`, `BLOCKED`, or `NEEDS_HUMAN_GATE` with the exact missing artifact or decision.

For medium or higher risk, running requires passing plan review. For high or critical risk, use independent review or human gate.

## Close review checks

Before acceptance, check:

- Scope matches contract.
- Required evidence is fresh, claim-relative, and covers the current diff or equivalent artifact.
- Skipped checks have scoped waiver or required human gate.
- Risk boundary was not crossed without approval.
- Tests are behavior-oriented and cover the risk surface.
- Findings are concrete and actionable.
- Passing close review cites evidence receipt IDs for the claims it judged. It does not need to be rerun merely because an equivalent receipt was refreshed later and implementation/scope/risk did not change.

## Review validity surface

Review validity is about the judgment surface, not latest artifact ids. Do not request a reviewer only because one of these changed:

- refreshed evidence receipt IDs for already-reviewed claims;
- commit creation, squash, or rebase where implementation diff is equivalent;
- CI rerun or command log path changes;
- handoff, archive, state, receipt, or review-request files under `.harness/`;
- GitHub issue/PR/branch metadata after publication review;
- generated lifecycle summaries or final notes.

Request full close review when implementation, scope, risk, success criteria, acceptance semantics, dependency/runtime surface, or test expectations changed. Request publication review for GitHub issue/PR/branch publication. Request close-addendum only when a prior close review remains valid for implementation but a lightweight non-publication acceptance judgment changed and controller review gate is blocking for that reason.

Before requesting close-addendum, run `harnessctl check --gate review --strict` or `harnessctl finalize-check --strict`. Only request review when `finalize-check` reports `review_required: true`; do not request review when it reports `rerun_evidence_required: false` and `do_not_request_review: true`.

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
python3 harness/cli/harnessctl.py finalize-check --id <WU-ID> --strict
```

The builder must not write the close review verdict for its own work. A medium-or-higher risk close review must cite an evidence snapshot or receipt at least once, but it does not need to cite every required claim or every refreshed receipt ID.


Close-addendum review, only when review gate blocks for a lightweight acceptance judgment change. Do not use this for receipt refresh, commit materialization, publication metadata, or lifecycle updates:

```bash
python3 harness/cli/harnessctl.py request-review --id <WU-ID> --mode close-addendum --reviewer-role reviewer-agent
python3 harness/cli/harnessctl.py submit-review --id <WU-ID> --mode close-addendum --decision PASS --reviewer-role reviewer-agent --independence-level fresh_context --evidence-ref <JUDGMENT-AFFECTED-EV-RECEIPT-ID>
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate review --strict
```

Publication review:

```bash
python3 harness/cli/harnessctl.py request-review --id <WU-ID> --mode publication --reviewer-role reviewer-agent
python3 harness/cli/harnessctl.py submit-review --id <WU-ID> --mode publication --decision PASS --reviewer-role reviewer-agent --independence-level fresh_context --evidence-ref <PUBLICATION-EV-RECEIPT-ID>
```
