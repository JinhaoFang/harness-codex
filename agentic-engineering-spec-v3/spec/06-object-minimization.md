# 对象最小化清单

## 1. 长期一等对象

### 1.1 AGENTS.md
作用：仓库级宪法、红线、角色边界、入口说明。

### 1.2 plan.md
作用：Goal truth。

### 1.3 workflow.md
作用：Process truth。

### 1.4 reviews/*.json
作用：review judgment。

### 1.5 evidence/*.json
作用：Process evidence。

### 1.6 code / tests
作用：World truth。

## 2. 派生视图

### 2.1 subtask-pack
定义：从 plan、workflow、World truth 与必要 evidence 再生出的 subtask 入口视图。

规则：
- 可以持久化，也可以按需生成。
- 不构成真相层。
- 优先引用，不复制主真相。

## 3. 临时 wrapper

### 3.1 delegation-brief
定义：一次 session 的角色包装与输出契约。

规则：
- 不承载任务真相。
- 不应成为长期对象。
- 可以由 controller 或编排层临时生成。

## 4. 必须区分的对象

### 4.1 Task / Subtask
- Task：较大的目标单元。
- Subtask：可独立执行、可独立验证、可独立审查的执行单元。

### 4.2 Subtask / Session
- Subtask 不是 session。
- 一个 subtask 可以对应多个 session：grounding、build、plan review、close review、recovery。

## 5. 不应继续厚持久化的内容

- handoff snapshots
- memory catalogs
- 大段 recap
- 重复的 truth anchors
- 重复的 context coverage
- summary of summary

## 6. 设计判断

对象是否值得成为长期对象，只问三件事：

1. 它是否承载独立真相或独立裁决责任？
2. 它是否不能稳定地从更低层对象再生？
3. 它是否脱离会话仍必须存在？

只要三问中大部分答案为否，就不应升级为长期对象。
