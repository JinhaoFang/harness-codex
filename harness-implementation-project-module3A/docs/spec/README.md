# Tracked Feature Specifications

Approved user/product intent for non-trivial Work Units lives here as `docs/spec/<WU-ID>.md`.

A spec records the problem, observable outcome, non-goals, write boundary, required evidence, stop conditions, clarification decisions, context pointers, and stable GitHub delivery references. It should be understandable by developers without access to an agent session.

Technical implementation plans, command logs, evidence receipts, review tracks, and handoffs are local intermediate artifacts under ignored `.harness/`. When that runtime is absent, rebuild it from the tracked spec, Git/GitHub history, and current code with:

```bash
python3 harness/cli/harnessctl.py resume --id <WU-ID>
```
