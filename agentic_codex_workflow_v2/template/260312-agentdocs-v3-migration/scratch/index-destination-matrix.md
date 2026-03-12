# Old Index Destination Matrix

> 用于把旧 `.agentdocs/index.md` 的每个区块冻结到一个明确目的地，避免 BUILD 时误删或误分流。

## 1. 顶层区块

| Old Section | Old Lines | Destination | Build Action | Reason |
|---|---:|---|---|---|
| `V2 当前任务入口` | 3-5 | `index.md` `## 2) 当前任务（SSOT）` | 用真实 active task 替换失效 V2 指针 | 当前任务入口仍属于热路径，只是要切到 V3 SSOT |
| `V2 / Legacy 兼容规则` | 7-12 | `index.md` compatibility note + legacy appendix note | 压缩成 V3 热路径兼容说明，保留 legacy/workflow-done 可读边界 | 仍是入口级导航规则，不应丢失 |
| `产品文档` | 14-16 | `index.md` quick/context pointer | 保留为顶层导航指针 | 仍是长期入口 |
| `长期知识` | 18-20 | `index.md` 长期入口 | 保留对 `insights.md` 的入口指针 | 仍是长期入口 |
| `架构文档` | 22-32 | `index.md` architecture pointers | 保留为顶层 canonical 导航 | 仍是长期入口 |
| `兼容层说明` | 34-37 | `index.md` compatibility note | 压缩保留 | 仍是理解 legacy stub 的必要说明 |
| `Legacy workflow 参考文档` | 39-58 | `index.md` legacy appendix | 保留列表，但降级为 reference appendix | 这些文件仍在 repo 内并承担导航兼容 |
| `Realtime 已归档任务（workflow/done）` | 60-64 | `index.md` legacy `workflow/done` appendix | 保留列表 | 旧版归档还不属于新 `archive/` 模型 |
| `Chat 已归档任务（workflow/done）` | 66-72 | `index.md` legacy `workflow/done` appendix | 保留列表 | 同上 |
| `Voice 已归档任务（workflow/done）` | 74-76 | `index.md` legacy `workflow/done` appendix | 保留列表 | 同上 |
| `Skills` | 78-81 | `index.md` legacy/deprecated note | 不再作为热路径顶层 section，保留为历史注记 | 当前 skill 发现机制不再以 `.agentdocs/index.md` 为真源 |
| `全局重要记忆` | 83-174 | 分流到 `insights.md` / existing `architecture/*` reference / `index.md` operation notes | 按下面的分流矩阵执行 | 这是当前最混杂也最容易丢失的块 |

## 2. 全局重要记忆分流矩阵

| Old Lines | Theme | Destination | Build Action | Rule |
|---|---:|---|---|---|
| 85 | 产品/范围记忆 | `insights.md` | 收敛到产品/边界类长期记忆 | 属于跨任务稳定口径，不是专题 architecture SoT |
| 86-90 | Electric / media / rate limit 稳定架构事实 | existing `architecture/*` reference | 在新 index 中改成对 `backend_data_and_sync.md`、`media_storage_and_files.md`、`backend_system_overview.md` 的明确指针，不复制正文 | 本任务不重写 architecture，只引用现有 canonical SoT |
| 91-103 | Chat / Responses / SessionHistory / attachments 行为口径 | `insights.md` temporary source-linked entries | 进入 `insights.md` 的“临时运行时集成记忆”分组，并保留来源 | 这些是稳定经验，但当前没有单一现成 architecture 文档能无损承接细粒度条目 |
| 104-120 | Realtime / LiveKit / internal responses 协作规则 | split: existing `architecture/*` reference + `insights.md` temporary entries | 稳定边界类事实指向 `agent_runtime_overview.md` / `agent_runtime_orchestration.md` / `backend_system_overview.md`；细粒度协议坑进入 `insights.md` | 先用现有 SoT 收容边界事实，细节坑点不新建 architecture SoT |
| 121-172 | runtime/tools/config/tracing/ops 决策与坑点 | split: existing `architecture/*` reference + `insights.md` temporary entries | 边界/配置/观测不变量指向 `agent_runtime_overview.md` / `agent_runtime_orchestration.md` / `agent_observability_and_eventing.md` / `backend_system_overview.md`；细粒度兼容坑点进入 `insights.md` | architecture 不重写；没有现成承载面的条目先以 source-linked insights 承接 |
| 173 | “涉及相关领域先读 skills” 操作提示 | `index.md` context map note | 保留为热路径操作提示 | 仍对新会话有直接操作价值 |
| 174 | `pre-push-check` 操作提示 | `index.md` verification/governance note | 保留为热路径验证提醒 | 仍对当前工程流程有直接操作价值 |

## 3. Hard Routing Rule

1. 本任务**不创建也不改写**任何 `architecture/*.md` canonical 正文。
2. 若旧 index 条目有明确现成 architecture SoT，则只在 `index.md` 或 `insights.md` 中指向该文档，不复制正文。
3. 若旧 index 条目没有明确现成 architecture home，则先进入 `insights.md` 的 source-linked temporary 分组，并在后续任务中再决定是否升级为专题 SoT。
4. 任何旧 index 条目都不能在没有 destination 的情况下被删除。
