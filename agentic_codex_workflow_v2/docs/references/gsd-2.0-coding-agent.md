# How We Built The World's Most Powerful Coding Agent

> Source: [GSD on X](https://x.com/gsd_foundation/status/2030361888681239003)

GSD is a system for getting large, multi-session projects done with AI coding agents. Not toy demos. Not "build me a landing page." Real projects — the kind with many files, multiple subsystems that need to talk to each other, and enough scope that no agent is finishing it in one context window.

The problem it solves is simple to describe and brutal in practice: agents lose coherence over time. They forget what they built three tasks ago. They produce files that exist but don't actually work. They burn tokens re-reading project structure every turn. They can't resume after an interruption without the human re-explaining everything. And when something breaks, there's no clean way to roll back.

GSD 2.0 addresses all of this. Here's how.

---

## 1. Three-Level Hierarchy

Everything decomposes into three levels:

- **Milestones** are shippable versions — the big thing you're building.
- **Slices** are independently demo-able vertical capabilities. Not "implement the database layer" (horizontal) but "user can sign up and log in" (vertical). Each slice has a demo sentence: "After this, the user can ___." If you can't fill in that blank with something a human can observe, the slice is scoped wrong.
- **Tasks** are context-window-sized units of work. One task fits in one agent session. If it doesn't fit, it's two tasks. This is an iron rule because violating it is where agents start losing coherence — they've been working for so long that early decisions have been compacted away, the context is polluted with dozens of old tool calls, and the model's reasoning degrades.

This hierarchy isn't just organizational. Each level has specific artifacts, specific verification criteria, and specific compression mechanisms that keep downstream work informed without blowing up context.

---

## 2. Boundary Maps

This is maybe the single most impactful planning feature.

When a milestone is planned, every slice declares what it produces and what it consumes from upstream slices. Not vaguely — concretely. Functions, types, interfaces, endpoints, with names.

```
S01 → S02
Produces:
* types.ts → User, Session, AuthToken (interfaces)
* auth.ts → generateToken(), verifyToken(), refreshToken()
Consumes: nothing (leaf node)

S02 → S03
Produces:
* api/auth/login.ts → POST handler
* middleware.ts → authMiddleware()
Consumes from S01:
* auth.ts → generateToken(), verifyToken()
```

This forces the agent to think about interfaces before writing implementation. When slice 3 is being planned, it doesn't have to guess what slice 1 built — the boundary map says exactly what's available and the planning step verifies that the upstream slice actually produced what the map claims.

No more "slice 3 needs a function that slice 1 never exported." No more silent assumptions about what exists. The contracts are explicit and checked.

---

## 3. Deterministic Code vs LLM Reasoning

This is the core architectural principle and the main reason the system is token-efficient and reliable.

**The rule:** If you could write an if-else that handles it correctly every time, it must be deterministic code — not LLM reasoning. Every token the model spends on mechanical operations is a token wasted and a failure mode introduced.

### What deterministic code handles:

- All git operations (branching, checkpoints, commits, squash merges, rollback)
- All state transitions (next task, complete task, complete slice, advance)
- File parsing and formatting (reading and writing all the markdown artifacts)
- Directory scaffolding (creating the right folders and files with correct frontmatter)
- State derivation (reconstructing current position from the files on disk)
- Context assembly (loading summaries, budgeting tokens, dropping old context)
- Static verification (checking that files exist, exports are present, imports are wired, stubs are detected)

### What the LLM handles:

- Decomposing scope into slices (architectural judgment)
- Decomposing slices into tasks (scoping judgment)
- Writing must-haves (understanding what observable outcomes matter)
- Discussing gray areas with the user (interpreting intent)
- Scouting the codebase during research (judging relevance)
- Diagnosing verification failures (abductive reasoning)
- Writing summaries (compressing what happened and why it matters)
- Actually writing the code

The LLM does judgment work. Deterministic code does everything else. The agent never constructs a git command. It never parses markdown to figure out which task is next. It never formats frontmatter. It calls a tool, gets a result, and moves on to the creative work.

Two tools expose the entire deterministic layer: `gsd_manage` (18 actions for state, git, scaffolding, context) and `gsd_verify` (4 actions for static verification). One tool call replaces what would otherwise be 5-10 bash/read/edit calls that the model has to reason about.

---

## 4. Anchor Pruning (Context Rot Elimination)

This changes everything about multi-task reliability.

Each task gets an invisible anchor message injected into the conversation. Before every LLM call, a context hook prunes the message history back to the current task's anchor.

**What this means in practice:** task 5 doesn't see the 40 tool calls from tasks 1-4. It doesn't see the failed attempts, the intermediate reads, the debugging from prior work. It gets a clean context window containing its task plan, relevant upstream summaries, and nothing else.

### Without this, you get context rot — the silent killer of multi-task agent work.

By task 3 or 4 in a slice, the context window is saturated with stale tool output from earlier tasks. File contents the model read four tasks ago that have since been refactored. Debugging traces from problems that were already fixed. Hundreds of lines of terminal output from builds and test runs that are no longer relevant. The model doesn't know what's current and what's stale — it's all just tokens in the window. So it starts making decisions based on outdated information. It references variables that were renamed. It follows patterns from code that was restructured. It avoids approaches it tried earlier that failed for reasons that no longer apply. The reasoning quality drops steadily as the signal-to-noise ratio in the context collapses.

This is why most agent systems hit a wall around task 3-4 in a sequence. It's not that the model got dumber — it's that the context got poisoned. Every new task is dragging along the corpse of every prior task's exploration, dead ends, and intermediate state.

**Anchor pruning eliminates context rot entirely.** Every task gets a clean window. The only things in context are the current task plan and curated upstream summaries. No stale reads, no old tool calls, no accumulated noise. Task 7 runs with the same context quality as task 1.

---

## 5. Pre-Assembled Context

Before a task starts, the system pre-assembles everything the agent needs:

- The task plan (goal, steps, must-haves)
- Compressed summaries from dependency slices
- Milestone-level context and decisions
- Continue-here data if resuming interrupted work

This is injected automatically. The agent never has to `grep` for project structure, `read` state files to figure out where it is, or search for what was built in prior slices. If it does, the context assembly is broken — that's a bug, not a workflow.

**The goal is zero discovery calls.** Every token the agent spends on "where am I, what exists, what was decided" is a token not spent on actual implementation.

---

## 6. Hierarchical Summaries

When a task completes, the agent writes a structured summary: what was built, key decisions made, files modified, patterns established, and what downstream work should know about.

When a slice completes, task summaries compress into a slice summary. When enough slices are done, slice summaries compress into a milestone summary. Each level includes drill-down paths to the level below if more detail is needed.

When planning slice 6, you don't load 15 individual task summaries from slices 1-5. You load one milestone summary — maybe 200 lines — that contains the essential information: what was built, what's available, what patterns to follow, what decisions were locked.

The token budget for injected summary context is capped at ~2500 tokens. If the dependency chain is too large, the oldest and least relevant summaries are dropped first. Milestone-level summaries take priority over slice-level, which take priority over task-level.

**One critical rule:** never summarize summaries. Each summary level regenerates from the level below plus actual code state. A slice summary comes from task summaries, not from a compressed version of a prior slice summary. This prevents the compounding information loss you get when you keep compressing compressed text.

---

## 7. Must-Haves & Verification

"All steps done" is not verification. Checking the actual outcomes is.

Every task defines **must-haves** — not a checklist of steps, but observable criteria:

- **Truths** are behaviors that must be true: "User can sign up with email and password." "Login returns a JWT token." "The CLI outputs results to stdout." These require the agent to actually run commands, check browser behavior, or read output to confirm.
- **Artifacts** are files that must exist with real implementation: `src/lib/auth.ts` — JWT helpers, minimum 30 lines, exports `generateToken` and `verifyToken`. Not "auth.ts exists" but "auth.ts exists, has enough substance to be real, and actually exports the functions it's supposed to."
- **Key links** are wiring between artifacts: `login/route.ts` imports `generateToken` from `auth.ts`. `middleware.ts` imports `verifyToken`. This catches the most common agent failure mode — files that exist independently but aren't actually connected to each other.

Static verification checks all of this deterministically: file existence, line counts, export detection, import wiring, and stub detection. The stub detector scans for TODO comments, FIXME markers, `return null`, `return {}`, `console.log` placeholders, hardcoded empty responses. An 8-line file that returns an empty object doesn't pass.

### 4-Tier Verification Ladder:

1. **Static** — files exist, exports present, wiring connected, no stubs
2. **Command** — tests pass, build succeeds, lint is clean
3. **Behavioral** — browser flows work, API responses are correct
4. **Human** — the user checks only when the agent genuinely can't verify itself

Each task picks the strongest tier it can reach. The agent doesn't ask a human to check something it can verify with a curl command.

---

## 8. Discussion Phase

This is one of the most underrated features in the system, and it's the reason GSD can run largely hands-off without building the wrong thing.

**The core problem with most AI coding agents:** you say "build me auth" and they immediately start writing code. They make 30 decisions in the first 5 minutes — session storage vs JWT, email verification vs none, OAuth vs password-only, redirect behavior, error message format — and you don't find out which choices they made until you're looking at the finished result wondering why it doesn't match what you had in mind.

GSD makes discussion a first-class phase. Before planning starts, the agent reads the scope, identifies the gray areas — places where multiple reasonable approaches exist and your preference actually matters — and interviews you about them. Not generically. It generates specific questions about concrete decisions and presents structured choices: "Session handling: (a) JWT with refresh rotation, (b) server-side sessions with Redis, (c) your call."

It's a thinking partner, not a checklist interviewer.

### Key behaviors that make this work:

- **It follows energy.** Whatever you emphasize, it digs into. If you spend time talking about the error handling experience, it asks deeper questions about that. It doesn't robotically march through a predetermined list.
- **It challenges vagueness.** "Make it simple" gets pushed back on. Simple how? Simple for the user? Simple to implement? Simple to extend later? The agent won't accept fuzzy answers because fuzzy input produces divergent output.
- **It makes the abstract concrete.** "Walk me through using this." "What does that actually look like on screen?" "What happens when this fails?" These questions force clarity before a line of code is written.
- **Scope guardrails prevent drift.** If you suggest a feature that belongs in a different slice, it captures the idea as deferred and redirects: "That sounds like a new capability — I'll note it for later. For now, let's focus on the auth flow."

The output is a `context.md` file — a structured record of every decision with your reasoning. This file gets injected into all downstream work: planning, execution, verification, everything. When the agent is implementing task 4 of slice 2, it still has your discuss-phase decisions in context. It doesn't re-debate them. It doesn't silently make a different choice because it forgot what you said. The decisions are locked and flow through the entire pipeline.

**This is what makes hands-off execution possible.** You front-load alignment in a 10-minute conversation, and every task that follows inherits those decisions automatically. The alternative — interrupting the agent mid-implementation to correct course — is dramatically more expensive in both tokens and time.

---

## 9. Research Phase

Also optional. Before planning a slice, the agent can scout the codebase and relevant library docs.

The output is a `research.md` with two sections that prevent the most expensive mistakes:

- **Don't Hand-Roll** identifies problems that look simple but have existing solutions. "Don't build your own JWT validation — use jose."
- **Common Pitfalls** documents what goes wrong, why, how to avoid it, and warning signs. Informed by library docs, codebase patterns, and known failure modes.

This research gets injected into the planning phase, so task decomposition and must-haves account for real-world constraints instead of idealized assumptions.

---

## 10. Git Workflow

Each slice gets its own git branch. On that branch, every task gets a checkpoint commit before it starts and a proper commit after verification passes. When the slice is done, the branch squash-merges to main as one clean commit.

**Main reads like a changelog:**

```
feat(M001/S06): verification + summarization + UAT
feat(M001/S05): task execution + context pruning
feat(M001/S04): milestone and slice planning commands
feat(M001/S03): extension scaffold and command routing
feat(M001/S02): state machine + deterministic operations
feat(M001/S01): types + file I/O + git operations
```

One commit per slice. Individually revertable. The branch is kept for per-task history — git log, git bisect, git blame all work against the granular commits.

### Rollback is straightforward:

- **Bad task** → `git reset` to the checkpoint on the branch
- **Bad slice** → revert the single squash commit on main
- **UAT failure after merge** → fix tasks go on a `-fix` branch, squash merge as `fix(M001/S01): what was fixed`

The user never runs a git command. The agent handles all branching, committing, merging, and archiving through deterministic tool calls.

---

## 11. Interruption Handling

Context windows end. Sessions time out. Users hit Ctrl+C. The system handles all of it.

If a task is interrupted — by compaction, session end, or manual stop — the system writes a continue file capturing:

- What's already completed
- What remains to be done
- Decisions made during the task (so the next session doesn't re-debate them)
- The "vibe" — what was tricky, what to watch out for
- The exact first thing to do when resuming

A fresh session reads this file, loads the task plan, injects both into context, and picks up from exactly where it left off. The continue file is consumed on resume — it's ephemeral, not a permanent record.

This is hooked into Pi's compaction event, so if the runtime auto-compacts the conversation, the continue file is written automatically before the compaction happens. No work is lost.

---

## 12. User Acceptance Tests (UAT)

Here's a question that should bother anyone using AI coding agents: when the agent says "done," how do you actually know?

You can read the code. You can check that files exist. But for most people, the real question is: does it actually work the way I asked? Can I go use it and see the thing I was promised?

GSD generates this automatically. Every time a slice completes, the system produces a User Acceptance Test script — a human-readable document that tells you exactly how to verify what was built. Not as an afterthought. Not as something you have to ask for. It's baked into the completion flow. Finish a slice, get a test script.

These aren't implementation details. Not "verify that generateToken returns a valid JWT" — the automated verification already checked that. UATs are about what you, the human, can observe:

```
Test: Sign up flow
Do:
1. Open http://localhost:3000/signup
2. Enter "test@example.com" in the Email field
3. Enter "password123" in the Password field
4. Click "Sign Up"
Expected:
* Page redirects to http://localhost:3000/dashboard
* Header shows "Welcome, test@example.com"
* Refreshing the page keeps you logged in
```

Every step is a copy-pasteable command or a specific UI action. Every expected result describes exactly what you should see — not "it should work" but the specific text, the specific URL, the specific behavior. You should never have to wonder "what's the command?" or "what page do I go to?" or "what does success look like?"

The tests are derived from the slice's demo sentence and must-haves, cross-referenced against what the task summaries say was actually built. They're the bridge between "the agent says it's done" and "I can see with my own eyes that it's done."

And critically, **UATs are non-blocking.** The agent writes the test script and immediately moves on to the next slice. You test whenever it's convenient — between slices, at the end of a milestone, whatever works for your workflow. If you find issues, you tell the agent, and it creates fix tasks. No waiting. No ceremony. Just a document sitting there whenever you want to verify.

At any given point in a project, you have a UAT file for every completed slice. It's an automatic paper trail of "here's what was built and here's how to prove it." That's not just useful for trust — it's useful for onboarding, for demos, for remembering what the thing does three weeks later.

---

## Summary

The fundamental insight is that most of what makes AI coding agents unreliable isn't the model's code generation — it's everything around it. State management, context pollution, lost continuity, mechanical errors in git operations, verification that checks process instead of outcomes, summaries that lose information through compounding compression.

GSD 2.0 makes all of that deterministic. The model writes code and makes judgment calls. Everything else — the state transitions, the file management, the git operations, the context assembly, the static verification — is handled by TypeScript that either works correctly or throws a clear error.

**The result is an agent that:**

- Gets a fresh, relevant context window for every task
- Never wastes tokens on mechanical operations
- Produces verifiable outcomes, not just completed checklists
- Survives interruptions and session boundaries transparently
- Maintains a clean, revertable git history automatically
- Scales its memory through compression instead of re-reading everything

All backed by markdown files on disk. No database. No external service. Just files and git.
