---
name: harness-clarify
description: Clarify ambiguous or non-trivial coding work through repo-grounded, one-question-at-a-time interaction before implementation. Use when user intent, deliverable, observable outcome, completion definition, non-goals, write boundary, evidence shape, approval point, deletion/migration condition, or risk acceptance is unclear; use before freezing a Work Unit Contract or Codex Goal.
---

# Harness Clarify

Interview the user and the repository until the task can be frozen as a bounded Work Unit. Do not implement during this skill.

Core rule: ask only questions that cannot be answered by inspecting the repo, docs, config, tests, runtime, or official sources. If a question can be answered by exploration, explore first and report the finding.

This skill is interaction, not a separate lifecycle gate. The controller already owns readiness through `harnessctl check --gate spec` and `harnessctl lock --status ready`.

## Grill-style interaction loop

1. Restate the current understanding in concrete terms:
   - requested deliverable;
   - observable effect;
   - completion definition;
   - what would look busy but still not count as done.
2. Inspect the minimum project context needed to avoid asking lazy questions.
3. Identify decision gaps:
   - scope / non-goals;
   - must-preserve constraints;
   - write boundary / out-of-bounds;
   - required evidence;
   - approval or stop conditions;
   - unresolved product or risk decisions.
4. Ask one high-value question at a time. Use 2-3 concrete options when possible and include your recommended answer.
5. Wait for the user answer before asking the next user-dependent question.
6. After each answer, update the understanding and re-check whether any remaining gap can be answered from the repo.
7. Pressure-test the answer with a concrete scenario when ambiguity is likely to cause wrong implementation.
8. When ready, produce a short confirmation summary and hand off to `harness-spec`.

## Repository-grounded questioning

Prefer repo exploration over user questions when the answer is factual:

- existing architecture, module ownership, and local conventions;
- current test command or package manager;
- public API shape and import boundary;
- documented product behavior;
- current implementation behavior.

Ask the user when the answer is a human intent, product tradeoff, risk acceptance, or scope decision.

## Surface conflicts

Immediately call out:

- user intent that conflicts with current repo behavior or docs;
- terminology that conflicts with glossary or code names;
- evidence that cannot prove the requested claim;
- scope that crosses an out-of-bounds or high-risk boundary;
- a requested completion condition that depends on unavailable environment or authority.

Do not hide these conflicts by silently choosing an interpretation.

## Do not

- Do not ask broad questionnaires.
- Do not ask "should I search?" when repository or official sources are available.
- Do not freeze the Work Unit while deliverable, completion, evidence, or boundary is still ambiguous.
- Do not implement during clarify.
- Do not let implementation preferences override user intent.
- Do not invent readiness fields such as `clarification_ready`; unresolved questions belong in `## Open questions`, and lifecycle readiness belongs in `state.json`.

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
Resolved decisions:
Remaining assumptions, if any:
```
