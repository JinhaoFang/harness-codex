---
name: harness-compound
description: Convert a repeated failure, review finding, recovery gap, platform change, or maintenance burden into the smallest durable asset—or remove a mechanism that has no demonstrated value.
---

# Harness Compound

Choose one outcome:

```text
none | docs | adr | test | lint | ci | permission | hook | skill | controller-check | workflow | deletion/pruning
```

Before retaining or adding a mechanism, record:

```yaml
purpose: ""
failure_mode: ""
protected_invariant: ""
validation_method: ""
known_cost: ""
removal_condition: ""
```

Prefer executable tests/checks and short routed guidance. Do not add always-on instructions without a concrete failure trace. The unused waiver path was removed for exactly this reason; reintroduce risk acceptance machinery only after a real case proves it necessary.
