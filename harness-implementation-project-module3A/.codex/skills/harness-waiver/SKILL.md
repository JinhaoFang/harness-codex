---
name: harness-waiver
description: Create scoped human-approved waivers for missing evidence, skipped checks, risk acceptance, or deadline exceptions. Use when required evidence cannot be produced, when replacement evidence is weaker than required, or when a high-risk gate must be explicitly accepted by an accountable human.
---

# Harness Waiver

A waiver is judgment truth, not evidence. It must be scoped to one requirement or risk and must not satisfy unrelated evidence.

```bash
python3 harness/cli/harnessctl.py waiver   --id <WU-ID>   --waiver-type evidence   --approved-by human:<owner>   --requirement <EV-ID>   --reason "Why this cannot be verified now"   --replacement-evidence "What was done instead"   --risk-accepted "Concrete risk accepted"   --expires-at "YYYY-MM-DD"
```

Before using a waiver:

- confirm skipped receipt is recorded as `skipped`, not `pass`;
- confirm the waiver requirement exactly matches the missing evidence ID;
- confirm the owner is a human accountable for the risk;
- confirm expiry or revisit condition exists for non-trivial risk.
