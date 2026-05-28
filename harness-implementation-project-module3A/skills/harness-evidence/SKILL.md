---
name: harness-evidence
description: Capture claim-relative evidence receipts and run the verification gate. Use after tests, typecheck, lint, runtime verification, manual QA, benchmark, migration dry-run, security scan, or any validation step that supports Work Unit completion; use when evidence is skipped so skipped is recorded honestly.
---

# Harness Evidence

Record what actually happened. A receipt is evidence only when it is linked to the current Work Unit, a required evidence claim, the current diff or equivalent CI artifact, and a reproducible command or artifact.

## Pass / fail

```bash
python3 harness/cli/harnessctl.py evidence   --id <WU-ID>   --claim <EV-ID>   --type test   --result pass   --command "<exact command>"   --command-log-ref ".harness/work-units/active/<WU-ID>/evidence/artifacts/<log>.txt"
```

Use the exact `EV-ID` from `contract.md`. For medium or higher risk, command text alone is not enough; include `command_log_ref`, `artifact_uri`, or `manual_artifact_ref` so a reviewer can inspect what happened.

## Skipped

```bash
python3 harness/cli/harnessctl.py evidence   --id <WU-ID>   --claim <EV-ID>   --type test   --result skipped   --note "Skipped requirement, reason, replacement evidence, risk impact, owner."
```

Skipped evidence is never pass evidence. If risk is accepted, create a scoped waiver. A skipped receipt must still name the skipped requirement, reason, replacement evidence, risk impact, and owner.

## Gate

```bash
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate verification --strict
```

Do not claim completion until this gate passes or returns only accepted scoped waiver warnings.
