---
name: harness-evidence
description: Run tests, type checks, lint, runtime probes, benchmarks, or other validation through the controller so pass/fail is observed, claim-relative, and fresh.
---

# Harness Evidence

Use `harnessctl verify`; never self-report `result=pass`. The controller resolves the approved `check_id`, executes its structured `argv[]`, captures stdout/stderr and exit code, and binds the receipt to the current Spec, reviewed plan, check definition, repository/workspace, HEAD, and implementation diff.

```bash
harnessctl verify \
  --id <WU-ID> --claim <EV-ID> --type test --phase final
harnessctl check \
  --id <WU-ID> --gate verification --strict
```

Optional argv after `--` is an exact equality assertion; it is not a replacement shell command. Use `record-skipped` only to expose an unavailable check. Skipped is not pass or waiver and leaves the Work Unit blocked.

Once all final claims are fresh, trigger Close Review rather than waiting for another prompt. For Codex, resume the native reviewer subagent from Plan Review; for Claude/manual adapter flows, call `advance`. Controller-executed verification remains authoritative in either path.
