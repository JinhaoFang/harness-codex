---
name: harness-clarify
description: Clarify a vague or non-trivial coding request one high-value question at a time, grounded in the current repository, before product-code implementation. Use when deliverable, observable behavior, non-goals, scope, evidence, approval, or risk is ambiguous.
---

# Harness Clarify

Do not implement product code during this skill.

1. Inspect the minimum relevant code, tests, docs, issues, and runtime facts before asking factual questions.
2. Restate the current deliverable, observable result, completion condition, and non-goals.
3. Identify only decisions that require human intent or tradeoffs.
4. Ask one high-value question at a time. Offer concrete options and a recommendation when useful.
5. After each answer, update the decision frontier and check whether the repository can answer the next gap.
6. Surface conflicts between requested intent and current code/docs instead of silently choosing.
7. Finish with a compact confirmed summary for `harness-spec`, update the single tracked Spec draft, and stop at explicit Spec approval. Do not implement or silently begin planning.

Ready summary:

```text
Deliverable:
Observable outcome:
Completion condition:
Non-goals:
Must preserve:
Write boundary:
Out of bounds:
Required evidence:
Stop / approval conditions:
Resolved decisions:
Remaining assumptions:
```

Readiness is not a confidence percentage. It means no unresolved question can materially change behavior, scope, evidence, or acceptance.
