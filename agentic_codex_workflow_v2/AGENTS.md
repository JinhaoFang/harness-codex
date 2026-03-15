# Repository Working Agreement

> 目标：让开发过程可复现、可验证、可回滚、可断点重续、可持续演进。
>
> 最高原则：
>
> 1. Control plane 不能覆盖 Goal truth / World truth
> 2. 能由 deterministic code 稳定处理的动作，不交给 agent 记忆维护
> 3. reviewer 负责独立判断，不负责代替实现

## 1. Truth model

### Goal truth

- user-confirmed intent
- `.agentdocs/tasks/<task-id>/plan.md`

### Process truth

- `.agentdocs/tasks/<task-id>/state.json`
- `.agentdocs/tasks/<task-id>/events.jsonl`

### World truth

- code
- tests

规则：

- 文档用于同步目标、进度、判断，不定义项目当前真实状态
- review 是 judgment，不是事实真源
- evidence 是验证记录，不是 world truth
- 发生冲突时：
  - Goal truth 看 `plan.md`
  - Process truth 看 `state.json`
  - World truth 看 code / tests

## 2. Main path

唯一正常主路径：

`DISCUSS -> PLAN -> BUILD -> REVIEW -> ARCHIVED`

辅助状态：

- `BLOCKED`
- `RECOVERING`

硬门禁：

- 未达到 95% 理解度，不得从 DISCUSS 进入 PLAN
- plan review 未 PASS，不得进入 BUILD
- reviewer 未 PASS，不得进入 ARCHIVED
- 目标 / 范围 / 验收 / 关键约束变化时，必须回到 PLAN
- 发现状态冲突、task pack 过期、review 中断、证据缺失时，进入 RECOVERING

## 3. DISCUSS is the heaviest gate

DISCUSS 必须完成以下内容后，才允许写 plan：

- Goal Restatement
- Explicit Non-Goals
- Acceptance
- Write Boundary
- Risks
- Current code anchors
- Current test anchors
- Open questions reduced to a controlled set

95% 理解度检查项：

- goal clear
- scope clear
- non-goals clear
- code anchors found
- test anchors found
- write boundary clear
- acceptance clear
- risks clear

任一不清楚，视为未完成 DISCUSS。

## 4. Plan requirements

每份 `plan.md` 必须至少包含：

- Understanding Proof
- What I Need / My Requirements / You Decide
- Current Code/Test Anchors
- Decision Freeze
- Invariants
- Must-Haves
- Verification
- Reviewer Recheck
- Rollback / Migration
- Phase breakdown

要求：

- plan 必须基于当前仓库真实情况编写
- plan reviewer 必须用 code/tests 审查 plan 是否与项目现实一致
- plan 不是格式文档，而是冻结后的 goal truth

## 5. Review model

### Plan reviewer

职责：

- 用 world truth 审查 plan 是否与项目真实情况一致
- 检查技术选型、架构假设、复用路径、改动边界是否与现有项目冲突
- 发现错误前提、虚构边界、忽略现有能力时，必须打回

权限边界：

- 有判断权和否决权
- 无业务实现权
- 不修改代码，只提交 review 结论

### Reviewer

职责：

- 在新的上下文中独立复核 BUILD 结果
- 检查实现是否偏离 plan
- 检查是否重复发明已有机制、已有抽象、已有入口
- 检查是否遗漏已有可复用方法、遗漏必要清理、遗漏迁移/回滚处理
- 检查最终结果是否满足 goal truth
- 检查是否满足归档条件

权限边界：

- 有判断权和否决权
- 无业务实现权
- 默认不与 worker 共享同一实现上下文

规则：

- REVIEW 必须使用新的上下文
- 需要时可启用 multi-agent reviewer
- “代码能跑”不等于“可以归档”

## 6. Task pack

task pack 是 phase-scoped digest，不是第三份规格。

用途：

- 为当前 BUILD / REVIEW 会话装配最小必要上下文
- 为 sub-agent 提供边界清晰的只读入口

要求：

- 只保留当前版本
- 可由 plan + state + latest review/evidence 重新生成
- 没有当前 pack，不得派发 worker / reviewer

## 7. Structured writing

以下动作优先用脚本完成，而不是手工多次编辑：

- 创建任务骨架
- 更新 state
- 同时写 review JSON 与 state 引用
- 同时写 evidence JSON 与 state 引用
- 写 events.jsonl
- 归档任务
- 更新时间戳
- 任何跨多个文件 / 同文件多位置的事务性更新

自由手写仅用于：

- plan 正文
- 代码实现
- 分析结论
- reviewer 的技术判断正文

## 8. Multi-agent boundaries

默认单 agent。

只有满足其一时才启用 multi-agent：

- 需要独立 reviewer 新上下文复核
- 需要并行探索，且写域独立
- 需要 monitor 做等待 / 轮询

规则：

- 并行 writer 必须独立 write boundary；必要时使用独立 worktree
- reviewer 不与 worker 共享同一实现上下文
- sub-agent 默认先读 task pack，不默认深读整个仓库

## 9. Where guidance lives

- repo-wide rules: `AGENTS.md`
- directory-local rules: `AGENTS.override.md`
- reusable methods / checklists: `.agents/skills/*`
- runtime config: `.agents/config.toml`
- deterministic actions: `.agents/workflow/taskctl.py`
