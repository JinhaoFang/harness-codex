# Agent Project Guide

This file is a short project map for Codex and other coding agents. It routes work to the right artifacts; it is not the full harness manual, task state store, or policy engine.

## 1. Role And Scope

- Treat this repository as a portable coding-agent harness implementation, not a business application.
- Keep active task state in `.harness/work-units/active/<WU-ID>/`, not in this file.
- Keep detailed lifecycle guidance in `docs/harness/`; keep reusable agent procedures in `skills/`.
- When copied into another repository, update project-specific commands, paths, and risk boundaries before relying on it.

## 2. Operating Principles

- Think before coding: state assumptions, surface ambiguity, and ask when intent or risk is unclear.
- Prefer simple, surgical changes that match the existing project style.
- Do not expand scope silently. Amend the Work Unit or stop for human direction.
- Separate truth sources: repository/runtime facts, Work Unit contracts, evidence receipts, review verdicts, waivers, and handoffs are not interchangeable.
- Do not call work complete without fresh evidence or an explicit human-approved waiver.

## 3. Harness Lifecycle

For non-trivial work:

```text
Clarify -> Work Unit Contract -> Context Routing -> Plan Review when needed -> Implementation -> Evidence -> Verification -> Close Review -> CI Gate -> Handoff or Archive
```

- Read `.harness/work-units/active/<WU-ID>/contract.md` directly before implementation.
- Lock the contract before running implementation gates.
- If a locked contract changes, record an amendment with `harnessctl amend`.
- Review judges sufficiency; it does not create evidence.

## 4. Task Classification

- Trivial: comments, small docs, or no production/runtime impact. A self-check may be enough.
- Non-trivial: production code, user-visible behavior, multiple files, reviewable artifacts, or cross-session work. Create or read a Work Unit Contract.
- Medium risk: multi-file or user-visible behavior. Use evidence receipts and close review.
- High/critical risk: auth, permissions, billing, migrations, secrets, production data, deployment, compliance, irreversible changes, or broad deletion. Require risk notes, rollback or reopen path, and independent review or human approval.

## 5. Context Routing

Read in this order:

1. Work Unit Contract or issue spec.
2. `docs/harness/README.md` and `docs/harness/workflow.md` for lifecycle rules.
3. Local rules near files you will touch.
4. Current code, tests, runtime behavior, and CI configuration.
5. ADRs or docs referenced by the Work Unit or changed paths.

If docs conflict with code, tests, or runtime behavior, surface the conflict and trust current world truth for implementation decisions.

## 6. Coding Standards

- Keep changes minimal and traceable to the Work Unit.
- Reuse existing code paths before adding new abstractions.
- Avoid speculative flexibility, unrelated refactors, and broad formatting churn.
- Remove only unused code/imports created by your own changes unless explicitly asked.
- Code files should have a short module-level description when project style supports it.
- Keep files under 1000 lines where practical; split only for real readability or ownership reasons.

## 7. Testing And Evidence

- For code-bearing development, use behavior-first TDD unless the contract explicitly defines another evidence plan.
- Record verification with `harnessctl evidence`; a natural-language claim is not evidence.
- Medium+ evidence should include `command_log_ref`, `artifact_uri`, or `manual_artifact_ref`.
- Skipped checks are never pass results. Record skipped evidence as skipped or use a scoped waiver.
- Run artifact validation before verification/review:

```bash
python3 harness/cli/harnessctl.py validate --id <WU-ID> --strict
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate verification --strict
```

## 8. Review And Acceptance

- Plan review checks whether the proposed work is grounded before implementation.
- Close review checks diff, evidence, scope, risk, and maintainability before acceptance.
- Builders must not write their own close review PASS.
- Medium+ close review must cite fresh evidence receipt IDs.
- High/critical work needs independent review or a human gate.

## 9. Commands

```bash
python3 harness/cli/harnessctl.py init
python3 harness/cli/harnessctl.py list
python3 harness/cli/harnessctl.py status --id <WU-ID>
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate spec --strict
python3 harness/cli/harnessctl.py lock --id <WU-ID> --status ready
python3 harness/cli/harnessctl.py evidence --id <WU-ID> --claim EV1 --type test --result pass --command "<command>" --command-log-ref "<log>"
python3 harness/cli/harnessctl.py validate --all --strict
python3 harness/cli/harnessctl.py ci --strict
python3 -m unittest discover -s harness/tests
```

Use project-specific build/test commands when a target repository defines them.

## 10. Platform Assets

- Codex repo skills live in `.agents/skills/` when the Codex profile is adopted.
- Codex subagent examples live in `.codex/agents/`; keep worker/reviewer as the default retained roles.
- Codex hook examples live in `.codex/hooks.json`; merge with existing project config rather than overwriting blindly.
- Platform-neutral editable skills live in `skills/`.
- Claude Code examples live in `.claude/` and are documented in `CLAUDE.md`.

## 11. Safety And Boundaries

- Do not handle secrets, production data, migrations, deployment, billing, auth, or irreversible operations without explicit risk handling.
- Destructive commands, force pushes, direct pushes to protected branches, package publishing, infrastructure mutation, and cluster mutation require human approval or platform permission gates.
- Prompt instructions are not sufficient for non-negotiable boundaries; use controller checks, hooks, permissions, CI, branch protection, or human gates.

## 12. Update Rules

- Keep this file short and structured. Update the relevant section instead of appending new free-form rules.
- Do not store active Work Unit state, chat summaries, or debug history here.
- Put detailed lifecycle changes in `docs/harness/`, reusable procedures in `skills/`, and deterministic checks in `harness/cli` or CI.
- When changing controller behavior, update tests and nearby docs in the same change.
