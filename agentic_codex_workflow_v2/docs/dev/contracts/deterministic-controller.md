# Deterministic Controller Contract

> 这层的目标不是“把所有事都脚本化”，而是把**稳定的结构动作**从 LLM 手里拿出来。只要一件事主要是 if-else、路径落位、模板渲染、目录移动、字段同步、schema 校验，就应该优先交给 deterministic controller。

## 1. 统一入口
```bash
python .codex/workflow/taskctl.py <subcommand>
```

## 2. 推荐 subcommands
### `create-task`
初始化 task-scoped 目录与模板。

### `check-transition`
检查状态迁移是否合法。

### `advance-state`
推进 workflow 状态头，写回 `Current State / Allowed Next State / Current State Owner / Transition Check / Last Updated`，并追加状态事件。

### `make-pack`
生成当前 phase 的 task pack。

### `validate-pack`
检查 task pack 是否具备最低运行字段、`Invariants`，以及按 phase 区分的 `Review Mode / Build Scope`，并输出缺失项。

### `emit-delegation-brief`
根据固定 6 段协议生成可直接交给 sub-agent 的 delegation brief。

### `record-review`
把 reviewer 输出落位到 `reviews/*.json`，并可同步 workflow review section；支持结构化记录 `Materials Accessed`。

### `record-evidence`
记录 evidence bundle 到 `evidence/*.json`。

### `record-workflow-event`
把关键事件写入 workflow 文本和 `runtime-events.jsonl`。

### `lint-skills`
校验 skill front matter、边界字段和基础结构，降低 skill 漂移。

### `sync-index`
同步 `.agentdocs/index.md`。

### `archive-task`
把 task-scoped 工件整体归档。

## 3. controller 负责什么
- 目录与模板脚手架
- 状态迁移检查
- task pack 渲染与校验
- delegation brief 渲染
- review / evidence / workflow event 的结构化写回
- task bundle 归档移动
- machine-readable canonical artifact 生成
- 基础 lint / consistency check
- machine-checkable gate（路径存在性、字段缺失、枚举值、状态机、引用类型）的统一前置检查

## 4. controller 不负责什么
- 不替代工程判断
- 不替代 reviewer 基于代码 / 架构 / 测试 / evidence 的独立技术判断
- 不决定 scope / acceptance / governance
- 不声称“任务完成”

## 5. 设计原则
1. 能用脚本稳定完成的，不应消耗 LLM
2. controller 产出的结构文件必须可审阅、可追踪
3. 新的结构输出应优先兼容后续可视化消费
4. controller 失败时，主 agent 只能报告失败并给出最小恢复动作，不能悄悄手改造成“看起来通过”
5. 凡是 reviewer 可以稳定复现为“路径/字段/状态/引用类型检查”的 finding，都应优先下沉成 canonical preflight
