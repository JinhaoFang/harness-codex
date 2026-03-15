# Repository Working Agreement

> 目标：让 coding-agent 开发活动保持可复现、可验证、可回滚、可断点重续、可持续演进。

## 0. 先记住这 8 条硬规则

1. **代码世界优先。** 文档约束动作，但不能覆盖项目真实情况。
2. **先理解并核对世界，再冻结计划。** 不允许凭空写 plan。
3. **计划通过独立审查前，不进入实现。**
4. **实现完成后必须再次独立审查。** reviewer 默认 fresh context。
5. **`plan.md` 只承载 Goal truth；`workflow.md` 只承载 Process truth。**
6. **Task Pack 是 subtask 的可再生 digest，不是新的真相层。**
7. **review 与 evidence 分离。** review 记录 judgment，evidence 记录过程事实。
8. **凡 deterministic layer 能稳定做对的动作，优先下沉到 controller。**

## 1. 仓库内的长期对象

- `plan.md`：Goal truth
- `workflow.md`：Process truth
- `reviews/*.json`：review judgment
- `evidence/*.json`：process evidence
- code / tests：World truth

不鼓励长期持久化：
- handoff snapshots
- memory catalogs
- 大段 recap
- 为了恢复方便而复制的摘要

## 2. 四个最小 gate

### Gate A：Understand
必须明确：
- Goal
- Non-goals
- Scope
- Acceptance
- Open questions

### Gate B：Ground in World
必须核对：
- 关键代码路径
- 关键符号 / entry points
- 现有 tests
- 现有可复用途径

### Gate C：Freeze Goal Truth
形成并冻结：
- deliverable
- boundaries
- must-haves
- invariants
- verification expectations
- rollback strategy
- subtask breakdown

### Gate D：Independent Review
review 使用 fresh context，对 plan 或实现做独立判断。

## 3. 多 agent 协议

角色建议：
- main：route / orchestration / state
- explorer：探索世界真相
- worker：在写入边界内实现
- plan_reviewer：审 Goal truth
- close_reviewer：审实现结果与漂移

规则：
- reviewer 无实现权
- reviewer 默认不共享 builder 长上下文
- 并行 writer 仅在写域独立时允许

## 4. controller 最小职责

controller 应承担：
- 状态推进检查
- 结构化写回
- review / evidence 记录
- 引用与 schema 校验
- subtask pack 再生
- archive / re-open 一致性检查

controller 不应承担：
- 代替 reviewer 判断
- 代替 plan 承载目标
- 代替代码世界回答“系统现在是什么”
