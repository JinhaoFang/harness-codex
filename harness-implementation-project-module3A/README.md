# Coding Agent Repository Harness

A lightweight repository harness for Codex, Claude Code, and similar coding agents. It separates tracked product intent from disposable execution state and makes the critical lifecycle boundaries mechanical.

## Design

```text
idea
→ clarify tracked spec
→ human approves spec revision
→ build local technical plan
→ plan review
→ isolated worker + TDD
→ controller-executed verification
→ same reviewer track closes the work
→ Git/GitHub integration or local handoff
```

Truth placement is deliberately small:

| Location | Purpose | Git tracked |
|---|---|---|
| `docs/spec/<WU-ID>.md` | approved product intent, scope, success, evidence contract | yes |
| current code/tests/runtime | current project truth | yes / runtime |
| Git and GitHub | actual changes, collaboration, CI, review and integration history | yes / remote |
| `.harness/` | local plan, state, command logs, evidence index, review track, handoff | no |

`.harness/` is recoverable runtime, not the system of record. Losing it must not lose product intent. Run `resume` to rebuild a safe local starting point from the tracked spec and current repository; prior local evidence and review are not assumed.

## What the controller enforces

- Product-file boundaries are enforced by controller gates and can be reinforced by optional platform policy hooks when a repository chooses to wire them in.
- Implementation cannot start before spec approval and the required plan review.
- `verify` executes the command itself and derives pass/fail from the observed exit code.
- Evidence is invalidated when relevant implementation content changes.
- A skipped required check blocks; the default profile has no generic waiver path.
- Plan and close review share one reviewer track; the close reviewer is read-only and cannot be the builder/session.
- Runtime pointers are namespaced by workspace/worktree identity.

## Quick start

```bash
python3 harness/cli/harnessctl.py new \
  --id WU-001 --title "Add bounded behavior" --type feature --risk medium

# Clarify and edit docs/spec/WU-001.md, then record the user's approval.
python3 harness/cli/harnessctl.py approve-spec \
  --id WU-001 --approved-by human:owner --approval-ref issue:123

# Fill .harness/work-units/active/WU-001/plan.md.
python3 harness/cli/harnessctl.py request-review \
  --id WU-001 --mode plan --reviewer-id reviewer-1 --reviewer-session review-plan-1 \
  --planner-id planner-1 --planner-session planner-session-1
python3 harness/cli/harnessctl.py submit-review \
  --id WU-001 --mode plan --request-id <RR-ID> --decision PASS \
  --reviewer-id reviewer-1 --reviewer-session review-plan-1

# Start the isolated worker only after the plan verdict passes.
python3 harness/cli/harnessctl.py start-work \
  --id WU-001 --builder-id worker-1 --builder-session worker-session-1

# Controller-observed TDD / final verification.
python3 harness/cli/harnessctl.py verify \
  --id WU-001 --claim EV1 --phase red --expect fail -- <test-command>
python3 harness/cli/harnessctl.py verify \
  --id WU-001 --claim EV1 --phase green --expect pass -- <test-command>
python3 harness/cli/harnessctl.py verify \
  --id WU-001 --claim EV1 --phase final

python3 harness/cli/harnessctl.py request-review \
  --id WU-001 --mode close --reviewer-id reviewer-1 --reviewer-session review-close-1
python3 harness/cli/harnessctl.py submit-review \
  --id WU-001 --mode close --request-id <RR-ID> --decision PASS \
  --reviewer-id reviewer-1 --reviewer-session review-close-1 --evidence-ref <EV-ID>
python3 harness/cli/harnessctl.py finalize-check --id WU-001 --strict
```

Use `harnessctl --help` for the complete command surface.

## Repository layout

```text
skills/                     canonical task-routed skills
.agents/skills/             Codex project skill mirror
.claude/skills/             Claude Code project skill mirror
harness/cli/harnessctl.py   lifecycle controller
harness/hooks/              narrow routing and policy hooks
harness/templates/          tracked spec and local plan templates
harness/schemas/            receipt/review/state schemas
docs/harness/               implementation documentation
docs/spec/                  tracked feature specifications
scripts/adopt.py             incremental installer
```

## Validate this harness

```bash
make test
make ci
make check
```

The default implementation intentionally omits schedulers, generic waiver machinery, resident planner/explorer agents, stop-blocking hooks, and tracked runtime ledgers. Add a mechanism only when a real failure trace proves its benefit.
