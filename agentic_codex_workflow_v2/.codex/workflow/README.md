# taskctl workflow scaffold

这个目录不是完整的 workflow engine，而是这套系统的 deterministic controller。

当前提供：

- `create-task`：初始化 task-scoped 目录与模板
- `check-transition`：检查状态迁移是否合法
- `advance-state`：推进 workflow 状态头，回填 owner / transition check / allowed next，并记录状态事件
- `make-pack`：生成 task pack
- `validate-pack`：校验 task pack 最低字段
- `emit-delegation-brief`：生成固定 6 段 sub-agent brief
- `record-review`：把 review 结论落位到 `reviews/*.json`，并可同步 workflow review section（含 `Materials Accessed`）
- `record-evidence`：记录 evidence bundle 到 `evidence/*.json`，并可同步 workflow evidence ledger
- `record-workflow-event`：写 workflow 文本并追加 `runtime-events.jsonl`
- `sync-index`：同步 `.agentdocs/index.md` 的 `DEFAULT/ACTIVE` 当前任务区
- `lint-skills`：检查 skills 基础结构
- `archive-task`：把 task bundle 移到 archive/，并更新 active/archive index

目标：

- 减少结构化工件的重复文本
- 减少 review / evidence / event 的自由拼接
- 为后续可视化观测提供稳定机读输入
