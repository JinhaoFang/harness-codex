# 真相层级与对象所有权

## 1. Goal truth

Goal truth 回答：

- 到底要做什么
- 不做什么
- 哪些灰区已经决策锁定
- 完成必须满足哪些约束

### 主承载物
- `plan.md`

### MUST 包含
- Goal / Non-goals
- Scope / Out of Scope
- Success / Acceptance
- Key decisions / frozen decisions
- Invariants / boundaries
- Subtask breakdown
- Verification expectations
- Rollback / migration

### MUST NOT 包含
- Build log
- 运行过程证据账本
- 长 handoff 快照
- 重复写入 workflow 状态
- 尚未冻结的 agent 工作假设

## 2. Process truth

Process truth 回答：

- 当前在哪个 subtask
- 当前处于哪个 gate / state
- 当前是否合法推进
- 下一步允许做什么
- 当前 review / exception 状态如何

### 主承载物
- `workflow.md`

### MUST 包含
- Active task / subtask
- Current state
- Allowed next action
- Review status
- Exception / recovery status
- 指向 plan / latest review / latest evidence 的 pointers
- 需要时记录 Discuss gate 的完成状态、审批状态与删除 / 迁移 guard 状态

### MUST NOT 包含
- Goal truth 的完整重述
- 厚 build log
- memory catalog
- issue 详情重复抄写

## 3. World truth

World truth 只认项目本体真实情况：

- source code
- tests
- 项目已有结构
- 项目已有可复用途径

### 说明
World truth 不包含：
- logs
- screenshots
- runtime transcripts
- evidence bundles
- review bundles
- workflow / plan / archive

这些对象都可能帮助判断，但它们不是世界本体。

World-grounded anchors 必须只引用**当前仓库里已经存在的对象**：

- code / tests / config / runtime artifacts
- 项目中已经存在的 docs / legacy materials / existing structure

它们不得引用：

- 当前 task 的 `plan.md`
- 当前 task 的 `workflow.md`
- 当前 task 的 `reviews/*.json`
- 当前 task 的 `evidence/*.json`
- 当前 task 的 `subtask-packs/*.md`
- 尚未产生的未来输出物

## 4. Process evidence

Process evidence 记录运行与审查过程中发生过的结构化事实，用于：

- 支持独立审查
- 支持异常恢复
- 支持断点重续
- 辅助抑制上下文腐烂

但它只应承担“可引用的过程事实”职责，不能膨胀成厚记忆层。

### 典型对象
- `evidence/*.json`
- `reviews/*.json`
- 局部 logs / screenshots / command outputs

### 正确使用方式
resume / re-entry 应通过以下组合再生成轻量入口：

- Goal truth
- 当前 Process truth
- 当前 World truth
- 相关 Process evidence

而不是直接把 Process evidence 当作下一轮工作说明书。

## 5. 派生对象与临时对象

### 可再生派生对象
- `subtask-pack.md`

它是 subtask 的入口视图，不是新的真相层。

### 临时 wrapper
- `delegation-brief.md`

它服务于单次 session 的角色、边界与输出契约，不应成为长期制度对象。

## 6. 对象所有权表

| 对象 | 类别 | 是否长期持久化 | 权力说明 |
|---|---|---:|---|
| `AGENTS.md` | 仓库级宪法 | 是 | 定义稳定不变量与边界 |
| `plan.md` | Goal truth | 是 | 目标与约束权威来源 |
| `workflow.md` | Process truth | 是 | 当前位置与推进状态来源 |
| `subtask-pack.md` | 派生视图 | 可选 | subtask 入口 digest |
| `reviews/*.json` | Process evidence | 是 | reviewer judgment |
| `evidence/*.json` | Process evidence | 是 | 过程事实记录 |
| `delegation-brief.md` | 临时 wrapper | 否 | session 启动包装 |
| code / tests | World truth | 是 | 项目本体真实情况 |

## 7. freshness / invalidation 规则

以下任一变化出现时，现有派生对象必须视为可疑并重生成：

- Goal / Scope / Acceptance 变化
- 关键决策变化
- subtask 边界变化
- 关键代码路径变化
- source materials 的分类 / 删除依据变化
- reviewer 打回并要求重新规划
- 实现偏离已批准 plan

摘要不能绕过 freshness check 直接成为后续规划依据。
