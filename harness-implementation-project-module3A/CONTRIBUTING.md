# Contributing To The Harness

This project is a harness implementation, so changes should remain traceable to
the failure mode or invariant they improve. Keep changes small, testable, and
easy to remove if the mechanism stops paying for itself.

## Change Classes

- Documentation-only changes: update the relevant docs and run a text/link check
  when available.
- Controller changes: update focused tests in `harness/tests/` and nearby docs.
- Hook changes: add or update hook simulation tests and document the lifecycle
  event shape.
- Skill or adapter changes: update the canonical `skills/` source first, then
  any copied platform examples or validation checks.
- New, removed, or materially changed harness mechanisms: update
  `docs/harness/mechanism-registry.yaml`.

## Traceability Checklist

For every harness behavior change, record or preserve:

- the Work Unit or issue that requested the change;
- the failure trace, user friction, or invariant gap that justifies it;
- the protected invariant;
- the validation used to prove the change;
- the known cost or false-positive risk;
- the removal, downgrade, or replacement condition.

If a change affects Work Unit, evidence, handoff, review, boundary, hook, or CI
flow, decide whether an HEB case, hook simulation, or controller regression test
is needed. Do not add a persistent mechanism solely because it is convenient in
one conversation.

## Verification

Default local verification:

```bash
python3 -m unittest discover -s harness/tests
```

Run narrower tests first when iterating, then the full suite before handing off.
If a check cannot run, record the reason and the replacement evidence or waiver.

## Documentation

Keep user-facing lifecycle rules in `docs/harness/`, reusable procedures in
`skills/`, deterministic behavior in `harness/cli` or `harness/hooks`, and short
routing guidance in `AGENTS.md` / `CLAUDE.md`. Do not store active Work Unit
state, chat history, or one-off debug notes in durable project guidance.

When changing terminology, update the entrypoint docs, adoption templates, hook
messages, and skills that route the same behavior.
