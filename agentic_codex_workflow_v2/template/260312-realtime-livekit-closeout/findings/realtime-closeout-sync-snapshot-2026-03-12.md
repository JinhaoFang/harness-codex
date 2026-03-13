# Realtime + LiveKit Closeout Sync Snapshot (2026-03-12)

> 目的：把 `realtime/livekit` 的 legacy workflow 叙述与代码事实快速对齐，形成本轮 closeout 的共同基线。  
> 结论以代码 / 测试 / 配置为准；legacy workflow 只作为历史参考与 TODO 线索。

## 0) Repo / task baseline

- 上一轮 `fastapi + agent` 收尾任务已归档：`.agentdocs/archive/260312-fastapi-agent-closeout/workflow.md`
- 当前活动任务切换为：`.agentdocs/archive/260312-realtime-livekit-closeout/workflow.md`
- 当前 realtime closeout 的目标不是“继续加新功能”，而是把现有实现收束成可复核的完成态。

## 1) 已完成且有代码锚点支撑的部分

### 1.1 Realtime 主链路

- LiveKit token/control plane 已存在：`src/app/api/v1/rtc.py`、`src/app/core/rtc.py`
- LiveKit worker 主入口、音频消费、VAD/ASR、`/internal/responses`、TTS publish 已存在：`services/livekit_agent/app/worker_entrypoint.py`
- TextStream 对齐已存在：`services/livekit_agent/adapters/livekit_text_stream.py`

### 1.2 P0/P1 修复

- interrupt 竞态治理：turn gate + cancel barrier
- sid 变化触发 cleanup：connection_generation + hard_stop/drain
- assistant/user 文本走 `lk.transcription`
- chunker v2

对应代码锚点：

- `services/livekit_agent/app/worker_entrypoint.py`
- `services/livekit_agent/pipelines/realtime_text_to_speech.py`
- `services/livekit_agent/core/text_chunker.py`

### 1.3 false interruption resume

- 已由单独任务完成，不应继续被视为未实现：
  - 文档：`.agentdocs/workflow/2602131555-livekit-agent-false-interruption-resume-task.md`
  - 代码：`services/livekit_agent/core/interruption_gate.py`
  - 代码：`services/livekit_agent/app/worker_entrypoint.py`
  - 测试：`tests/services/livekit_agent/core/test_interruption_gate.py`

### 1.4 5xx/断流重试、interrupt 重试、voice-mode thinking

- `/internal/responses` 首输出前有限重试：`services/livekit_agent/adapters/fastapi_internal_client.py`
- `/internal/system/responses/interrupt` 网络错误/5xx 有限重试：`services/livekit_agent/adapters/fastapi_internal_client.py`
- ASR/TTS 最小超时：`services/livekit_agent/adapters/dashscope_asr.py`、`services/livekit_agent/adapters/dashscope_tts.py`
- voice/text thinking 分流：`services/agentscope_runtime/agent/factory.py`
- 测试：`tests/services/agentscope_runtime/test_voice_mode_prompt.py`

## 2) 真实剩余项（closeout scope 内）

### 2.1 E4 验收闭环仍未完成

- 手动验收清单还没固化到 task-scoped closeout 文档：
  - `Playground / App join`
  - interrupt 是否“尽快静音 + 不续播历史”
  - `lk.transcription` 是否可见
  - Jaeger 中的关键 span / attributes 是否可见

### 2.2 最小自动化回归范围仍未统一

- 文档多处提到“补齐最小自动化”，但当前还没有一个 closeout 级别的统一回归清单。
- 现有服务测试覆盖了 gate / TextStream / Retry-After / voice-mode 等，但未见直接覆盖 `disconnect cleanup / connection_generation` 的明确测试锚点。

### 2.3 Jaeger 结构验证仍未回填

- `.agentdocs/workflow/2602121821-livekit-agent-e3-hardening-tracing-task.md` 仍保留 “Jaeger 结构验证” 未完成。

### 2.4 `openai` 显式依赖仍是实质风险

- 代码中存在 `from openai import AsyncOpenAI`：`services/livekit_agent/adapters/dashscope_asr.py`
- 但 `services/livekit_agent/pyproject.toml` 尚未显式声明 `openai`
- `services/livekit_agent/uv.lock` 中已有 transitive `openai`，说明当前运行依赖于传递依赖而非显式契约

## 3) 明显文档漂移

### 3.1 主 SoT 旧 TODO 未回填

- `.agentdocs/workflow/2602102130-realtime-livekit-agent-task.md`
  - 仍把 `false interruption resume` 写为未完成
  - 仍把 5xx/断流治理写为待补齐
  - 仍把 E4 验收与最小自动化列为未完成

### 3.2 README 漂移

- `services/livekit_agent/README.md` 仍写“未覆盖 false interruption resume”，与代码事实不符。

### 3.3 部分中间执行文档分析段已过时

- `.agentdocs/workflow/2602131414-realtime-e3-enhancements-voice-mode-e4-task.md` 的分析区仍写 `false interruption resume 当前未见实现`，但 TODO/代码已被后续任务覆盖。

## 4) 本轮冻结边界

- 只做：
  1. `E4` 验收闭环
  2. `openai` 显式依赖补齐
  3. `README / 关键 workflow` 状态统一
- 不做：
  1. `WS realtime TTS`
  2. 进一步性能/听感优化
  3. 新的 UX/体验增强设计
  4. 非 realtime 模块收尾
