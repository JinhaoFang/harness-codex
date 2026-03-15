---
name: dev-workflow-bootstrap
description: |
  用于初始化或恢复 task-scoped `.agentdocs` 工作台的 bootstrap skill。
  Use when a high-entropy task needs a new `.agentdocs/tasks/<task-id>/` root, or when must resume the current active task,
  while preferring controller-backed creation over ad-hoc manual scaffolding.
---

# Dev Workflow Bootstrap

先确定是创建新 task root，还是恢复当前唯一活动 task。

## Procedure

- 优先运行 `python .agents/workflow/taskctl.py create-task` 创建 task-scoped workflow、plan 与子目录。
- 阅读 `references/directory-and-naming-conventions.md`，再决定 task id、slug 与目录落位。
- 只在检查 scaffold 输出时读取 `assets/index-template.md`、`assets/architecture/index-template.md` 与 `assets/insights-template.md`。
- 仅把 `scripts/bootstrap_workflow.py` 当作当前 task-scoped bootstrap 的兼容 wrapper。
- 仅把 `scripts/validate_workflow_state.py` 用作 workflow sanity check。

## Boundary

- 一次只创建或注册一个 task-scoped root。
- 不要手工拼接冲突的 DEFAULT / ACTIVE 条目或 archive 目录结构。

## Escalate

- 在 task root 已存在且非空、存在多个 DEFAULT、或没有唯一活动任务时，停止并要求显式恢复或覆盖。
