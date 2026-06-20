---
name: harness-evidence
description: Run tests, type checks, lint, runtime probes, benchmarks, or other executable validation through the controller so pass/fail is observed rather than self-reported. Use during TDD and before close review.
---

# Harness Evidence

Use `harnessctl verify` through the repository script. Do not manually provide `result=pass`: the controller launches the argv declared by the approved spec, captures stdout/stderr and exit code, and binds the receipt to the approved spec, reviewed plan, and current implementation content.

```bash
python3 harness/cli/harnessctl.py verify \
  --id <WU-ID> \
  --claim <EV-ID> \
  --type test \
  --phase final \
  --expect pass
```

Then run:

```bash
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate verification --strict
```

If a required command cannot execute, use `record-skipped` to expose the blocker. A skipped record is not evidence and cannot satisfy completion. Produce the check, revise and reapprove the evidence contract, or leave the Work Unit blocked.
