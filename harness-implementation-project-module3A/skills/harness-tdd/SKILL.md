---
name: harness-tdd
description: Implement an approved plan through behavior-first RED/GREEN/refactor slices using controller-executed verification, then route directly to Close Review when evidence is complete.
---

# Harness TDD

Prerequisites: approved tracked Spec, passing Plan Review, and a controller-bound isolated Worker.

For each behavior slice:

1. Write an externally observable test inside the reviewed test surface.
2. Run the declared RED check through the controller and inspect that it fails for the **expected reason**, not syntax, import, environment, or “no tests found” failure.

```bash
harnessctl verify --id <WU-ID> --claim <EV-ID> --phase red
```

3. Implement the smallest vertical slice inside the approved write boundary.
4. Run GREEN, refactor only while GREEN, and rerun affected checks.

```bash
harnessctl verify --id <WU-ID> --claim <EV-ID> --phase green
```

5. Produce fresh final evidence for every required claim, and make sure the final evidence matches the acceptance level planned in `acceptance_evidence`. RED/GREEN alone do not prove completion if the final user-visible outcome needs a broader check.

```bash
harnessctl verify --id <WU-ID> --claim <EV-ID> --phase final
```

6. Do not pause merely because implementation ended. For Codex, resume the same native reviewer subagent from Plan Review; for Claude/manual adapter flows, invoke `advance` so the exact Reviewer session performs Close Review:

```bash
harnessctl route --id <WU-ID> --platform codex
harnessctl advance --id <WU-ID> --platform claude
```

A RED receipt never satisfies completion. When the test cannot express the behavior or the implementation needs unapproved scope, stop and return to the plan/spec instead of weakening the assertion.

For Codex native orchestration details, including when to bind or resume the worker session, follow `docs/harness/codex-native-subagents.md`.
