# AstraFlow 文档索引

> V3 运行入口只承载当前任务、长期知识入口、兼容边界与可恢复导航；旧索引里的长期记忆已按去向迁入 `insights.md`、现有 `architecture/*.md` 引用或保留为操作提示。

## 0) 快速入口（新会话默认只读）

- 仓库规则：`AGENTS.md`
- 当前任务 workflow：见 `## 2) 当前任务（SSOT）`
- 当前任务 task pack：从当前 task root 下的 `task-packs/` 进入
- 产品文档：`.agentdocs/prd/product-spec.md`
- 长期洞察：`.agentdocs/insights.md`
- Archive Index：`.agentdocs/archive/index.md`
- 状态机契约：`docs/dev/contracts/high-entropy-state-machine.md`
- task pack 契约：`docs/dev/contracts/task-pack-layout.md`

## 1) Context Map（按需检索）

- 看产品与范围：`.agentdocs/prd/product-spec.md`
- 看长期经验：`.agentdocs/insights.md`
- 看后端/数据：`.agentdocs/architecture/backend_system_overview.md`、`.agentdocs/architecture/backend_data_and_sync.md`
- 看 runtime/agent：`.agentdocs/architecture/agent_runtime_overview.md`、`.agentdocs/architecture/agent_runtime_orchestration.md`
- 看观测与事件化：`.agentdocs/architecture/agent_observability_and_eventing.md`
- 看媒体与文件：`.agentdocs/architecture/media_storage_and_files.md`
- 看当前执行证据：从当前 task root 下的 `evidence/` 进入
- 看当前 scratch：从当前 task root 下的 `scratch/` 进入

## 2) 当前任务（SSOT）
<!-- DEFAULT = 新会话默认先读的 workflow；同一时间应尽量只有一个 DEFAULT -->
<!-- ACTIVE = 并行任务，仅在明确允许并行时保留 -->
<!-- NONE -->

## 3) 长期知识（Canonical / Reusable）

- `insights.md`：跨任务可复用的工程/迁移/治理经验；本轮已吸收旧 index 的“全局重要记忆”正文。
- `architecture/backend_system_overview.md`：后端系统总览与服务边界。
- `architecture/backend_data_and_sync.md`：Electric / FastAPI / 数据同步与写路径口径。
- `architecture/agent_runtime_overview.md`：AgentScope Runtime / SDK / S2S / LiveKit 协作边界。
- `architecture/agent_runtime_orchestration.md`：sessions、orchestration、interrupt、tooling 编排。
- `architecture/agent_observability_and_eventing.md`：OTel、Run Store、Outbox、回放与观测。
- `architecture/media_storage_and_files.md`：媒体上传、complete、派生物与生命周期治理。
- `architecture/backend_technical_debt.md`：长期技术债清单。

## 4) 兼容、治理与操作提示

- 新的高熵任务统一进入 `.agentdocs/tasks/<task-id>/`，由 `workflow.md` / `plan.md` / `task-packs/` 承担当前运行时 SSOT。
- `.agentdocs/workflow/*.md` 继续保留为 legacy reference layer，用于兼容旧路径引用；若要继续演进某个 legacy 主题，应新建 task-scoped 任务并回链原文。
- legacy workflow 迁移清单（删除前必读）：`.agentdocs/archive/260312-fastapi-agent-closeout/findings/p3-legacy-workflow-migration.md`
- `.agentdocs/workflow/done/` 是旧版归档层，不等同于新的 `.agentdocs/archive/` task bundle archive。
- legacy `backend/**` 与旧名 `architecture/**` 文件继续保留为兼容 stub / pointer，不再作为活跃 SoT；长期事实优先读取上面的 canonical architecture 文档。
- 旧 index 的“全局重要记忆”已经分流：
  - 产品/运行时经验：`.agentdocs/insights.md` 的“旧 index 全局记忆迁移（2026-03-12）”
  - 架构事实：直接读取现有 `architecture/*.md`
  - 操作提示：继续保留在本索引
- 如涉及 Electric / AgentScope / LiveKit / fastapi-boilerplate，请按仓库技能目录进一步阅读对应 `.codex/skills/*/SKILL.md`
- Git 推送前必须运行 `/skill pre-push-check`

## 5) Archive 与 Legacy 导航

- 新 archive task bundle 入口：`.agentdocs/archive/index.md`
- archive task bundle 明细统一从 `.agentdocs/archive/index.md` 进入，避免在本索引重复维护一份会自行陈旧的列表。
- 旧 `workflow/done/` 任务仍可读，但只作为 legacy reference，不会被冒充为新 archive bundle。

## 6) Legacy workflow 参考文档

- `workflow/260104-migrate-backend-docs-to-fastapi-boilerplate.md` - 基于 FastAPI-boilerplate 重构后端设计文档
- `workflow/260111-agent-backend-architecture-setup.md` - Agent Backend 架构评价与实施路径建议
- `workflow/260118-agent-backend-macro-architecture-analysis.md` - Agent 后端宏观架构分析
- `workflow/2601271550-observability-implementation-plan.md` - 全链路观测开发执行规划
- `workflow/2601271909-observability-task.md` - 全链路观测落地执行跟踪
- `workflow/2602031143-agent-backend-orchestration-refactor-v2-sot.md` - Agent Backend 编排模块重构方案 SoT
- `workflow/2602052223-agent-voice-implementation-plan.md` - 语音能力接入实施方案
- `workflow/2602102130-realtime-livekit-agent-task.md` - Realtime（LiveKit self-host + livekit-agent）方案文档
- `workflow/2602121830-livekit-agent-phase-e3-implementation-task.md` - Realtime livekit-agent Phase E3 实装任务
- `workflow/2602122142-realtime-livekit-fix-plan.md` - Realtime（LiveKit）修复方案
- `workflow/2602130932-realtime-livekit-fix-plan-review.md` - Realtime（LiveKit）E3 实机问题复核与 fix-plan 评估
- `workflow/2602131031-realtime-livekit-fix-execution-task.md` - Realtime（LiveKit）E3 实机问题修复执行
- `workflow/2602122230-attachments-awareness-followup-task.md` - attachments awareness 提示增强与回归补齐
- `workflow/2602131000-livekit-standalone-deployment-plan.md` - LiveKit 独立服务器部署方案
- `workflow/2602281120-runtime-business-audit.md` - Runtime 业务架构与工程规范审查

## 7) Legacy 已归档任务（workflow/done）

### Realtime

- `workflow/done/2602121231-realtime-livekit-review-fix-task.md` - Realtime（LiveKit）代码审查与修复任务
- `workflow/done/2602121245-livekit-agent-structure-refactor-task.md` - livekit_agent 目录结构重排任务
- `workflow/done/2602121535-livekit-compose-env-source-unify-task.md` - LiveKit compose 环境变量来源统一任务

### Chat

- `workflow/done/2602091241-chat-responses-streaming-issues-analysis.md` - `/api/v1/chat` / `/api/v1/responses` 五个问题复盘与根因分析
- `workflow/done/2602091744-chat-coldstart-history-state-fix-task.md` - `/api/v1/chat` 冷启动回填 + agent_state 双写修复任务
- `workflow/done/2602091926-chat-fix-review.md` - `/api/v1/chat` 修复审查与 E2E 失败复盘
- `workflow/done/2602101027-react-text-order-regression-analysis.md` - ReAct 多轮 reasoning/tool 场景 text 顺序回退分析
- `workflow/done/2602101756-attachments-awareness-hint-design.md` - 附件感知与冷启动回填修复方案设计文档

### Voice

- `workflow/done/2602061616-agent-voice-kickoff-review.md` - 语音能力接入 Kickoff 评审与落地准备
