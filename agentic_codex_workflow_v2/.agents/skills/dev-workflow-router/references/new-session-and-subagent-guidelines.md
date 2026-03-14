# 新会话与 Subagent 规范

> 目标：把独立视角与写入边界变成运行时协议，而不是口头原则。

## 1) 必须使用独立会话的阶段

- `PLAN_REVIEW`
- 每个独立执行 phase
- `CLOSE_REVIEW`

## 2) Reviewer 等待协议

- 当前状态为 `PLAN_REVIEW` 时，主 agent 只允许等待 reviewer 输出并回填 workflow
- 当前状态为 `CLOSE_REVIEW` 时，主 agent 只允许等待 close reviewer 输出并回填 workflow
- 不允许以“顺便检查一下”为理由继续实现、继续改 plan、继续扩 scope

## 3) Subagent 的委派格式

```text
【Role】explorer / worker / plan_reviewer / close_reviewer / monitor
【Goal】一句话，可判定
【Must Read】必须读取的 workflow / plan / code / docs
【Adjacent Scan】允许扩展搜索的边界
【Write Boundary】允许写入的目录 / 文件；reviewer / explorer 仅允许 task-scoped 工件
【Escalation Rule】发现新问题后如何升级
【Output Format】固定输出字段
```

## 4) 写入边界

- `explorer`: 允许写 `task-packs/`、`findings/`、`scratch/`、`evidence/`
- `plan_reviewer`: 允许写 `reviews/` 与 controller sidecar
- `worker`: 只允许写当前 phase 授权边界
- `close_reviewer`: 允许写 `reviews/` 与 controller sidecar
- `monitor`: 只读

## 5) 防循环规则

- reviewer 只给修改集，不重写整份 plan
- worker 发现 plan 不足时，立即回退到 `PLAN_DRAFT`
- 连续两轮 review 仍无法收敛时，输出“人工拍板分歧点”
