# AstraFlow Insights

> 只沉淀跨任务可复用的工程/迁移/治理经验；不复制单次 workflow 正文，不替代专题架构 SoT。

## 使用规则

- 仅收录可跨任务复用的稳定经验。
- 单次任务的执行日志、临时方案和 rollout 细节不进入本文件。
- 若某条规则更适合成为专题架构 SoT，应优先写入 `architecture/`，这里只保留跨主题的抽象结论。

## 当前沉淀

### 1. 目录模型升级先拆“运行入口兼容”和“长期正文迁移”

- 先完成 task-scoped 入口、状态真源和导航收口，再推进长期文档的物理迁移与 canonical target 调整。
- 这样可以先让新流程稳定运行，避免在同一轮里同时处理状态机迁移与大范围路径变更。
- 来源：`.agentdocs/archive/260308-agentdocs-v2-migration/workflow.md`、`.agentdocs/archive/260308-agentdocs-v2-migration/evidence/E01-align-inventory.md`、`.agentdocs/archive/260308-agentdocs-v2-migration/evidence/E02-build-index-migration.md`

### 2. 路径稳定性优先于目录美观

- 当旧路径已经被仓库内多处引用时，优先采用“新 canonical target + 旧路径 stub/pointer”的迁移方式，而不是直接删除或整体搬迁。
- 先保兼容，再分轮次收敛外部引用，可以显著降低迁移期的断链风险。
- 来源：`.agentdocs/archive/260308-agentdocs-v2-migration/evidence/E01-align-inventory.md`、`.agentdocs/archive/260308-agentdocs-v2-migration/evidence/E04-backend-doc-inventory.md`

### 3. `architecture/` 只承接长期 SoT / 架构蓝图

- 是否迁入 `architecture/`，取决于文档回答的是“系统边界 / 职责 / 分层 / 演进约束”，而不是它当前放在哪个目录下。
- implementation spec、data spec、debt、engineering spec 应继续留在各自更贴近语义的层次，避免因为目录收敛而失去类型边界。
- 来源：`.agentdocs/archive/260308-agentdocs-v2-migration/scratch/backend-doc-classification.md`

### 4. 跨服务共享配置与身份口径必须由测试锁定

- 只在文档里声明共享配置、身份字段或服务间约束是不够的；只要它会被 FastAPI / runtime / worker 等多个边界共同依赖，就应补充测试或验证梯子来锁定口径。
- 这样能减少“文档已更新但实现漂移”的隐性回归。
- 来源：`.agentdocs/workflow/2602281120-runtime-business-audit.md`

### 5. 旧 index 全局记忆迁移（2026-03-12）

- 来源：旧 `.agentdocs/index.md` 的“全局重要记忆”区块（原 85-174 行），在 V3 热路径重写时迁移到本文件与现有 `architecture/*.md` 引用。
- 迁移规则：已有明确 architecture SoT 的条目只保留指针，不在这里复制 canonical 正文；这里主要保留跨任务复用的运行时经验、兼容坑点和操作不变量。

#### 5.1 已转为 architecture 指针的条目

- 原 86-90 行（Electric / media / rate-limit 稳定架构事实）请直接读取：
  - `architecture/backend_data_and_sync.md`
  - `architecture/media_storage_and_files.md`
  - `architecture/backend_system_overview.md`
- 原 104、109-117、127-133、164-172 行（runtime 服务边界、session / S2S / room 约束、基础观测主路径）请直接读取：
  - `architecture/agent_runtime_overview.md`
  - `architecture/agent_runtime_orchestration.md`
  - `architecture/agent_observability_and_eventing.md`
  - `architecture/backend_system_overview.md`

#### 5.2 产品 / 范围记忆

- 快速开发版聚焦：速记、日记、Agent、家庭（不含天赋、待办、健康、Agent 记忆）

#### 5.3 Chat / Responses / Session / Attachments 集成记忆

- Vercel AI SDK：FastAPI 新增 `/api/v1/chat`（UI Message Stream，SSE `data:` 行），并复用 Responses Proxy 的幂等/锁/落库/断流 detach 语义；`messageId/reasoningId` 由 `Idempotency-Key` 确定性生成；`textId` 在此基础上按 `output_index` 分段生成；生产 Nginx 需对 `/api/v1/chat` 关闭 buffering（`proxy_buffering off`）。
- UI Message Stream 顺序：延迟发送 `text-start`，仅在首次 `text-delta` 或 completed fallback 前发送，确保 parts 严格按事件到达顺序构建。
- `/api/v1/chat` 多段 text part：翻译层按 Responses SSE 的 `output_index` 切分并生成独立 `text-start/text-delta/text-end`，避免 ReAct 场景多段文本被错误合并。
- 冷启动回填一致性口径：以“prompt 等价（模型输入等价）”为准，不强求 SessionHistory JSON deep-equal。
  - DB 快照 SoT：`chat_session_runtime_snapshots` + 内网 `GET/PUT /internal/system/chat/runtime-snapshot`
  - runtime 冷启动：SessionHistory 为空时优先从 snapshot 回填；无 snapshot 才 fallback `/internal/system/chat/context`
  - fallback `/internal/system/chat/context` 文本桥接需拼接同一 response 内所有 `type=="message"` 的 `output_text` 并过滤纯空白
  - `agent_state` 默认写入 Redis StateService；DB snapshot 由后台 worker 在 Redis TTL 临期时导出
  - `RUNTIME_SNAPSHOT_COMMIT_UPSERT_MODE=seed/missing/always` 仅作为低频兜底，不替代默认后台导出路径
- `adapt_agentscope_message_stream` 的尾部空/纯空白 TextContent 必须在 `message.completed` 处过滤，避免污染 `response.completed` 和 DB transcript。
- ReAct tool 前空白 text 必须在 stream 层缓冲并丢弃，避免 DB 出现 `content=[]` 的 message 空壳，也避免前端因空白 delta 提前 text-start 导致 parts 顺序回退。
- `/api/v1/chat` UIMessage 附件：`parts[].type=="file"` 的 `url` 统一为媒体系统 `files.id`；后端映射为 Responses `input_image/input_audio` 并复用 attachments side-channel；当前仍要求同一条 user message 中存在非空 text part。
- 附件感知提示通过 `attachments side-channel -> Agent awareness` 路径落地：runtime 在 `attachments_index` revision 变化/缺失时追加内部 `<system-hint>`，并把 `attachments_hint_revision` 写入 StateService 与 runtime snapshot 用于去重和冷启动恢复。
- Responses 并发治理与附件旁路：
  - session single-flight：FastAPI 使用 Redis 锁 `"{KEY_PREFIX}:agent:session_lock:{user_id}:{session_id}"`
  - interrupt：FastAPI 写入 Redis 信号 `"{KEY_PREFIX}:agent:interrupt:{user_id}:{session_id}:{request_id}"`，runtime watcher 命中后触发 `agent.interrupt()`
  - attachments side-channel：FastAPI 强制覆盖 `metadata.astraflow_attachments`（JSON string），runtime 解析并维护 `attachments_index`
  - prewrite user message 去重仅按 `Idempotency-Key(request_id)`，不按 `content_hash`
  - Responses Proxy 代码结构：`src/app/domains/agent/responses_proxy.py` 是稳定门面，实现拆分在 `src/app/domains/agent/responses/`

#### 5.4 Realtime / Voice / Responses 运行时坑点

- livekit-agent Phase E2 最小闭环需要同时验证：OTel 初始化 + W3C 传播、S2S JWT 缓存/续期、`/internal/responses` SSE 解析、文本增量转 TTS publish；debug 可用 `LIVEKIT_AGENT_BOOTSTRAP_USER_TEXT`。
- livekit-agent Phase E3 最小闭环：远端音频帧 -> 轻量 VAD/utterance -> DashScope ASR -> `/internal/responses` -> TTS publish；用户说话开始时触发“本地取消 + `POST /internal/system/responses/interrupt`”；TTS 请求必须支持外部注入 `request_id` 以精确打断。
- Agent 看图（Phase 1）：FastAPI 提供 `/internal/media/files/{file_id}/download-url`；runtime builtin 工具 `view_image` 支持 `index/file_id/image_url` 三选一；`image_url` 必须做域名 allowlist。
- tool output 不进入 OpenAI Responses SSE output items；如需观测，仅在 debug-only 通过 `astraflow.debug.tool_output` chunk 输出，且不进入 `response.completed`/DB。
- Responses Proxy 幂等与 completed 回放：
  - `Idempotency-Key` 必填；`metadata.request_id` 默认等同 `Idempotency-Key`
  - `X-Request-Id` / `metadata.attempt_request_id` 只用于监控
  - `in_progress` 返回 `409 + Retry-After: 1`
  - completed 回放必须合成最小 Responses SSE 事件流，不能只回放单个 `response.completed`
  - completed 侦测要同时兼容 `event: response.completed` 与 `data.type == "response.completed"`
- agentscope-runtime `v1.0.4` Responses SSE 已知坑：tool_use 被标记为 `plugin_call` 并在 Responses 适配层丢弃；reasoning 的 `output_index` 可能错位；`function_call` 的 `output_item.added.item.id` 可能缺失。
- SSE message 文本收口坑：若 upstream completed TextContent 缺少 `msg_id/index`，ResponsesAdapter 会丢弃该事件并缺失 `response.output_text.done` / `response.content_part.done`；需要在 `message.completed()` 前补齐 `message.content_completed(...)`。
- Vercel Responses 流解析约束：`@ai-sdk/openai` 只解析 SSE `data` 中的 JSON，并强依赖顶层 `type` 字段；任何 FastAPI 合成事件都必须包含 `{\"type\":\"...\"}`。
- reasoning summary 顺序约束：`response.reasoning_summary_part.done` 必须早于 `response.output_item.done(reasoning)`，否则前端可能在 reasoning state 已清理后崩掉。
- StreamingResponse 断连坑：客户端提前断开会触发 anyio cancel scope；清理路径必须 shield，否则可能污染 DB 连接池并导致 `asyncpg: connection is closed`。
- TaskGroup keepalive 坑：在 `anyio.create_task_group()` 中启动无限循环 keepalive/续租协程时，主任务结束后必须显式 cancel，否则 task group 不退出。
- detach pump 取消坑：不要在 StreamingResponse 的请求上下文里用 `asyncio.create_task()` 启动后台 pump；应挂到 app 级 `TaskGroup`，否则下游断流会导致 finally 清理不执行。

#### 5.5 Tools / Config / Ops / 观测补充记忆

- OpenAI-compatible provider 可能严格拒绝空文本；runtime 在模型调用前必须清洗 messages，SessionHistory 适配层也要过滤空 `TextBlock(text=\"\")`。
- `create_tables_on_start` 仅允许 `local` 环境启用；staging/production 必须通过 Alembic 迁移。
- 历史兼容路由 `DELETE /api/v1/db_user/{username}` 与 `DELETE /api/v1/{username}/db_post/{id}` 已统一为软删除语义。
- agentscope-runtime Tool 的入参不能泛型写成 `BaseModel`；每个工具都必须绑定具体 `*Input(BaseModel)`，并在适配层对 `ToolResponse(metadata.error=True)` 打日志。
- runtime tools 约束：
  - 写入类工具幂等键统一使用 `request_id:tool_name:tool_call_id`
  - `tool_call_id` 缺失时拒绝执行写入
  - `tool_call_id` 禁止从泛化字段 `id` 兜底
  - `ToolPack` 是配置层工具包，不等同于 agentscope `Toolkit.group`
  - runtime 工具装配入口统一使用 `services/agentscope_runtime/tools/assembly.py::register_enabled_tool_packs_to_toolkit`
  - Tools Registry 收敛为 `pack_name -> builder`
  - 显式配置 `RUNTIME_TOOLS_ENABLED_PACKS` 时，unknown pack 不再静默
  - 注册到 SDK `Toolkit` 时优先用公开 API `Toolkit.register_tool_function(..., json_schema=...)`
  - ToolPack 默认启用集合为 `diaries,quick_notes,view_image,transcribe_audio`
- 共享配置与 MCP / ContextVar 约束：
  - 配置中心统一使用 `pydantic_settings.BaseSettings`
  - 跨服务共享配置（如 `KEY_PREFIX`、`S2S_JWT_SECRET/S2S_JWT_ISSUER`、`INTERNAL_SERVICE_SECRET` alias）必须由单测锁定
  - `modelstudio_search_lite` 直连 builtin tool import，不通过 MCP server
  - `linear_mcp` 通过 AgentScope SDK MCP client 接入，推荐 `transport=streamable_http`，且仅允许 stateless
  - MCP tool 列表应在 warmup 阶段缓存，避免每请求 `list_tools()`
  - MCP server 默认不透传 `user_id/session_id/trace_id/request_id` 等内部治理字段
  - ToolRequestContext 承载请求级治理字段；仅启用 MCP tools 时不再 set/reset
  - ToolCallContext 承载调用级关联字段，清理统一下沉到 `Toolkit.postprocess_func`
- 开发与热重载注意事项：
  - `watchfiles` 热重载需 ignore `.venv`，避免宿主机权限不一致导致 `Permission denied`
  - 为避免 `docker compose watch` 被 `__pycache__/*.pyc` 触发 `sync+restart`，测试禁写 `.pyc`，compose 运行的 Python 服务设置 `PYTHONDONTWRITEBYTECODE=1`
- 观测 / Studio 运行时操作提示：
  - 观测传播主路径是 W3C `traceparent` + `baggage`
  - `OTEL_TRACES_EXPORTER=none` 时仍要初始化 propagator + tracer
  - FastAPI -> runtime 的出站请求需显式 `propagate.inject(headers)`
  - `otel-collector` 的 OTLP receiver 在 docker-compose 场景必须显式监听 `0.0.0.0:4318/4317`
  - 观测镜像 tag 通过 `OTEL_COLLECTOR_IMAGE_TAG` / `JAEGER_IMAGE_TAG` 覆盖
  - AgentScope Studio 只能用于单次交互调试，服务形态必须禁用
