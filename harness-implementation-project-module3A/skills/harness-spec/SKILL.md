---
name: harness-spec
description: Create, lock, or amend a Work Unit Contract from clarified intent. Use after clarification or issue analysis when a non-trivial task needs frozen intent, scope, success conditions, required evidence, stop conditions, and context pointers before planning or implementation.
---

# Harness Spec

Create the smallest contract that lets an agent, reviewer, and controller agree on the same task truth.

## Rules

- Contract owns user intent, scope, success, required evidence, and stop conditions.
- Contract does not own lifecycle status; `state.json` is the lifecycle authority. Do not add `status:` to the contract header.
- Execution plans, feature lists, Codex Goals, briefings, and agent summaries do not override the contract.
- The agent should read `contract.md` directly before implementation. Do not replace it with a compressed briefing.
- Scope, success, risk, or required evidence changes require an explicit contract amendment before implementation continues.
- Keep contract content checkable; avoid vague evidence like "verify it works".
- Do not proceed while open questions, placeholders, missing write boundary, missing required evidence, or missing stop conditions block the spec gate.

## Procedure

1. Read the clarification summary and current repo context pointers.
2. Create or update the Work Unit:

```bash
python3 harness/cli/harnessctl.py new --id <WU-ID> --title "..." --type <type> --risk <risk>
```

3. Fill `contract.md` with:
   - intent;
   - expected outcome;
   - non-goals;
   - likely changed areas;
   - write boundary;
   - out-of-bounds;
   - required evidence IDs and commands;
   - success / blocked stop conditions;
   - resolved open questions or `- none`;
   - context pointers.
   Do not add lifecycle `status` to the YAML header; readiness is set by `harnessctl lock`.
4. Run the spec gate and lock the Work Unit before implementation:

```bash
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate spec --strict
python3 harness/cli/harnessctl.py lock --id <WU-ID> --status ready
```

5. If the locked contract changes, record the amendment after editing `contract.md`:

```bash
python3 harness/cli/harnessctl.py amend --id <WU-ID> --field scope --reason "..." --summary "..."
```

After amendment, request a new plan review before running because the plan must match the current contract.
