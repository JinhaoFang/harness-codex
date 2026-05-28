# Reference Source Analysis

This file records what was copied, adapted, rejected, or deliberately simplified from the uploaded reference projects and external platform docs.

## Uploaded harness standard and tutorial

The implementation adopts these invariants:

- Work Unit Contract before non-trivial work.
- Bounded scope and explicit non-goals.
- Task-routed context instead of accumulated context.
- Separate truth sources for intent, project facts, execution, evidence, judgment, continuity, and memory.
- Fresh evidence or waiver before completion.
- Review separated from evidence.
- Cross-session recovery through controller state and handoff.
- Mechanisms introduced only with purpose, validation method, cost, and removal condition.

Design decision: this project implements a Controlled Repo Harness that can be thinned down or thickened up. It does not start with a scheduler.

## Official platform docs

Adapter decisions are locked to current official structures:

- Codex repo skills: `.agents/skills/<skill>/SKILL.md`, with `name` and `description` frontmatter.
- Codex subagents: `.codex/agents/*.toml`, using `developer_instructions` plus role-specific fields such as `model`, `sandbox_mode`, and `model_reasoning_effort`. The repo does not use `[agent] instructions_file = "AGENTS.md"`; Codex discovers `AGENTS.md` through its documented instruction-file chain.
- Claude Code project skills: `.claude/skills/<skill>/SKILL.md`; directory name is the slash-command name, `description` drives invocation, and `name` is display metadata.
- Claude Code project subagents: `.claude/agents/*.md` with markdown frontmatter and body prompt.

## grill-me

Useful pattern observed:

- Extremely short skill with a strong trigger description.
- Clarification is framed as relentless interview until shared understanding.
- If the answer can be found in code, the agent should inspect code instead of asking the user.

Adapted:

- `harness-clarify` uses the same compact interrogation stance, but grounds it in Work Unit readiness: deliverable, observable effect, completion definition, evidence, boundaries, and stop conditions.

Rejected:

- The original is intentionally broad and does not produce a controller-ready artifact; this harness requires handoff into `harness-spec`.

## Trellis brainstorm

Useful pattern observed:

- Task-first capture of ideas.
- Action-before-asking.
- Research-first for technical choices.
- One question per message.
- Diverge then converge to MVP scope.

Adapted:

- `harness-clarify` asks one high-value question at a time and inspects repo/offical sources before asking derivable questions.
- `harness-spec` freezes only the minimal contract needed for execution, rather than creating a heavy task system by default.

Simplified or rejected:

- Trellis creates task directories and PRDs early. This project keeps one Work Unit Contract as the default and only adds extra plan/feature docs when task complexity justifies them.

## harness-codex

Useful patterns observed:

- Explicit truth model for goal, workflow, and world facts.
- Deterministic controller separate from skills.
- Review/evidence separation.
- TDD overlay.
- Subagent handoff discipline.
- Role-specific Codex agents with `name`, `model`, `description`, `sandbox_mode`, `model_reasoning_effort`, and `developer_instructions`.

Adapted:

- Controller-owned state and gate checks.
- Request-review and submit-review lifecycle.
- Evidence receipts separated from review verdicts.
- Worker/reviewer role separation as the default subagent layer.
- GitHub collaboration wording for issue body, PR body, commit body, and traceability.
- Codex TOML agent files now use `developer_instructions`, not ad hoc `instructions`.

Simplified or rejected:

- Maintaining many `.agentdocs` files can make every task start with large context reads and manual document upkeep. This implementation uses one active Work Unit directory plus direct Work Unit reads; compressed briefings are optional diagnostics, not a substitute for `contract.md`.
- `plan.md` and `workflow.md` are collapsed into a Work Unit Contract and optional execution plan unless the task is complex enough to justify separate files.
- Explorer, planner, verifier, and monitor are not retained as resident subagents. Their responsibilities stay in skills, controller commands, hooks, or ordinary task routing until a concrete failure trace proves a separate role is needed.

## TDD references

Sources compared:

- `skills/tdd`
- `superpowers/skills/test-driven-development`
- `coding-agent-flow/.agents/skills/tdd`
- `harness-codex/.agents/skills/tdd`
- `agent-skills/skills/test-driven-development`

Common design principles:

- Write one failing behavior test before production code.
- Verify RED fails for the expected reason.
- Implement the smallest GREEN vertical slice.
- Refactor only while green.
- Prefer public interface / behavior tests over private implementation assertions.
- Bug fixes require a regression test first.
- TDD proof does not replace evidence receipt or close review.

Adapted:

- `harness-tdd` uses behavior-first vertical slices and maps test type to risk surface: regression, contract/schema, error-path, boundary, state-transition, or e2e.
- Evidence capture remains separate through `harness-evidence`.

Rejected:

- Strict universal TDD is not applied to pure docs, mechanical renames, generated artifacts, or exploratory spikes. Those require an explicit alternative evidence plan or waiver.

## agent-skills

Useful patterns observed:

- Large reusable skill catalog.
- Distinct roles such as code reviewer, security auditor, and test engineer.
- Commands for spec, plan, build, test, review, and ship.

Adapted:

- A small curated skill set focused on harness lifecycle, evidence, review, TDD, handoff, waiver, GitHub, and compounding.
- Plan/review/build/test patterns are represented as skills and controller commands rather than always-on subagents.

Simplified or rejected:

- Copying a large skill catalog wholesale would violate purpose-fit and increase discovery/context cost.
- Skills must not become lifecycle state authority.

## superpowers

Useful patterns observed:

- verification-before-completion.
- test-driven-development.
- writing-plans.
- subagent-driven-development.
- requesting-code-review and receiving-code-review.
- worktree guidance.

Adapted:

- fresh evidence gate;
- independent review workflow;
- strict "do not finish without evidence" language;
- TDD as the default method for behavior-changing work.

Simplified or rejected:

- Strict TDD should not become an unreviewed dogma for docs, mechanical changes, generated artifacts, or exploratory spikes.

## coding-agent-flow

Useful patterns observed:

- GitHub-first workflow with issues, branches, PRs, CI, and review.
- Distinct PO, QA, implementer, reviewer, and verifier roles.
- Worktree isolation and explicit development stages.
- TDD and PR checklists.

Divergence:

- Treating `AGENTS.md` as the source of truth conflicts with truth separation. In this implementation, `AGENTS.md` is only a context router.
- Flat task/progress files can become stale or manually expensive; this implementation keeps per-Work-Unit state and generates handoffs from controller-owned artifacts.
- Automatic completion or auto-merge requires strong evidence and review gates; this project leaves integration authority outside the agent.

## Bun / GitHub-first lesson

Current Bun repository signals informed the GitHub adapter, but were not copied mechanically:

- Bun keeps a large `CLAUDE.md` with concrete build/test routing. That confirms the value of repository-local validation entrypoints, but this implementation keeps the entrypoint shorter and moves detailed workflow guidance into `docs/harness/` to avoid always-on context bloat.
- Bun's active GitHub workflows show multiple CI/review surfaces around Claude-named branches and PRs. That supports treating GitHub issues, branches, PRs, CI, and comments as operational surfaces for agent-assisted work.

This implementation treats GitHub as a collaboration layer, not a replacement for Work Unit and evidence gates.

## General divergence rule

When an open-source implementation and the standard disagree, this project follows the standard's core invariants first. Implementation patterns are copied only when they reduce a named failure mode without introducing disproportionate context or maintenance cost.
