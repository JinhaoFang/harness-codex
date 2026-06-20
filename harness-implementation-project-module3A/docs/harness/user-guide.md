# Operator guide

## Storage model

```text
docs/spec/<WU-ID>.md                       tracked intent and approval metadata
.harness/work-units/active/<WU-ID>/        ignored local execution state
  plan.md                                  local technical design
  state.json                               phase, identity and Git snapshot
  evidence/receipts.jsonl                  small evidence index
  evidence/artifacts/*.log                 command output
  reviews/track.json                       persistent reviewer lineage
  reviews/requests/*.json                  review input snapshots
  reviews/verdicts/*.json                  judgments
  handoff.md                               local recovery view
.harness/runtime/<workspace-id>/current    workspace-local active pointer
```

The local directory is deliberately disposable. It is useful for session continuity, but the safe recovery substrate is the tracked spec plus current Git/GitHub/code.

## Main command sequence

```bash
# Create draft spec and local runtime.
harnessctl new --id WU-123 --title "..." --type feature --risk medium

# Validate and approve the user-visible spec.
harnessctl check --id WU-123 --gate spec --strict
harnessctl approve-spec --id WU-123 --approved-by human:owner --approval-ref issue:123

# Complete local plan, then request/submit plan review.
harnessctl check --id WU-123 --gate plan --strict
harnessctl request-review --id WU-123 --mode plan --reviewer-id rev-1 --reviewer-session rev-plan-1 --planner-id planner-1 --planner-session plan-1
harnessctl submit-review --id WU-123 --mode plan --request-id <RR> --decision PASS \
  --reviewer-id rev-1 --reviewer-session rev-plan-1

# Start worker and verify actual commands.
harnessctl start-work --id WU-123 --builder-id worker-1 --builder-session build-1
harnessctl verify --id WU-123 --claim EV1 --phase red --expect fail -- <command>
harnessctl verify --id WU-123 --claim EV1 --phase green --expect pass -- <command>
harnessctl verify --id WU-123 --claim EV1 --phase final

# Same reviewer lineage closes the work from a separate session.
harnessctl request-review --id WU-123 --mode close --reviewer-id rev-1 --reviewer-session rev-close-1
harnessctl submit-review --id WU-123 --mode close --request-id <RR> --decision PASS \
  --reviewer-id rev-1 --reviewer-session rev-close-1 --evidence-ref <EV>
harnessctl finalize-check --id WU-123 --strict
```

Run through `python3 harness/cli/harnessctl.py` when `harnessctl` is not installed on `PATH`.

## Commands

| Command | Purpose |
|---|---|
| `init` | initialize ignored local runtime and `.gitignore` entry |
| `new` | create tracked draft spec and local plan/runtime |
| `resume` | reconstruct a safe local runtime from a tracked spec |
| `status`, `brief`, `list` | inspect current local state |
| `approve-spec` | record human approval in the tracked spec and local state |
| `amend` | approve changed spec content; material changes invalidate plan review |
| `check` | run one deterministic gate |
| `request-review`, `submit-review` | maintain the plan/close reviewer track |
| `start-work` | bind builder identity/session and enter implementation |
| `verify` | execute a command and derive evidence from observation |
| `record-skipped` | record a missing check and block the task |
| `resume-work` | re-enter implementation from handoff/blocked after current spec and plan gates pass |
| `finalize-check` | combine spec, scope, verification and close-review gates |
| `handoff` | generate local recovery information |
| `archive` | archive local runtime; tracked spec remains |
| `ci` | validate tracked specs and installed skill mirrors |
| `doctor` | inspect installation shape |

## Spec amendments

A manual edit to approved spec content invalidates the approval hash. Use:

```bash
harnessctl amend --id WU-123 \
  --reason "Requirement changed" --summary "Add observable behavior X" \
  --actor human:owner --approval-ref issue:123#comment-4
```

Every approved spec-content change is treated as material: it returns the lifecycle to `spec_approved`, clears plan approval, and requires a fresh plan review. This deliberately avoids a weak “context-only” escape hatch that could silently change intent.

## Evidence rules

- `verify` takes an argv after `--`; it does not use a shell by default.
- `--expect pass` requires exit code 0.
- `--expect fail` requires a non-zero exit code and is intended for TDD RED observation.
- The controller captures command logs under `.harness/`.
- Any implementation-content change makes prior receipts stale.
- A skipped record is not evidence and cannot satisfy completion.

## Reviewer rules

- Plan and close modes are the default review surface.
- The reviewer identity that owns the plan track must normally own close review.
- A different reviewer requires an explicit future takeover mechanism; the default CLI rejects silent replacement.
- Close review cannot use the builder identity/session.
- Reviewer findings go back to the worker; reviewer does not edit product code.
- Medium+ close review cites current receipt IDs.

## Optional phase write policy

The repository includes optional hook helpers for phase/path policy if a project wants stronger platform-level enforcement than the default installed hook surface:

| Phase | Writable surface |
|---|---|
| `clarifying` | current tracked spec only |
| `spec_approved`, `planning`, `plan_reviewing` | tracked spec and local plan only |
| `ready` | no product edit until `start-work` |
| `running` onward | approved write boundary; spec/plan changes require stopping |
| reviewer role | read-only |

These hooks are defense-in-depth only. The default installed adapters keep the hook surface to `PreCompact`, `PostCompact`, and `Stop`; CI, sandbox, permissions and branch protection remain necessary for high-risk boundaries.

## Recovery

`.harness/runtime/<workspace-id>/current` avoids one repository-global pointer across worktrees. A session brief always re-reads the spec and current Git/code.

When a local handoff or blocker exists, `resume-work` rechecks the approved spec and plan review, then binds a fresh worker session before product writes are enabled again. There is no generic state setter.

When `.harness` is unavailable, `resume`:

1. reads `docs/spec/<WU-ID>.md`;
2. verifies its approval marker/content hash;
3. recreates local state and an empty plan template;
4. does not claim old evidence or review survived;
5. directs the agent to rebuild and review the plan.

This is deliberate recovery, not exact replay.
