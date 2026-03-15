# Task Pack Runtime Contract

> Task pack 的职责不是“复制更多文档”，而是把**当前 task、当前 phase、当前角色真正需要的上下文**冻结出来。它是 phase-scoped digest，不是第三份规格真源。

## 1. 何时必须存在

以下阶段必须先有 task pack：

- `PLAN_REVIEW`
- `BUILD`
- `CLOSE_REVIEW`

没有 task pack：

- 不得派发 reviewer
- 不得启动 worker
- 不得宣布“上下文已足够”

## 2. 推荐路径

`.agentdocs/tasks/<task-id>/task-packs/<phase>-task-pack.md`

## 3. 最低字段

### 3.1 Identity

- `Task ID`
- `Title`
- `Phase`
- `Owner`
- `Current State`
- `Allowed Next State`

### 3.2 Understanding Proof

- `Goal Restatement`
- `Explicit Non-Goals`
- `95% Understanding Check`
- `Missing Pieces`

### 3.3 Source Pointers

- `Spec Source`
- `Review Inputs`

### 3.4 Frozen Context

- `Frozen Decisions`
- `Known Non-Reopen Decisions`
- `Open Risks / Escalations`
- `Previous Findings`

### 3.5 Read Boundary

- `Must Read`
- `Verified Adjacent Context`
- `Unread But Potentially Relevant`
- `Coverage Decision`

### 3.6 Current Truth Anchors

- `Code Paths`
- `Key Symbols / Entry Points`
- `Tests / Checks`
- `Config / Runtime`

### 3.7 Action Boundary

- `Write Boundary`
- `Forbidden Writes`
- `Review Mode`（仅 `PLAN_REVIEW / CLOSE_REVIEW`）
- `Build Scope`（仅 `BUILD`）
- `Escalation Rule`

### 3.8 Invariants

- `Invariants`

### 3.9 Verification

- `Must-Haves`
- `Verification Obligations`
- `Reviewer Recheck Plan`
- `UAT`

## 4. 生成与校验

推荐由 controller 生成与校验：

```bash
python .agents/workflow/taskctl.py make-pack ...
python .agents/workflow/taskctl.py validate-pack --pack <path>
```

原则：

- task pack 不是百科全书
- task pack 不复制整个 plan
- task pack 必须显式指回 plan / review / evidence 的 source pointers
- 只摘出“当前 role / 当前 phase / 当前 gate 真的要用到的包”

## 5. phase-specific mode 规则

若为 `DELTA_REVIEW`：

- 必须写明上一轮 `Required Changes`
- 必须给出 `Recheck Scope`
- 若局部改动已经影响全局不变量，必须把 `Review Mode` 升级为 `FULL_REVIEW`

若 `BUILD` 使用 `FINDINGS_ONLY`：

- 必须把执行范围限制在上一轮 review findings 的闭包内
- 必须明确引用上一轮 findings / required changes
- 若修复已溢出到新 contract / 新 write boundary / 新 acceptance，必须回退到 `PLAN_DRAFT` 或重新进入 `PLAN_REVIEW`

若为 review 类 task pack：

- reviewer 应基于 `Spec Source`、`Review Inputs` 与 `Current Truth Anchors` 做独立技术判断
- reviewer 可以深读代码 / 架构 / 测试 / 日志，但不得产出替代性实现或替代性路由

## 6. 与 AGENTS / skills / deep docs 的关系

- **AGENTS**：启动级硬规则与总路由
- **Skills metadata**：告诉系统哪些场景要触发什么能力
- **Task Pack**：当前阶段的运行包
- **Deep Docs**：task pack 中显式引用的长期知识与合同
