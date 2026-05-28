---
name: harness-compound
description: Convert repeated agent failures, review findings, failed handoffs, false completions, context bloat, platform changes, or maintenance costs into durable harness assets or pruning decisions. Use after a Work Unit or when a mechanism should be added, downgraded, or removed.
---

# Harness Compound

Compounding must reduce future entropy. Do not add mechanisms because they look professional.

## Decision options

```text
none | docs | adr | test | lint | ci | permission | hook | skill | controller-check | workflow | evaluator-rubric | deletion/pruning
```

## Mechanism test

Before adding or keeping a mechanism, answer:

```yaml
mechanism: ""
purpose: ""
failure_mode: ""
protected_invariant: ""
validation_method: ""
known_cost: ""
removal_condition: ""
owner: ""
```

Prefer tests, lint, CI, controller checks, or concise docs over adding always-on prompt text. If a mechanism has no traceable failure mode or removal condition, downgrade or delete it.
