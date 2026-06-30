# Operator guide

## Storage model

```text
docs/spec/<WU-ID>.md                       tracked intent and approval
.harness/work-units/active/<WU-ID>/        ignored local execution state
  plan.md                                  local technical design
  state.json                               lifecycle and Git/workspace snapshot
  evidence/receipts.jsonl                  evidence index
  evidence/artifacts/*.log                 command output
  reviews/track.json                       persistent Reviewer lineage
  reviews/requests/*.json                  immutable review inputs
  reviews/verdicts/*.json                  judgments
  recovery/checkpoint.json                 controller checkpoint
  handoff.md                               derived recovery view
.harness/runtime/<workspace-id>/<session>/current
.harness-adoption.json                     tracked installation ownership hashes
```

## Automated command sequence

```bash
harnessctl new --id WU-123 --title "..." --type feature --risk medium
# Edit and walk through docs/spec/WU-123.md.
harnessctl check --id WU-123 --gate spec --strict
harnessctl approve-spec --id WU-123 --approved-by human:owner --approval-ref issue:123
# Edit the local plan, then let Codex route native reviewer/worker subagents.
harnessctl check --id WU-123 --gate plan --strict
harnessctl route --id WU-123 --platform codex
```

For Codex, `route` reports the next native reviewer/worker action and the controller commands that must accompany it. For Claude, `advance` performs all currently valid automatic transitions; use `advance --dry-run` or `route` to inspect without execution.

## Manual control surface

```bash
# Plan review. Capture and reuse one logical reviewer session.
harnessctl request-review --id WU-123 --mode plan \
  --reviewer-id rev-1 --reviewer-session review-session-1 \
  --planner-id planner-1 --planner-session plan-session-1
harnessctl submit-review --id WU-123 --mode plan --request-id <RR> \
  --decision PASS --reviewer-id rev-1 --reviewer-session review-session-1

# Worker and evidence.
harnessctl start-work --id WU-123 --builder-id worker-1 --builder-session worker-session-1
harnessctl verify --id WU-123 --claim EV1 --phase red
harnessctl verify --id WU-123 --claim EV1 --phase green
harnessctl verify --id WU-123 --claim EV1 --phase final

# Close review resumes the same logical session, not a new alias.
harnessctl request-review --id WU-123 --mode close \
  --reviewer-id rev-1 --reviewer-session review-session-1
harnessctl submit-review --id WU-123 --mode close --request-id <RR> \
  --decision PASS --reviewer-id rev-1 --reviewer-session review-session-1 \
  --evidence-ref <EV>
harnessctl finalize-check --id WU-123 --strict
```

## Important commands

| Command | Purpose |
|---|---|
| `new` | create tracked draft Spec and ignored runtime |
| `approve-spec`, `amend` | record accountable intent approval/change |
| `advance` | Claude/manual adapter path: execute valid Plan Review → Worker → Close Review → final gate transitions |
| `route` | report one next transition; for Codex this is the primary native-subagent routing surface |
| `dispatch-review`, `dispatch-worker` | Claude/manual adapter path: invoke one platform role and capture its real session ID |
| `reviewer-takeover` | explicitly replace an unrecoverable Reviewer and reset review generation |
| `bind-session` | bind a native platform session so controller review/worker gates can trust it |
| `verify` | execute an approved structured check and record observed evidence |
| `delivery-link`, `github-sync` | bind PR/check references and capture GitHub state |
| `resume-session` | continue existing local/controller session state |
| `reconstruct` | conservatively rebuild runtime after `.harness` loss |
| `checkpoint`, `handoff` | create recovery state/view |
| `workspace-check`, `workspace-create` | enforce or create Work Unit worktree isolation |
| `finalize-check`, `archive` | run acceptance/archive gates |
| `adapter-doctor`, `doctor`, `ci` | validate platform and repository installation |

When `harnessctl` is not installed globally, vendored repositories can use the repo-local `./harnessctl` wrapper. Thin shared repositories expect an externally installed `harnessctl`.

For native Codex/Claude subagents, the normal path is: bind the observed reviewer/worker session, call `request-review` / `start-work`, let the worker run `verify`, then resume the same reviewer session for close review. `dispatch-review` / `dispatch-worker` remain controller-managed adapter surfaces, mainly for Claude/manual flows and diagnostics.

## Evidence rules

- The approved contract owns the command as structured `argv[]`.
- Optional argv after `verify ... --` must exactly match the contract.
- `red` requires nonzero exit plus the plan's expected failure signature.
- `green` is useful during a slice; only fresh `final` evidence satisfies completion.
- Any relevant implementation change invalidates prior receipts.
- `record-skipped` is a blocker/observation, never a pass or waiver.

## Reviewer rules

- Reviewer is read-only and separate from planner/builder.
- Plan and Close Review use one logical platform session.
- Close Review directly inspects the current repository, diff, tests, and receipts.
- A silent session replacement is rejected.
- High/critical work can add fresh specialist review or a human gate.

## GitHub delivery

The Spec's `delivery.required_checks` lists exact GitHub check names. `github-sync` captures PR head and normalized check outcomes with `gh`; `check --gate delivery` fails when the local and PR heads differ or a required check is absent/pending/failing. No PR means no GitHub burden unless required checks were configured.

## Recovery

`resume-session` requires the local runtime to exist. `reconstruct` reads the tracked Spec and current Git/code, creates a new empty local plan/runtime, and refuses to restore old evidence or verdicts from narrative memory.

The pre-compaction hook writes a fresh checkpoint automatically. Session-start context is a short pointer to authoritative artifacts, not a copied task history.

`PreToolUse` is optional hardening. When enabled, keep it limited to dangerous shell/tool interception. Ordinary phase, scope, and acceptance enforcement belongs to controller gates and repository/platform sandboxing.

## Archive override

`archive --force` is not an anonymous bypass. It requires a reason, `human:<identity>`, and durable approval reference, and records an `archive-override.json` judgment.
