# 运行、审查、恢复与反熵

## 1. 最小运行闭环

本规范不要求固定长状态链，只要求以下闭环成立：

### Gate A：Understand
回答：
- 要交付什么
- 不交付什么
- 验收信号是什么
- 哪些问题仍未解决

### Gate B：Ground in World
必须核对：
- 关键代码路径
- 关键符号 / entry points
- 已有 tests
- 已有可复用能力
- 关键兼容性约束

### Gate C：Freeze Goal truth
形成 plan，并冻结：
- deliverable
- boundaries
- must-haves
- invariants
- reviewer expectations
- rollback strategy
- subtask breakdown

### Gate D：Independent Review
review 必须在 fresh context 中进行。

通过后才可进入实现；实现完成后必须再次经过独立 review 才能关闭。

## 2. review 的职责重定义

### 2.1 Plan review
不是格式检查，而是用 World truth 审 Goal truth。

必须检查：
- plan 是否和项目现状冲突
- 技术选型是否违背项目真实结构
- 是否忽略已有实现或可复用途径
- 是否引入不必要新抽象
- 验证方案是否足以证明完成

### 2.2 Close review
不是“看起来做完了没有”，而是：
- 实现是否偏离已批准 plan
- 是否与项目真实情况冲突
- 是否重复发明已有能力
- 是否引入了多余的新方法 / 新路径
- 是否满足验证要求与回滚边界

## 3. review 必须 fresh context

MUST：
- reviewer 默认不继承 builder 的长对话历史
- reviewer 只读取 plan、必要 pointers、代码世界与必要过程证据
- reviewer 可以由专门 subagent 执行

MUST NOT：
- builder 自证式 review
- 共享长上下文导致 review 变成 continuation

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
4. 核对当前代码 / tests
5. 只补读必要 review / evidence
6. 再生新的 subtask pack / review digest

## 6. 反熵机制

系统必须定期执行：
- 过期摘要失效检查
- rules / skills 冲突清理
- workflow 减重
- pack 重生成
- fix flow 后 re-verify

禁止依赖无限累加的 memory routing、handoff snapshots、历史 recap。
