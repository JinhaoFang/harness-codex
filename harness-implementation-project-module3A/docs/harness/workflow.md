# Workflow Contract

## 1. Clarify

The agent should not start implementation while essential intent, scope, success, or risk questions are unresolved. Ask the smallest number of questions needed to freeze the Work Unit.

If the task is time-sensitive or the user asks for immediate action, proceed with explicit assumptions and mark them in the contract.

## 2. Specify

Create or update a Work Unit Contract. The contract is the shared truth for user intent and scope. Execution plans may change; the contract should not drift silently.

Gate:

```bash
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate spec --strict
python3 harness/cli/harnessctl.py lock --id <WU-ID> --status ready
```

For non-trivial work, unresolved open questions, placeholders, missing write boundary, missing required evidence, or missing stop conditions block lock/readiness. After lock, changes to intent, scope, risk, required evidence, success criteria, or stop conditions must be recorded with `harnessctl amend`; otherwise readiness/running transitions are blocked. Classify the amendment impact when recording it: `context_only`, `collaboration_only`, `evidence_only`, `success_criteria`, `scope_or_risk`, or `implementation`. Re-run plan review only when the amendment changes the plan, implementation boundary, risk, success criteria, or user intent. Evidence-only and collaboration-only amendments should not invalidate implementation evidence or force full plan review when implementation content is unchanged.

## 3. Route context

Use the project map first. Then read only the docs, code, tests, ADRs, and runtime surfaces that are relevant to the contract.

Record context pointers in the contract or handoff when they materially affect implementation.

## 4. Implement with TDD discipline

Use behavior-first TDD for production changes:

1. Write or identify a failing regression or behavior test.
2. Run it and record RED evidence when it is useful.
3. Implement the smallest vertical slice.
4. Run the targeted test and broader required checks.
5. Record GREEN evidence.
6. Refactor only while green.

Do not apply TDD dogmatically to pure docs, mechanical renames, generated snapshots, or exploratory spikes. In those cases, write an explicit evidence plan or waiver.

## 5. Capture evidence

Every completion claim needs fresh, claim-relative evidence or waiver. Skipped checks are not pass results. For medium or higher risk, passing evidence should include a command log, artifact URI, or manual artifact reference so review can inspect what actually happened.

Evidence freshness is strict for implementation changes. HEAD, diff representation, or harness lifecycle artifacts under `.harness/` can change after evidence or review for commits, handoff, receipts, review records, or archival notes; when implementation content is unchanged, those non-implementation context changes should warn rather than force all product evidence to be rerun.

Gate:

```bash
python3 harness/cli/harnessctl.py validate --id <WU-ID> --strict
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate verification --strict
```

CI / protected branch gate:

```bash
python3 harness/cli/harnessctl.py ci --strict
```

## 6. Review

Plan review checks whether the execution plan is grounded in repository truth before implementation starts. Close review checks whether diff, evidence, scope, risk, and maintainability satisfy the Work Unit Contract before acceptance. Close-addendum review supplements a prior close review after evidence-only or lightweight acceptance changes. Publication review checks GitHub issue/PR/branch publication and does not replace implementation close review.

For medium or higher risk, `running` requires a passing plan review or explicit self-check downgrade where allowed. For high or critical risk, use independent review or human gate. For medium or higher risk, the passing review set must cite the fresh evidence receipt IDs it relied on. A close-addendum or publication review may cite newly added receipts without forcing a full close review when implementation content is unchanged.

On Codex, subagents are explicit. When a Work Unit requires reviewer or worker isolation, the main agent must start the reviewer/worker directly and wait for the result before continuing; do not rely on automatic delegation.

Gates:

```bash
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate plan-review --strict
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate review --strict
```

## 7. GitHub collaboration

Use GitHub after the local task shape is grounded. Create issues, branches, commits, and PRs after the Work Unit is specified and the relevant plan review has passed. GitHub records collaboration state; it does not replace the contract, evidence receipts, review verdicts, waivers, or controller gates. If GitHub collaboration is added after implementation, record it as a `collaboration_only` amendment, add publication evidence, and use publication review instead of rerunning implementation review unless code/scope/risk changed.

Do not keep a local Work Unit active only because a PR is waiting for merge. Once local implementation, evidence, close review, and PR/update publication are complete, archive the Work Unit locally with a no-next-step reason or handoff. If PR review or merge later requires changes, reopen the archived Work Unit or create a follow-up Work Unit with the new scope.

## 8. Handoff or archive

A task can be archived when local completion gates pass: evidence/waiver, required review, and either a handoff or an explicit `--no-next-step-reason`. Remote PR merge is not a prerequisite for local archive because the harness cannot reliably infer merge state from local repository state.

## 9. Compound or prune

Keep or add a mechanism only if it has a failure trace, protected invariant, validation method, known cost, and removal condition.
