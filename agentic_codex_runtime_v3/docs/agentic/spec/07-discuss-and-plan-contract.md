# DISCUSS -> PLAN 合同

## 1. 为什么这是最重 gate

`DISCUSS -> PLAN` 不是“写计划之前随便聊一聊”，而是把一次任务的 **Goal truth** 冻结到可执行、可评审、可验证的程度。

如果这里含糊：

- 后续实现会在错误方向上高效前进
- reviewer 无法判断哪些结果是有意为之，哪些只是 accidental output
- evidence 会变成“证明做了很多”，而不是“证明目标成立”
- reopen / recovery 会不断回到模糊规格，而不是回到稳定真相

因此，这个阶段的目标不是产出很多文字，而是消灭关键歧义。

## 2. DISCUSS 必须澄清什么

在进入 `Freeze Goal Truth` 之前，至少必须把以下问题讲清楚：

### 2.1 交付物与效果

- 这次最终交付物是什么
- 外部观察者会看到什么变化
- 成功时最短的 demo sentence 是什么
- 哪些结果属于“看起来做了事，但并不算完成”

### 2.2 需求边界

- 明确不做什么
- 哪些要求必须保留，不能在实现时静默改写
- 哪些实现空间可以授权给 agent / engineer 自主决定
- 阶段顺序、阶段边界与不可提前合并的部分是什么
- 哪些动作必须先审后做
- 删除 / 迁移 / 重分类的前置条件是什么
- 哪些 open questions 仍需要用户拍板

### 2.3 世界立足

- 当前真实代码入口、关键符号、关键 tests 在哪里
- 哪些既有机制应复用，而不是新发明路径
- 哪些兼容性、数据、运行时约束会影响方案
- 哪些现有事实若不核对，plan 就会建立在幻觉上

### 2.4 证明方式

- 完成后靠什么证据证明结果成立
- 哪些信号必须自动验证
- 哪些信号只能通过行为、截图、日志或人工观察确认
- reviewer 必须重点复核什么

### 2.5 写入边界与风险

- 本次允许改哪些区域
- 哪些区域是 forbidden zones
- 哪些不变量必须始终成立
- 如果判断失误，最主要的失败模式是什么

## 3. 离开 DISCUSS 的最低标准

只有当以下问题大多数答案为“是”，才允许冻结 plan：

- 交付物清楚了吗？
- 目标效果清楚了吗？
- 非目标清楚了吗？
- 必保要求和可授权决定分开了吗？
- 外部可观察的 acceptance 清楚了吗？
- 关键 world anchors 找到了吗？
- 可复用路径清楚了吗？
- 写入边界清楚了吗？
- 证据策略清楚了吗？
- 未决问题已经收敛到受控集合了吗？

如果其中任一关键项为否，正确动作不是“先写个 plan 试试”，而是继续 DISCUSS 或补 Ground in World。

这里的 95% 必须同时成立于两个方向：

- **用户侧 95%**：对交付物、效果、非目标、阶段顺序、审批点、删除 / 迁移条件的理解已与用户对齐。
- **项目侧 95%**：对代码、tests、配置、已有 docs、legacy materials 与可复用途径的理解已足以支撑 plan。

## 4. PLAN 必须冻结什么

`plan.md` 只承载 Goal truth，但要把 DISCUSS 的关键结论压成 reviewer 和 worker 真正可用的结构。

至少应冻结：

- Problem / Goal / Deliverable / Why now
- Non-goals
- Acceptance（包括外部可观察信号）
- Must-preserve requirements / You decide
- Phase order / stage boundaries / approval points
- World-grounded anchors
- Frozen decisions / escalation points
- Write boundary / forbidden zones / delete-or-migrate guardrails / invariants
- Verification / evidence plan / reviewer recheck
- Rollback / migration
- 最小可审查 subtask breakdown

## 5. plan 的颗粒度规则

### 5.1 写到什么程度才够

plan 不需要复制代码，也不需要把 workflow 日志塞进去；但必须具体到 reviewer 可以判断“这是不是一个 grounded、可证明的计划”。

一个合格的 plan：

- 能让 reviewer 判断是否偏离真实代码结构
- 能让 reviewer 判断是否改写了已确认的任务节奏与审批边界
- 能让 worker 知道哪些地方能写、哪些地方不能写
- 能让 close reviewer 判断结果是否 drift
- 能让 recovery 在 fresh context 下重新进入

### 5.2 subtask 粒度

每个 subtask 至少要清楚这六件事：

- Goal
- Expected effect
- Preconditions
- Write boundary
- Verify
- Review focus

如果一个 subtask 无法同时说清这六件事，说明它太粗。

如果一个 subtask 横跨多个彼此弱相关的 write zones，或需要多个独立验证闭环，通常也应该拆开。

对于分阶段迁移 / 删除 / 重组任务，subtask 还必须显式保留：

- 当前阶段之前的前置审批
- 不得提前触发的删除 / 迁移动作
- 该阶段允许回看的 source materials

## 6. 与 TDD 的关系

这里借鉴 TDD 的核心习惯，但不把它缩成“先写测试”：

- 先定义结果，再定义实现
- 先定义证明方式，再进入编码
- 先明确失败信号，再谈“完成”

更准确的叫法是：

**contract-first / evidence-first planning**

测试只是证据的一种；对于 harness、架构、迁移、运维或 UI 任务，还可能需要：

- static checks
- behavior checks
- screenshots
- logs / traces
- human-visible acceptance

## 7. 对 v3 的直接影响

这份合同会直接约束：

- `AGENTS.md` 中的 Understand / Freeze Goal Truth gate
- `plan.md` 模板的字段颗粒度
- `world-grounding` 与 `freeze-plan` 技能的输出要求
- `subtask-pack` 再生时应携带的 objective / verification / evidence 信息
