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

## Do not
- do not require GitHub for every task
- do not create a second task ledger in issue comments
- do not turn `agentctl.py` into a GitHub orchestration layer
