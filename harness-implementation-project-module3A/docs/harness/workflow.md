# Workflow

The Harness has two loops and three long-lived roles.

```text
Definition loop: idea → clarify → approved tracked Spec
Delivery loop:   Spec → Plan → Plan Review → Worker/TDD → evidence → Close Review → integration

Conductor: clarify, obtain approval, and invoke lifecycle transitions
Reviewer:  read-only; one logical platform session from Plan Review through Close Review
Worker:    isolated implementation and controller-observed evidence production
```

Every role grounds on current repository truth, Work Unit progress, and GitHub integration state via `harness-ground` before starting its turn — reading what *is*, not what a prior summary claimed. No role begins clarifying, planning, reviewing, or implementing from stale context.

## 1. Clarify and freeze intent

Use `harness-clarify` before product-code changes. Inspect the minimum relevant repository facts, ask one high-value product question at a time, and update the single tracked Spec draft. Clarification ends at `awaiting_spec_approval`; it never silently starts planning or implementation.

The canonical JSON block in `docs/spec/<WU-ID>.md` owns intent, observable outcomes, non-goals, scope, claim IDs, structured checks, stop conditions, and clarification decisions. Commands are `argv[]`, not quoted shell strings. `scope.write_boundary` and `scope.out_of_bounds` are executable repository path/glob constraints, not descriptive prose; the controller matches them mechanically against changed files.

```bash
harnessctl check --id <WU-ID> --gate spec --strict
harnessctl approve-spec \
  --id <WU-ID> --approved-by human:<identity> --approval-ref <durable-ref>
```

Approval binds the semantic contract hash. Delivery references are deliberately excluded from that hash; product intent is not reapproved merely because an issue or PR number changes.

## 2. Build the local technical plan

The ignored plan lives at:

```text
.harness/work-units/active/<WU-ID>/plan.md
```

Re-ground it in current code, tests, runtime, local rules, and Git/GitHub facts. Every behavior slice binds a required claim to test paths, an observable oracle, RED check and expected failure signature, GREEN check, allowed paths, risks, and replan conditions. The plan must also define the final `acceptance_evidence` level for each claim so the Worker and Reviewer know whether completion depends on unit, integration, functional, E2E, acceptance, smoke, or other runtime-facing proof. The plan may evolve as project facts are discovered, but cannot alter approved intent or scope by itself.

## 3. Advance continuously

After the plan passes its structural gate, invoke:

```bash
harnessctl route --id <WU-ID> --platform codex
harnessctl advance \
  --id <WU-ID> --platform claude \
  --reviewer-id <REVIEWER-ID> \
  --planner-id <PLANNER-ID> --planner-session <PLANNER-SESSION> \
  --builder-id <WORKER-ID>
```

For Codex, `route` repeatedly tells the main session which native subagent action is next. For Claude, `advance` repeatedly asks the controller for the next valid transition. Across both paths the lifecycle can:

```text
dispatch Plan Review
→ dispatch/resume Worker
→ dispatch Close Review in the same Reviewer session
→ run final acceptance gates
```

It stops rather than guessing when clarification is incomplete, the plan is invalid, evidence is missing, a reviewer requests changes, a platform adapter/native session binding fails, or a human/risk decision is required. Each transition rechecks current state and hashes, so a stale action cannot silently mutate a newer Work Unit generation.

## 4. Plan Review

The Reviewer reads the tracked Spec, local plan, current repository, tests, and relevant runtime facts. It does not merely validate document shape or planner-selected anchors. Claude's adapter capability-probes the installed CLI and launches a read-only reviewer. Codex instead uses a native reviewer subagent whose real session is bound into the same logical review track.

For manual review, use `request-review` and `submit-review`. A reviewer replacement requires `reviewer-takeover`; takeover increments generation and requires Plan Review again.

## 5. Worker and behavior-first TDD

The Worker gets workspace-write capability only after Plan Review. For each behavior slice it should run:

```bash
harnessctl verify --id <WU-ID> --claim <EV-ID> --phase red
harnessctl verify --id <WU-ID> --claim <EV-ID> --phase green
harnessctl verify --id <WU-ID> --claim <EV-ID> --phase final
```

`verify` resolves the approved `check_id` and executes the exact `argv[]` with `shell=False`. Optional argv after `--` is an equality assertion, not another command source. RED succeeds only when the command fails for the reviewed reason; arbitrary syntax/import/environment failure is rejected by the expected-failure oracle.

Receipts bind the check-definition hash, argv, cwd, logs, approved spec/plan hashes, repository/workspace, branch, HEAD, and implementation diff. A skipped check remains `skipped` and blocks completion. Fresh internal or static checks do not automatically satisfy user-visible acceptance unless the planned `acceptance_evidence` says that level is sufficient.

## 6. Close Review

Close Review resumes the exact platform session created for Plan Review. The Reviewer retains previously identified risks but must re-ground in current code, complete diff, tests, and fresh receipts. The Reviewer enumerates the complete diff with native `git diff` and reviews every changed file and hunk — including bystander fields the planned change did not target — so collateral damage is not hidden behind green checks. The plan remains a hypothesis, not proof.

A reviewer that modifies the implementation becomes a builder for the new diff; prior evidence/review must be regenerated. This implementation therefore keeps the Reviewer read-only. High/critical work may add a separate fresh security/risk reviewer or human gate without replacing the continuous primary Reviewer.

Any relevant change after the review request or verdict invalidates that review.

## 7. Git/GitHub integration

Git is execution history; GitHub is collaboration/integration history. Neither replaces the Spec or evidence.

```bash
harnessctl delivery-link \
  --id <WU-ID> --issue <REF> --branch <BRANCH> --pull-request <REF> \
  --required-check test --required-check lint
harnessctl github-sync --id <WU-ID>
harnessctl check --id <WU-ID> --gate delivery --strict
```

The controller stores only a local snapshot/reference. When a PR is linked, the delivery gate checks PR HEAD against local HEAD and checks explicitly declared required status names. It does not reinterpret CI success as evidence for unrelated product claims.

## 8. Recovery

```text
resume-session: local runtime and platform bindings still exist; continue them
reconstruct:     local runtime was lost; rebuild conservatively from Spec + Git
```

`PreCompact` writes a fresh controller checkpoint; `PostCompact` injects only a short pointer. Checkpoints include Work Unit, workspace, branch, base/head, diff, current role, session refs, evidence refs, blockers, and next safe action.

Reconstruction never claims that old local plans, receipts, or reviews survived.

## 9. Archive and override

Normal archive requires Spec, scope, verification, review, optional delivery gate, and a handoff/no-next-step reason. Forced archive is an auditable risk override and requires:

```bash
--reason ... --approved-by human:<identity> --approval-ref <durable-ref>
```

The override is recorded before the local runtime is moved to archive.
