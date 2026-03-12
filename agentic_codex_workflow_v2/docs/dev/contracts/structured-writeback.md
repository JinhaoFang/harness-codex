# Structured Writeback Contract (V3)

> 目标：把 review bundle、evidence、workflow event、index sync、archive manifest 等结构化内容，从“主 agent 手工编辑 Markdown”切换成“脚本稳定写入”。

## 1. 适用对象
- `reviews/*.json`
- `evidence/*.json`
- `workflow.md` 的 build log / evidence ledger / runtime 指针
- `workflow.md` 的 plan-review / close-review summary 区块
- `.agentdocs/index.md`
- `.agentdocs/archive/index.md`
- `archive-manifest.json` / backlink

## 2. 原则
1. 结构统一优先于书写自由
2. 语义结论可由 agent 生成，最终落盘由脚本负责
3. 脚本输入应尽量简单：CLI flags 或 JSON
4. 同类工件的格式要支持后续迁移脚本消费
5. review / evidence / archive manifest 以 JSON 为 canonical artifact；如需人类摘要，应由读取端渲染，而不是再持久化一份并行 Markdown
6. `review` 与 `evidence` 必须分开持久化；workflow 中的引用字段必须指向正确的工件类型
