# Coding Agent Repository Harness

A purpose-fit repository harness for Codex, Claude Code, and similar coding agents. It keeps product intent tracked, execution state local, commands structured, evidence observable, sessions recoverable, and acceptance outside the model.

## Lifecycle

```text
idea
→ repository-grounded clarification
→ tracked Spec / PRD + explicit human approval
→ local technical plan
→ independent Plan Review
→ isolated Worker + behavior-first TDD
→ controller-executed evidence
→ the same logical Reviewer session performs Close Review
→ GitHub / CI / human integration
```

The normal delivery loop is continuous. For Codex, native reviewer/worker subagents carry Plan Review, implementation, and Close Review while the controller keeps lifecycle authority. For Claude Code, `advance` dispatches Plan Review, starts or resumes the Worker, resumes the same Reviewer for Close Review, and runs the final gate. Both paths stop for a real human decision, a blocker, missing evidence, requested rework, or completion.

## Truth placement

| Location | Purpose | Git tracked |
|---|---|---|
| `docs/spec/<WU-ID>.md` | approved intent, scope, evidence contract, delivery references | yes |
| current code/tests/runtime | current project truth | yes / runtime |
| Git and GitHub | diff, commits, PR/CI and integration history | yes / remote |
| `.harness/` | local plan, state, receipts, session lineage, checkpoints and handoff | no |
| `.harness-adoption.json` | hashes of safely managed installation assets | yes |

`.harness/` is a disposable continuity cache, not a team task ledger. Continue with `resume-session` while it exists. If it is lost, use `reconstruct`; reconstruction never invents the old plan, evidence, or review.

## Mechanical guarantees

- The tracked Markdown spec contains one canonical JSON Work Unit contract; prose is not parsed as pseudo-YAML.
- Checks use `check_id` plus structured `argv[]`; normal execution uses `shell=False`.
- Embedded quotes and spaces survive as argv values rather than being stripped and reparsed.
- TDD RED must match the failure reason declared by the reviewed plan.
- Evidence is bound to the approved spec, reviewed plan, check definition, repository/workspace, branch, HEAD, and implementation diff.
- Plan and Close Review use the exact same logical Reviewer session. `reviewer-takeover` is explicit and resets review lineage.
- A post-review commit or relevant diff change invalidates Close Review.
- Workspace recovery distinguishes repository identity from worktree identity.
- Platform adapters capture real Codex/Claude session IDs and fail closed on capability or session-capture failure.
- Codex workers bind the projection to persisted thread Goal state through app-server when available; Goal completion remains non-authoritative and an explicit degraded fallback never weakens controller gates.
- Compound shell commands cannot borrow the controller command exception.
- A linked PR must match local HEAD and satisfy explicitly configured GitHub checks before delivery/archive passes.

## Typical path

```bash
harnessctl new \
  --id WU-001 --title "Add bounded behavior" --type feature --risk medium

# Complete docs/spec/WU-001.md, walk it through with the user, then approve it.
harnessctl approve-spec \
  --id WU-001 --approved-by human:owner --approval-ref issue:123

# Complete .harness/work-units/active/WU-001/plan.md, then let Codex launch
# native reviewer/worker subagents and use the controller for routing/gates.
harnessctl check --id WU-001 --gate plan --strict
harnessctl route --id WU-001 --platform codex

# Optional GitHub integration gate.
harnessctl delivery-link \
  --id WU-001 --issue 123 --pull-request 456 \
  --required-check test --required-check lint
harnessctl github-sync --id WU-001
harnessctl finalize-check --id WU-001 --strict
```

Use `route` to inspect the next transition. For Claude, `advance --dry-run` or `advance` still drive controller-managed dispatch. Manual `request-review`, `submit-review`, `start-work`, `bind-session`, and `verify` commands remain available.

## Install and upgrade

```bash
python3 scripts/adopt.py install /path/to/repo --profile codex
python3 scripts/adopt.py install /path/to/repo --profile thin-shared-codex
python3 scripts/adopt.py check /path/to/repo
python3 scripts/adopt.py upgrade /path/to/repo
```

The tracked adoption manifest lets upgrades replace only assets that still match the previously installed hash. Locally modified managed files cause an explicit conflict instead of being overwritten.

## Validate and release

```bash
make check
make release
```

`make release` builds a deterministic zip, embeds a SHA-256 manifest, extracts it into a clean directory, runs the test suite and controller gates, and rejects `.harness`, caches, bytecode, or hash drift.

The implementation intentionally omits a resident scheduler, generic multi-agent swarm, and tracked runtime ledger. Add a mechanism only when a failure trace proves it is the smallest effective control.
