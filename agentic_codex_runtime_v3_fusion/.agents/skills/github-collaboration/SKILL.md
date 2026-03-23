---
name: github-collaboration
description: use when codex needs optional github issue or pr synchronization for traceability, review communication, or external collaboration, while keeping `plan.md`, `workflow.md`, reviews, and evidence as the source of truth.
---

# github-collaboration

Use GitHub as an external mirror, not as task truth.

## Suitable cases
- create or update an issue that mirrors a grounded task
- attach progress or review summaries to an existing issue/pr
- prepare a PR review/closure comment from runtime truth
- keep external stakeholders informed without moving truth out of the repo

## Read first
- current `plan.md`
- current `workflow.md`
- relevant review/evidence refs
- the minimum code/test context needed for accurate wording

## Runtime boundary
- task truth stays in `plan.md`, `workflow.md`, reviews, and evidence
- GitHub refs are mirrors for collaboration and traceability
- do not let issue/PR text overrule current repo truth

## Minimal traceability writeback
When a GitHub issue or PR becomes relevant, record it in workflow pointers:

```bash
python .codex/tools/agentctl.py update-current   --task-id <task-id>   --external-ref "gh:issue#123"   --external-ref "gh:pr#456"   --event "github refs linked"
```

## Suggested flow
1. make sure the task is already grounded and has a real `plan.md`
2. create/update the GitHub object using `gh` only if the repo actually uses GitHub for this task
3. mirror concise, current facts from runtime truth
4. record the external refs back into workflow
5. keep comments short and traceable; prefer file/ref links over long summaries

## GitHub writing conventions

### Issue body
When mirroring a grounded task into GitHub, prefer this structure:

```markdown
## Background
- what problem or change triggered this task

## Goal
- the grounded deliverable
- the observable effect

## Acceptance Criteria
- [ ] concrete, externally checkable result
- [ ] concrete, externally checkable result

## Validation
- Test: `<real command>`
- Or behavior/screenshot/log proof: `<real evidence path or step>`

## Runtime refs
- Plan: `.agentdocs/tasks/<task-id>/plan.md`
- Workflow: `.agentdocs/tasks/<task-id>/workflow.md`
```

### Progress comment
Prefer short progress updates backed by current runtime truth:

```markdown
## Progress
- Completed: ...
- Verified by: `<real command or evidence ref>`
- Next: ...
```

### PR body
Prefer this structure:

```markdown
## Summary
- what changed

## Testing
- Test: `<real command>`
- Evidence: `<evidence-ref>`

## Traceability
- Plan: `.agentdocs/tasks/<task-id>/plan.md`
- Workflow: `.agentdocs/tasks/<task-id>/workflow.md`
- Refs: `gh:issue#123`
```

Use `Closes #123` only when the PR is actually intended to close the issue.

## Git timing conventions
- Create a branch only after `plan-review` passes and the task is truly entering implementation.
- Prefer branch names tied to the collaboration object when one exists, for example `issue-123` or `task-<slug>`.
- Do not commit before a meaningful local verification step exists for that slice.
- Prefer one verified slice per commit instead of one giant end-of-task commit.
- Prefer commit subjects in the form `feat: ...`, `fix: ...`, `refactor: ...`, `docs: ...`, `test: ...`, `chore: ...`, or `TDD: ...`.
- If the work is linked to a GitHub issue, put `Refs: #123` in the commit body; reserve `Closes #123` for the final PR or final closing commit when appropriate.

## Do not
- do not require GitHub for every task
- do not create a second task ledger in issue comments
- do not turn `agentctl.py` into a GitHub orchestration layer
