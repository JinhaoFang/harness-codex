---
name: worktree-isolation
description: use when codex needs parallel or high-risk execution isolation through git worktrees, separate branches, or separate working directories, while keeping worktree state outside the runtime truth model.
---

# worktree-isolation

Use worktrees as execution infrastructure, not as task truth.

## Good use cases
- risky refactors that should not disturb the main working tree
- parallel subtasks handled by separate agents
- review reproduction in a clean working directory

## Runtime boundary
- worktree choice belongs to the execution workspace layer
- do not store worktree state as Goal truth or Process truth
- only record the minimum pointer in workflow events when it matters for traceability

## Suggested workflow
1. confirm the task gate is ready for the intended action
2. create a dedicated branch/worktree
3. perform the subtask in that isolated workspace
4. capture evidence from the real workspace used
5. keep runtime truth in `.agentdocs`, not in branch naming conventions alone

## Typical commands
```bash
git worktree add ../wt-<task-id>-<subtask-id> -b <branch-name>
cd ../wt-<task-id>-<subtask-id>
```

Optionally record a minimal event:

```bash
python .codex/tools/agentctl.py update-current   --task-id <task-id>   --event "subtask executing in isolated worktree <path-or-branch>"
```

## Do not
- do not require one worktree per task by default
- do not let worktree naming become the source of truth
- do not use one git working directory for multiple concurrent writers
