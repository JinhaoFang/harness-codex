# 运行、审查、恢复与反熵

## 1. 最小运行闭环

本规范不要求固定长状态链，只要求以下闭环成立：

`DISCUSS -> PLAN` 是整个运行时最重的 gate；这里如果没有把目标效果、边界和证据方式冻结清楚，后续实现只会高效放大偏差。

详细合同见：`docs/agentic/spec/07-discuss-and-plan-contract.md`

### Gate A：Discuss / Understand
回答：
- 要交付什么
- 外部会观察到什么效果
- 不交付什么
- 哪些要求必须保留、哪些实现空间可以授权决定
- 验收信号是什么
- 阶段顺序与阶段边界是否已冻结
- 哪些动作必须先审后做
- 删除 / 迁移 / 重分类的前置条件是什么
- 哪些问题仍未解决

离开 Gate A 之前，至少应确保：
- user-side understanding >= 95%
- project-side understanding >= 95%
- deliverable clear
- target effect clear
- non-goals clear
- must-preserve requirements clear
- user-visible acceptance clear
- phase order / stage boundaries clear
- approval points clear
- delete / migration conditions clear when the task can delete, migrate, or reclassify materials
- open questions reduced to a controlled set

### Gate B：Ground in World
必须核对：
- 关键代码路径
- 关键符号 / entry points
- 已有 tests
- 已有可复用能力
- 关键兼容性约束
- 哪条既有路径应优先复用而不是新发明
- 对迁移 / 删除 / 重组类任务，原始 source materials、现有目录结构与候选删除对象

### Gate C：Freeze Goal truth
形成 plan，并冻结：
- deliverable
- target effect
- boundaries
- phase order / stage boundaries
- approval points
- must-haves
- invariants
- delete / migration guardrails
- evidence strategy
- reviewer expectations
- rollback strategy
- subtask breakdown

plan 的颗粒度至少要足以让 reviewer 判断：
- 目标是否 grounded in world
- 写入边界是否明确
- 验证是否真的能证明完成
- subtask 是否是最小可审查单元

每个 subtask 至少要明确：
- Goal
- Expected effect
- Preconditions
- Write boundary
- Verify
- Review focus

### Gate D：Independent Review
review 必须在 fresh context 中进行。

通过后才可进入实现；实现完成后必须再次经过独立 review 才能关闭。

## 2. review 的职责重定义

### 2.1 Plan review
不是格式检查，而是让 fresh-context reviewer 同时对齐三层：

- 任务要求与阶段约束
- Goal truth
- World truth

必须检查：
- plan 是否改写了已经确认的任务节奏、阶段边界、审批点或先审后做约束
- plan 是否和项目现状冲突
- 技术选型是否违背项目真实结构
- 是否忽略已有实现或可复用途径
- 是否引入不必要新抽象
- 验证方案是否足以证明完成
- 对迁移 / 删除 / 重组 / 重新分类类任务，是否回看了 source materials，并判断保留 / 压缩 / 删除依据是否成立

### 2.2 Close review
不是“看起来做完了没有”，而是：
- 实现是否偏离已批准 plan
- 是否与项目真实情况冲突
- 是否重复发明已有能力
- 是否引入了多余的新方法 / 新路径
- 是否满足验证要求与回滚边界
- 对迁移 / 删除 / 重组 / 重新分类类任务，是否能把结果追溯回 source materials 与删除 / 迁移依据

### 2.3 完整核对与抽样

以下对象必须完整核对，不得抽样：

- 任务要求层
- Goal truth 核心约束

World truth 只在以下条件下允许抽样：

- reviewer 明确记录抽样范围
- reviewer 明确记录抽样依据
- reviewer 明确记录残余风险
- reviewer 明确记录实际访问过的材料

## 3. review 必须 fresh context

MUST：
- reviewer 默认不继承 builder 的长对话历史
- reviewer 只读取 plan、必要 pointers、代码世界与必要过程证据
- reviewer 可以由专门 subagent 执行
- subagent 应先从当前 `.agentdocs/*` 重建 task / process 上下文，再读取最小必要的 world truth
- rereview 仍然是 fresh full review；上一轮 findings 只能作为附加回归检查清单

MUST NOT：
- builder 自证式 review
- 共享长上下文导致 review 变成 continuation
- 让 parent prompt 把 reviewer scope 收缩成“只检查上次报错的几项”
- 把 prior findings list 当成 rereview 的完整输入

## 4. 过程证据的使用原则

过程证据可以支持：
- 审查裁决
- 异常恢复
- resume
- 反熵再生

但不应：
- 复制成厚 workflow
- 演化为下一轮完整说明书
- 替代对当前代码世界的重新核对

## 5. resume 机制

resume 不是“继续上次上下文”，而是“重新进入系统”。

推荐顺序：
1. 读取 `AGENTS.md`
2. 读取 `workflow.md`
3. 读取 `plan.md`
4. 读取 active subtask pack（若存在）
5. 只补读必要 review / evidence
6. 核对当前代码 / tests
7. 再生新的 subtask pack / review digest

## 6. 反熵机制

系统必须定期执行：
- 过期摘要失效检查
- rules / skills 冲突清理
- workflow 减重
- pack 重生成
- fix flow 后 re-verify

禁止依赖无限累加的 memory routing、handoff snapshots、历史 recap。
