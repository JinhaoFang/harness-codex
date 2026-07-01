# Harness Control Model

The Harness should be strict where failure is high-risk, irreversible, or falsely claims completion. It should stay light everywhere else.

The operating principle is:

```text
strong acceptance, weak steering
```

The Harness owns verifiable acceptance and high-risk boundaries. It does not micromanage ordinary local iteration.

## Control layers

### 1. Hard block

Use a blocking control only when one of these is true:

- the action is destructive, irreversible, or has external effects;
- the action crosses a security, secrets, auth, billing, deployment, or production-data boundary;
- the action would let one role fake another role's authority;
- the action would let the system claim acceptance without real evidence or review.

Examples:

- dangerous shell or infrastructure commands;
- reviewer/builder identity or session reuse;
- forged or stale evidence being treated as current acceptance proof;
- archiving or closing work without required acceptance gates.

### 2. Lifecycle gate

Use a lifecycle gate when the Harness is deciding what it may claim, record, or accept.

Lifecycle gates should constrain `harnessctl` conclusions. They should not freeze ordinary repository work.

Examples:

- `start-work` recording that implementation has formally started;
- `verify` recording fresh evidence;
- close review requiring the same logical reviewer session;
- `finalize-check` deciding whether the Work Unit is actually acceptable.

### 3. Advisory / observability

Use non-blocking controls for continuity, reminders, and context recovery.

Examples:

- checkpoint refresh before compaction;
- session-stop handoff reminders;
- subagent context injection;
- route/status guidance.

### 4. No control

The Harness should intentionally stay out of ordinary local execution that does not create high-risk effects and does not claim Harness acceptance.

Examples:

- branch cleanup and repository hygiene;
- local experimentation and iteration;
- ordinary edits and shell mutation;
- work that does not ask the Harness to certify a lifecycle transition or final outcome.

## Current mapping

| Surface | Layer | What it should do |
|---|---|---|
| `PreToolUse` | hard block, optional | intercept dangerous shell or tool usage early |
| `SubagentStart`, `PostCompact` | advisory | inject context and persist session observations |
| `PreCompact`, `Stop` | advisory | refresh checkpoints and remind about handoff |
| `start-work`, `resume-work` | lifecycle gate | record worker identity/session and formal implementation state |
| `verify` | lifecycle gate | execute approved checks and record fresh receipts |
| review track / close review | lifecycle gate | preserve reviewer continuity and acceptance separation |
| scope checks | lifecycle gate | decide whether acceptance can proceed for the current diff |
| `finalize-check`, `archive` | lifecycle gate / hard block | block unverified or unreviewed completion |
| platform sandbox / permissions | hard block | limit dangerous capability at execution time |

## What should not happen

These are anti-goals for the default Harness posture:

- a planning-state Work Unit freezing ordinary shell mutation;
- a hook acting like a resident scheduler or mandatory workflow engine;
- write-boundary controls blocking every edit before acceptance is even being claimed;
- platform hooks being treated as the only critical boundary;
- native subagent workflows depending on controller-managed dispatch as their normal path.

## Mechanism triage

Use this rule when reviewing or adding a mechanism:

1. If it protects a destructive or external-risk action, keep it as a hard block.
2. If it protects a Harness-owned claim of progress, evidence, review, or acceptance, keep it as a lifecycle gate.
3. If it improves continuity or visibility, make it advisory.
4. If it only restricts ordinary local iteration without protecting one of the cases above, remove it or make it opt-in.

## Profile guidance

- `thin-shared-codex` and `thin-shared-claude` are the recommended default profiles for flexible native-subagent use.
- Full `codex` and `claude` profiles add the local controller/core surfaces and optional hook hardening.
- `PreToolUse` should remain narrow even in full profiles. Repositories with stronger local guardrails may omit it entirely.

## Design consequence

When in doubt, move enforcement later and make it more authoritative:

- from pre-edit interception to `verify`, review, scope, and final acceptance;
- from prose instructions to controller-executed checks;
- from universal blocking to explicit opt-in hardening for dangerous operations.
