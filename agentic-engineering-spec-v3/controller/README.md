# Controller 设计定位

controller 是 **deterministic control plane**，应当单独设计与实现，不应被塞进 skills。

## 职责边界

controller MUST:
- 检查 gate 合法性
- 检查 schema / completeness / 引用约束
- 结构化写入 workflow / reviews / evidence
- 刷新 subtask pack
- 维护 archive / reopen 一致性

controller MUST NOT:
- 代替 reviewer 做主观裁决
- 代替 plan 写 Goal truth
- 代替代码世界回答架构是否正确

skills MAY:
- 指导 world grounding
- 指导 plan review
- 指导 reuse check
- 指导 close review
- 触发 controller 命令

skills MUST NOT:
- 直接定义状态推进真相
- 直接定义完成真相
- 直接定义回滚真相
