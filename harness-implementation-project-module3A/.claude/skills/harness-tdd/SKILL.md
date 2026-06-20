---
name: harness-tdd
description: Implement an approved plan through behavior-first RED/GREEN/refactor slices using controller-executed verification. Use for bug fixes, features, interfaces, schemas, errors, permissions, or lifecycle behavior.
---

# Harness TDD

Prerequisites: approved tracked spec, passing plan review, and `harnessctl start-work`.

For each behavior slice:

1. Write one externally observable test.
2. State the **expected reason** the old implementation should fail.
3. Run RED through `harnessctl verify` and inspect output to confirm the observed failure matches that expected reason:

```bash
python3 harness/cli/harnessctl.py verify --id <WU-ID> --claim <EV-ID> --phase red --expect fail -- <targeted-command>
```

4. Implement the smallest vertical slice inside the approved write boundary.
5. Run GREEN:

```bash
python3 harness/cli/harnessctl.py verify --id <WU-ID> --claim <EV-ID> --phase green --expect pass -- <targeted-command>
```

6. Refactor only while green and rerun affected commands.
7. Run final or broader evidence for every required claim:

```bash
python3 harness/cli/harnessctl.py verify --id <WU-ID> --claim <EV-ID> --phase final
```

A RED receipt proves only that the command exited non-zero as expected; the worker/reviewer must still verify the failure reason. RED never satisfies completion. If the test cannot express the behavior, return to the plan rather than weakening the assertion.
