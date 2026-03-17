# 架构层、模块层、横切系统

## 1. 四层架构

### 1.1 意图层
回答：要做什么、为什么做、哪些灰区已锁定。

对应对象：
- `plan.md`
- 用户确认 / 需求决策

### 1.2 上下文层
回答：当前 subtask 需要看到什么，不该看到什么，如何装配。

对应对象：
- `subtask-pack.md`（可再生）
- skills / rules 的按需路由
- 必要 source pointers

### 1.3 执行层
回答：agent 在什么工作区、什么边界内改变世界。

对应对象：
- code workspace
- tool access
- write boundary
- session / agent role

### 1.4 反馈层
回答：什么算完成，谁来裁决推进、返工或关闭。

对应对象：
- `reviews/*.json`
- `evidence/*.json`
- tests / checks
- reviewer gate

## 2. 八个一级模块

### 模块 1：意图 / 决策工件
存放目标、边界、关键决策与 non-goals。

### 模块 2：规划 / 边界契约
存放 subtask breakdown、write boundary、验证要求、回滚策略。

### 模块 3：状态机 / 工作流
只记录当前位置、门禁状态、合法推进与异常恢复。

### 模块 4：上下文 / 记忆
负责最小上下文装配与再生，不负责变成厚记忆库。

### 模块 5：执行工作区
负责工作目录、工具权限、写入边界、并行策略。

### 模块 6：验证 / 证据
负责过程证据采集、测试、行为检查与结构化记录。

### 模块 7：版本 / 可逆
负责回滚边界、分支 / patch / checkpoint 策略。

### 模块 8：恢复 / 演进
负责 resume、fix flow、summary regeneration、规则去冲突与反熵。

## 3. 两个横切系统

### 3.1 deterministic control plane
它不是一级模块，而是横切底座。

职责只保留为：
- 状态推进检查
- 结构化写回
- schema / 引用类型 / 存在性校验
- 恢复与归档一致性检查
- 派生 digest 的再生

它不应该演化为：
- 厚流程管理器
- 替代 reviewer 的判断层
- 替代 plan 的目标承载物

### 3.2 rules / skills injection
skills / rules / hooks / subagents 都属于方法注入与运行时路由面。

它们的职责是：
- 提供可复用方法
- 为特定场景按需注入知识
- 为角色提供 specialist workflow

它们不能：
- 定义 Goal truth
- 决定 Process truth
- 定义完成真相
- 决定回滚真相

## 4. 依赖与禁止反向依赖

### 正向依赖
- Goal truth -> subtask planning
- subtask planning -> Process truth
- Goal truth + Process truth + World truth -> subtask pack
- World truth + Process evidence -> review

### 禁止反向依赖
- workflow 反向定义 plan
- summary 反向定义 Goal truth
- session history 反向定义 Process truth
- skills 反向定义状态推进与完成裁决
- delegation brief 反向定义任务真相


### 3.3 optional modules / adapters
这些模块位于 runtime core 之外：
- repo guardrails（`.githooks/*`、`.github/workflows/*`）
- external collaboration adapters（例如 GitHub）
- execution workspace helpers（例如 worktree isolation）
- durable contract artifacts（`docs/contracts/*`）

它们可以增强工程落地与协作，但不能定义 Goal truth / Process truth，也不能替代 review verdict。
