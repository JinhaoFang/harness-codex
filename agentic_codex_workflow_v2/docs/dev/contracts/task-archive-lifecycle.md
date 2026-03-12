# Task Archive Lifecycle Contract

> 这份契约解决的不是“要不要保留历史”，而是“task-scoped 工件不该永久占着热路径”。V2 不做信息压缩；只把**跟任务绑定的工件**整体归档，让长期知识继续留在热路径。

## 1. task-scoped 工件
以下内容跟随任务创建，也应跟随任务归档：
- `workflow.md`
- `plan.md`
- `task-packs/`
- `reviews/`
- `evidence/`
- `scratch/`
- task-local manifests / packets

## 2. 长期工件
以下内容不跟着单任务移动，继续留在热路径：
- `.agentdocs/index.md`
- `.agentdocs/architecture/*`
- `.agentdocs/insights.md`
- 长期 canonical backend / PRD / migration map / triage map

## 3. 推荐目录
### Active
`.agentdocs/tasks/<task-id>/`

### Archived
`.agentdocs/archive/<task-id>/`

## 4. 归档触发条件
- `CLOSE_REVIEW = PASS`
- `archive-task` 执行成功
- active index 已更新

## 5. 归档动作
1. 记录 close reviewer 的最终结论
2. 将 task-scoped 目录整体移动到 archive
3. 将 task bundle 内部的 task-scoped 路径从 `.agentdocs/tasks/<task-id>/` 重写为 `.agentdocs/archive/<task-id>/`
4. 更新 active index（`.agentdocs/index.md`）与 archive index（`.agentdocs/archive/index.md`）
5. 在热路径只保留必要 backlink（若有）

## 6. 兼容 legacy
- 旧布局 `.agentdocs/workflows/`、`.agentdocs/plans/`、`.agentdocs/evidence/`、`.agentdocs/scratch/` 继续保留
- 新设计不强制清理旧资料
- 若需要用旧任务验证 V2，可以先保持 legacy 文件不动，只对新任务启用 task-scoped 生命周期

## 7. 禁止事项
- 未通过 `CLOSE_REVIEW` 就把任务移入 archive
- 为了“看起来整洁”删除 evidence 或 review 记录
- 把长期 SoT 跟着单任务一起挪走
