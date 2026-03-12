# 目录与命名约定

## 目录职责
- `.agentdocs/index.md`：入口地图与当前任务索引
- `.agentdocs/architecture/`：长期架构知识
- `.agentdocs/insights.md`：长期可复用坑点与技巧
- `.agentdocs/tasks/<task-id>/plan.md`：任务级规格真源
- `.agentdocs/tasks/<task-id>/workflow.md`：任务级执行状态真源
- `.agentdocs/archive/<task-id>/`：任务级归档区

## 命名约定
- task root：`.agentdocs/tasks/<task-id>/`
- workflow：`.agentdocs/tasks/<task-id>/workflow.md`
- plan：`.agentdocs/tasks/<task-id>/plan.md`
- task-id：建议使用 `YYMMDDHHMM`
- slug：小写英文 kebab-case

## active 约定
- `DEFAULT`：新会话默认先读的唯一 workflow
- `ACTIVE`：并行任务，仅在明确允许并行时保留
- 默认行为应偏保守：优先恢复已有 DEFAULT，而不是盲目新建
