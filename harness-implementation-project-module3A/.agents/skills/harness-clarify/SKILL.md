---
name: harness-clarify
description: Clarify ambiguous or non-trivial coding work before implementation. Use when user intent, deliverable, observable outcome, completion definition, non-goals, write boundary, evidence shape, approval point, deletion/migration condition, or risk acceptance is unclear; use before freezing a Work Unit Contract or Codex Goal.
---

# Harness Clarify

Interview the user and the repository until the task can be frozen as a bounded Work Unit. Do not implement during this skill.

Core rule: ask only questions that cannot be answered by inspecting the repo, docs, config, tests, or official sources. If a question can be answered by exploration, explore first and report the finding.

## Loop

1. Restate current understanding in concrete terms:
   - requested deliverable;
   - observable effect;
   - completion definition;
   - what would look busy but still not count as done.
2. Inspect the minimum project context needed to avoid asking lazy questions.
3. Identify readiness gaps:
   - scope / non-goals;
   - must-preserve constraints;
   - write boundary / out-of-bounds;
   - required evidence;
   - approval or stop conditions;
   - unresolved product or risk decisions.
4. Ask one high-value question at a time. Use 2-3 concrete options when possible and include your recommended answer.
5. After each answer, update the understanding before asking again.
6. When ready, produce a short confirmation summary and hand off to `harness-spec`.

## Do not

- Do not ask broad questionnaires.
- Do not ask "should I search?" when repository or official sources are available.
- Do not freeze the Work Unit while deliverable, completion, evidence, or boundary is still ambiguous.
- Do not let implementation preferences override user intent.

## Ready summary

```text
Deliverable:
Observable effect:
Completion definition:
Non-goals:
Must-preserve:
Write boundary:
Out-of-bounds:
Required evidence:
Approval / stop conditions:
Remaining assumptions, if any:
```
