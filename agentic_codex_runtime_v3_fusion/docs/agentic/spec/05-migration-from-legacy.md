# 从旧规范迁移

## 1. 迁移目标

不是推倒重来，而是完成三件事：

1. 减重
2. 去重复
3. 重新分配权力

## 2. 旧规范中保留的部分

保留：
- deterministic controller 方向
- review / evidence 分离
- 先理解、再计划、再实现、再复核的总门禁
- 多 agent 角色分离
- 结构化写回优先

## 3. 旧规范中需要重写的部分

### 3.1 长状态链
旧链路：
`DISCUSS -> ALIGN_PROOF -> BOOTSTRAP -> ISSUE_SYNC -> PLAN_DRAFT -> PLAN_REVIEW -> BUILD -> CLOSE_REVIEW -> ARCHIVE`

迁移为：
- 保留门禁逻辑
- 压缩显式状态数量
- 不再要求所有中间动作都必须固化成阶段名

### 3.2 Task Pack 定位
从“所有 sub-agent 第一入口”迁移为：
- subtask 的可再生 digest
- 可用于 worker / reviewer / explorer
- 但不是新的真相对象

### 3.3 workflow.md
从“运行时厚账本”迁移为：
- 薄 Process truth 文件
- 不再保存 build log / memory catalog / issue summary / handoff snapshot

### 3.4 plan.md
从“目标真相 + 部分过程真相 + 部分上下文账本”迁移为：
- 纯 Goal truth 文件
- 只保存目标、边界、决策、验证、回滚、subtask

### 3.5 delegation brief
从长期工件迁移为：
- session 级临时 wrapper
- 可由 controller 即时生成
- 默认不持久化

## 4. controller 迁移策略

controller 未来应优先保留：
- create / update workflow state
- validate references
- record review
- record evidence
- regenerate subtask pack
- archive / re-open consistency

controller 不应继续扩张为：
- 厚流程编排器
- 摘要存储中心
- reviewer judgment 替代层

## 5. 最小兼容策略

迁移初期可允许：
- 旧 `task-packs/` 目录保留，但视为派生物
- 旧 `delegation-brief` 继续使用，但标记为 ephemeral
- 旧 `workflow.md` 中冗余段落保留读取兼容，停止新写入
- review / evidence JSON schema 保持向后兼容


## 6. 从第一套工程模板吸收时的额外边界

可以吸收：
- repo guardrails
- 外部协作镜像能力
- worktree / session recovery 这类执行辅助能力
- 长期 business/API/UI 合同文档习惯

但必须重写为：
- 可选模块，而不是 runtime core
- 通用 external refs，而不是 GitHub-first truth
- `docs/contracts/*`，而不是每 task 默认强制 PRD/API/UI
- session recovery 技能，而不是第二套之外的独立 progress ledger

不得迁移：
- `harness-tasks.json` / `harness-progress.txt` 作为第二状态账本
- 所有任务默认 issue + PR 才算合法
- controller 直接承担 issue/PR orchestration
