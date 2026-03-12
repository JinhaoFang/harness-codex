# High-Entropy State Machine Contract (V3)

> V3 的变化有三点：
> 1. 在 plan 前增加 `DISCUSS -> ALIGN_PROOF`
> 2. 明确“控制平面 / 事实平面”分离
> 3. 将结构化写回交给 controller / skills + scripts

## 1. 正常路径
`DISCUSS -> ALIGN_PROOF -> BOOTSTRAP -> ISSUE_SYNC -> PLAN_DRAFT -> PLAN_REVIEW -> BUILD -> CLOSE_REVIEW -> ARCHIVE`

## 2. 全局硬规则
- `ALIGN_PROOF` 未完成：不得进入 `PLAN_DRAFT`
- `PLAN_REVIEW = PASS` 前：不得进入 `BUILD`
- `CLOSE_REVIEW = PASS` 前：不得进入 `ARCHIVE`
- 所有 `PLAN_REVIEW / BUILD / CLOSE_REVIEW` 都必须绑定当前 phase task pack
- BUILD / REVIEW 阶段必须引用 `Current Truth Anchors`
- 结构化工件优先由脚本落盘，不手工维护机器字段

## 3. 异常路径
- 任一非 `ARCHIVE` 状态在发现 state conflict / evidence gap / review 中断 / task pack 过期时，允许转入 `EXCEPTION_RECOVERY`
- `EXCEPTION_RECOVERY` 的退出状态由当前恢复结论决定，可返回 `DISCUSS / ALIGN_PROOF / PLAN_DRAFT / PLAN_REVIEW / BUILD / CLOSE_REVIEW / BLOCKED`
- workflow 状态头应由 controller 推进，不手工改 `Current State / Allowed Next State`
