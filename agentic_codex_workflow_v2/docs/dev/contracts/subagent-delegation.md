# Sub-agent Delegation Contract

> 关键不是“字段写全”，而是把**冻结上下文、可写边界、目标、输出契约与升级条件**一起打包，让 main agent 不再充当手工中间层。

## 1. 固定 6 段接口

每次委派都应明确：

1. `Identity`
2. `Boundary`
3. `Objective`
4. `Procedure`
5. `Output Contract`
6. `Escalation`

说明：

- 这 6 段不是新增文档对象，而是 sub-agent 指令接口的稳定骨架
- 主 agent 不重述完整背景历史；只传当前 phase 所需的上下文

## 2. 每次委派都必须包含的字段

- `Role`
- `Task Pack`
- `Goal`
- `Review Mode`（review 类任务必填）
- `Build Scope`（BUILD 类任务必填）
- `Must Read`
- `Current Truth Anchors`
- `Write Boundary`
- `Escalation Rule`
- `Output Contract`

缺少任一字段，委派不合格。

## 3. Frozen Context Card（委派包核心）

每个 task pack 都应携带：

- `Task Identity`
- `Current State`
- `Allowed Next State`
- `Frozen Decisions`
- `Known Non-Reopen Decisions`
- `Open Risks / Escalations`
- `Previous Findings`（复核轮次）
- `Verification Obligations`

规则：

- sub-agent 不得重新解释 frozen decisions
- 发现 frozen decisions 与真实情况冲突时，只能升级，不得自行改写

## 4. Review Mode 必须显式声明

### FULL_REVIEW

默认模式。以下任一情况必须使用：

- Goal / Scope / Acceptance / Contract 变化
- Write Boundary 变化
- canonical target / navigation 变化
- evidence 语义变化
- 长期 SoT 变化

### DELTA_REVIEW

只允许在：

- 上一轮 `Required Changes` 的闭包范围内
- 且未触发 FULL 保护字段

### FORMAT_ONLY

只用于：

- 机器字段补齐
- 标题 / 路径 / 格式修补

## 4.1 Build Scope 必须显式声明

### APPROVED_SCOPE

默认模式。用于：

- 按已通过的 plan / plan review 执行当前 BUILD phase
- 写入范围与 frozen `Write Boundary` 一致

### FINDINGS_ONLY

只允许在：

- 上一轮 review findings 的闭包范围内修复
- 且未触发新的 contract / scope / acceptance / write boundary 变化

### FORMAT_ONLY

只用于：

- machine-field 修补
- 路径归一化
- 不改变实现语义的格式修补

## 5. 写入边界

### reviewers（shared）

- 可以主动读取代码、架构、接口、测试、日志与 evidence，做独立技术判断
- 有分析权和否决权，没有实现权、改写权、调度权
- `Required Changes / Required Follow-ups` 必须是修改闭包，不能写成替代性完整 plan、替代性实现方案或替代性路由方案

### explorer

默认允许写 task-scoped 工件：

- `task-packs/`
- `evidence/`
- `scratch/`
- `findings/`

禁止：

- 改业务代码
- 改 workflow 状态头
- 改 canonical plan
- 改长期 architecture / insights

### plan_reviewer / close_reviewer

允许写：

- `reviews/plan-review-r<N>.json`
- `reviews/close-review-r<N>.json`
- controller 生成的 task-scoped structured artifact

禁止：

- 重写 plan
- 修改业务代码
- 直接推进状态机
- 直接归档
- 直接替主 agent 重新路由、重新分解任务或宣布状态已推进

### worker

允许：

- 在当前 phase 的 `Write Boundary` 内改业务文件
- 写 task-scoped `evidence/`、`scratch/`、`task-packs/`

禁止：

- 越过当前 phase
- 修改 review 结论
- 修改 governance 决策
- 静默扩大 write boundary

## 6. 自描述回复（必须返回）

### explorer / worker

- `Summary`
- `Files Written`
- `Evidence Produced`
- `Verification Run`
- `Risks Found`
- `Next Legal Action`

### plan_reviewer

- `Decision: PASS | NEEDS_CHANGES`
- `Summary`
- `Required Changes`
- `Evidence`
- `Recheck Scope`
- `Review Mode Used`
- `Materials Accessed`
- `Global Impact: YES | NO`
- `Open Questions`

### close_reviewer

- `Final Status: PASS | NEEDS_FIX | BLOCKED`
- `Key Findings`
- `Required Follow-ups`
- `Evidence Summary`
- `Recheck Scope`
- `Review Mode Used`
- `Materials Accessed`
- `Global Impact: YES | NO`
- `Archive Actions`

## 7. 升级条件

sub-agent 发现以下情况时应直接 escalate，而不是自由推断：

- 缺少 truth anchor
- task pack 过期或不完整
- 需要越界写入
- delta review 已演变成全局影响
- build-before-review 或 evidence 不可追踪
