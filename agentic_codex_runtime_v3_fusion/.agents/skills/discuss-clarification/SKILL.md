---
name: discuss-clarification
description: use when codex must clarify user intent before freezing goal truth. run this before freeze-plan whenever the task still has ambiguity around deliverable, observable effect, completion definition, non-goals, must-preserve requirements, approval points, deletion or migration conditions, or unresolved user decisions.
---

# discuss-clarification

Clarify the user's intent until the task is ready to freeze as Goal truth.

This skill exists because `DISCUSS` is not a vibe check.  
It is a structured clarification loop whose job is to remove the ambiguities that would otherwise poison `plan.md`.

## Purpose

Before `freeze-plan`, make sure the task is understood well enough that:

- the deliverable is explicit
- the observable effect is explicit
- the terminal completion definition is explicit
- the "looks busy but not done" outcomes are explicit
- the non-goals are explicit
- the must-preserve requirements are separated from `You decide`
- the approval points and stage boundaries are explicit
- deletion / migration / reclassification conditions are explicit when relevant
- unresolved user decisions are reduced to a controlled set
- a short discuss summary can be shown back to the user for confirmation

Do **not** treat a drafted plan as proof that DISCUSS is complete.

## Read first

Read only the minimum needed:

- the user's current request
- any recent user clarifications
- `AGENTS.md`
- `docs/agentic/spec/07-discuss-and-plan-contract.md`
- the current task's `workflow.md` if it exists
- the smallest amount of project context needed to speak accurately about the request (for example: `README`, package manifest, obvious entry files)

If repo/project reality still looks unclear after this, hand off to `$world-grounding`.  
Do not silently substitute repo guesses for user intent.

## Operating model

### Step 1: reflect the current understanding first

Before asking more questions, briefly restate:

- what you believe the user wants
- what the final deliverable seems to be
- what the visible outcome seems to be
- what still looks ambiguous

The user should be able to say "yes, that's right" or "no, that's not what I meant."

### Step 2: scan for readiness gaps

Check the task against these readiness dimensions:

1. **Deliverable**

   - what exact thing should exist at the end?
   - is the output format or artifact clear?

2. **Observable effect**

   - what will an external observer see?
   - what is the shortest demo sentence of success?

3. **Completion definition**

   - what counts as done?
   - what explicitly does **not** count as done?

4. **Requirement boundary**

   - what is in scope?
   - what is explicitly out of scope?
   - what is must-preserve?
   - what is still `You decide`?

5. **Execution boundary**

   - are stage order and stage boundaries explicit?
   - are there approval points or review-before-action constraints?
   - are there delete / migrate / reclassify guardrails?

6. **Evidence shape**

   - how will completion be proven?
   - what should later show up in plan verification / evidence?

7. **Open decisions**
   - what still needs explicit user confirmation?
   - are unresolved questions narrowing or still expanding?

### Step 3: ask only the highest-value questions

Ask **at most 2–3 questions per round**.

Rules:

- Ask the questions that remove the highest-risk ambiguity first.
- Prefer concrete contrast questions over vague "anything else?" prompts.
- Prefer questions that lock the terminal state, boundaries, and approval conditions.
- Avoid asking implementation questions too early when the deliverable itself is still fuzzy.

Good examples:

- "At the end of this task, is the expected deliverable a patched repo, a design proposal, or a packaged zip?"
- "What result would look substantial but still not count as complete?"
- "Which parts are fixed requirements, and which parts should the agent decide?"
- "For deletion or migration work, what must be reviewed or approved before anything is removed?"

### Step 4: update the understanding after each answer

After each user reply:

- tighten the current understanding
- collapse resolved ambiguities
- identify the next most important missing piece
- continue only if a meaningful gap remains

Do **not** ask another batch of questions without incorporating the user's last answers.

### Step 5: produce a discuss summary before freeze-plan

When readiness is high enough, present a short summary for confirmation.

The summary should cover:

- final deliverable
- observable effect
- completion definition
- what does not count as done
- non-goals
- must-preserve requirements
- `You decide` space
- approval points / stage boundaries / delete-or-migrate conditions if relevant
- remaining escalations, if any

This summary is the last checkpoint before `freeze-plan`.

## Handoff rule

Only hand off to `$freeze-plan` when both are true:

- **user-side readiness** is strong enough that the task shape is locked
- **project-side readiness** is strong enough that world grounding can support a real plan

If user intent is ready but repo reality is not, go to `$world-grounding`.  
If repo reality is ready but user intent is still ambiguous, stay in DISCUSS.

## Output shape

Return a concise result with:

- current understanding
- readiness gaps
- the 2–3 questions for this round

Or, if ready:

- a short discuss summary
- a clear statement that the task is ready for `$freeze-plan`

## Do not

- do not generate PRD / API / UI documents here
- do not score the task with a permanent numeric artifact
- do not create new long-lived task objects
- do not freeze Goal truth yourself
- do not ask more than 2–3 questions in one round
- do not confuse project grounding with user-intent clarification
