# Harness Evaluation Benchmark

HEB evaluates whether the harness improves engineering reliability, not whether one model is smarter than another.

Compare:

```text
Agent A + Harness v0
Agent A + Harness v1
Agent A + Harness v1 without evidence gate
Agent A + Harness v1 without recovery
Agent A + Harness v1 without boundary guard
```

Do not compare different agents and different harnesses in the same conclusion unless the experiment is explicitly about agent selection.

## Minimal case set

- HEB-O-001: outcome correctness.
- HEB-E-001: evidence freshness.
- HEB-R-001: recovery after reset.
- HEB-A-001: ambiguity surfacing.
- HEB-S-001: scope and boundary.
- HEB-C-001: context routing.

## Result states

```text
PASS
PASS_WITH_WARNINGS
BLOCKED_GOOD
BLOCKED_BAD
FAIL
HARD_FAIL
```

A good harness is allowed to block work when the correct engineering action is to stop.

## Failure-trace regression cases

The generic v0.1 cases are supplemented by implementation regressions derived from real Harness failures:

- `HEB-E-002`: quoted/space-bearing argv round trip;
- `HEB-S-002`: compound-shell controller exception bypass;
- `HEB-R-002`: persistent Reviewer session and explicit takeover;
- `HEB-R-003`: linked-worktree identity isolation;
- `HEB-E-003`: post-review diff invalidation.

These cases should remain small and executable. Add another case only when a new failure trace is materially different from an existing one.
