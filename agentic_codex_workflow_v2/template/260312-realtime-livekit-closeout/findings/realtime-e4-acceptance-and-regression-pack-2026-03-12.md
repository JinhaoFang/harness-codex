# Realtime E4 Acceptance and Regression Pack (2026-03-12)

> 目的：把 `realtime/livekit` 本轮 closeout 还剩的 `E4` 验收与最小回归从“分散 TODO”收束成一个可直接执行、可复核的包。  
> 事实判断以代码 / 测试 / 配置为准；本文件只负责把 closeout 所需的验证路径写清楚。

## 0) 范围冻结

- 本文件只覆盖 3 类 closeout 尾项：
  1. `E4` 手动验收
  2. 最小自动化回归范围
  3. Jaeger 结构验证与 remaining manual UAT 义务
- 不在本文件内扩展：
  - `WS realtime TTS`
  - 新的打断体验设计
  - 更深的弱网/性能优化
  - 非 realtime 模块收尾

## 1) 当前事实锚点

- 主链路入口：`services/livekit_agent/app/worker_entrypoint.py`
- false interruption resume / cooldown：`services/livekit_agent/core/interruption_gate.py`
- internal responses / interrupt 重试：`services/livekit_agent/adapters/fastapi_internal_client.py`
- ASR OpenAI-compatible client：`services/livekit_agent/adapters/dashscope_asr.py`
- 文本可见性：`services/livekit_agent/adapters/livekit_text_stream.py`
- voice/text thinking 分流：`services/agentscope_runtime/agent/factory.py`
- RTC token 契约：`src/app/api/v1/rtc.py`、`src/app/core/rtc.py`

## 2) 最小自动化回归范围

### 2.1 统一命令

- Lint：
  - `UV_CACHE_DIR=.uv_cache uv run ruff check services/livekit_agent services/agentscope_runtime tests/services/livekit_agent tests/services/agentscope_runtime tests/api/v1/test_rtc_token.py`
- Tests：
  - `ASTRAFLOW_TEST_USE_UVLOOP=1 UV_CACHE_DIR=.uv_cache uv run pytest -q tests/services/livekit_agent tests/services/agentscope_runtime/test_voice_mode_prompt.py tests/api/v1/test_rtc_token.py`

### 2.2 场景覆盖矩阵

| 场景 | 自动化锚点 |
|---|---|
| false interruption 的 pause / confirm / resume / cooldown | `tests/services/livekit_agent/core/test_interruption_gate.py` |
| `/internal/responses` 401 刷新、409 `Retry-After`、5xx/断流首输出前有限重试、interrupt 5xx/网络错误重试、W3C headers 注入 | `tests/services/livekit_agent/adapters/test_fastapi_internal_client.py` |
| `lk.transcription` 文本可见性契约 | `tests/services/livekit_agent/adapters/test_livekit_text_stream.py` |
| stop/turn gate 后不续播历史文本、TTS pipeline 取消治理 | `tests/services/livekit_agent/pipelines/test_realtime_text_to_speech.py` |
| 文本切片规则（chunker v2） | `tests/services/livekit_agent/core/test_text_chunker.py` |
| utterance/VAD 基础行为 | `tests/services/livekit_agent/core/test_voice_activity.py` |
| ASR OpenAI-compatible 适配行为 | `tests/services/livekit_agent/adapters/test_dashscope_asr.py` |
| voice/text thinking 分流 | `tests/services/agentscope_runtime/test_voice_mode_prompt.py` |
| RTC token 契约（identity=`user_id`、room=`session_id`） | `tests/api/v1/test_rtc_token.py` |

### 2.3 自动化未直接覆盖的风险

- `connection_generation` / duplicate identity reconnect / `participant_disconnected` cleanup 目前未见直接单测锚点。
- 因此这些场景必须进入手动验收 checklist，不能只依赖自动化回归通过来宣布 closeout。

## 3) 手动验收 checklist

### 3.1 环境前提

- `docker compose` 中至少保证以下服务可用：`web`、`livekit`、`livekit-agent`、`otel-collector`、`jaeger`
- 客户端可使用：
  - 现有 App/Web 语音入口；或
  - LiveKit Playground / 任一能加入同一 room 的测试客户端
- Jaeger UI：`http://localhost:16686`

### 3.2 Checklist

1. **Join / 首轮播报**
   - 获取 `/api/v1/rtc/token`，以 `identity=user_id`、`room=session_id` 加入房间。
   - 触发一次语音请求或 bootstrap 文本请求。
   - 通过标准：
     - 房间内能听到 assistant 音频；
     - 客户端能看到 `lk.transcription` 文本增量；
     - livekit-agent 未绕过 FastAPI，日志/trace 中可见 `/internal/responses`。

2. **真实打断（confirm）**
   - 在 assistant 已经开始播报后，连续说话超过 `confirm_speech_ms`。
   - 通过标准：
     - 当前播报尽快静音；
     - 旧 turn 不会在静音后继续续播；
     - 后续由新的用户输入触发新的 request / 回答。

3. **误打断恢复（resume）**
   - 在 assistant 已经开始播报后，制造一次短噪声/咳嗽/极短语音，持续时间明显短于 `confirm_speech_ms`，随后保持静音直到超过 `cancel_silence_ms`。
   - 通过标准：
     - 播报会短暂停顿后恢复同一 turn；
     - 不会因为这次误触发产生新的 assistant 回合；
     - 不会把短噪声残留成新的 transcript / 新请求。

4. **断连 / 重连 cleanup**
   - 在 assistant 播报期间执行下列任一操作：
     - 当前客户端主动断开；
     - 同一 `identity=user_id` 的新客户端重新加入房间（触发 sid 变化）。
   - 通过标准：
     - 旧播报立即停止；
     - 旧 backlog 不会在重连后继续播放；
     - 新连接建立后，后续回合按新连接继续，不出现乱序续播。

5. **Jaeger 结构验证**
   - 在 Jaeger 选择 `service=astraflow-livekit-agent`。
   - 至少检查一条正常回合与一条打断回合。
   - 通过标准：
     - 可见 `utterance` 根 span；
     - 可见关键子阶段 span：`dashscope.asr.transcribe`、`fastapi.internal_responses`、`dashscope.tts`；
     - 发生真实打断时可见 `fastapi.interrupt`；
     - span attributes 中可见 `astraflow.session_id`、`astraflow.user_id`、`astraflow.request_id`；
     - 正常播报回合可见 `astraflow.first_audio_latency_ms`，便于继续追查首音频指标。

## 4) Closeout 判定口径

- 下列条件同时满足，才可把 realtime/livekit 收尾推进到 close review：
  - `2.1` 的 lint/tests 全部通过
  - `3.2` 的手动验收 checklist 已执行，或明确记录为待用户执行的 UAT obligation
  - README 与关键 legacy workflow 不再把已完成项写成未完成
  - `openai` 显式依赖已从“传递依赖碰巧可用”升级为显式契约

## 5) Remaining UAT obligation（若当前会话无法实机跑）

- 若当前会话不启动 compose / App / Playground，则必须把以下事项保留为用户侧 UAT：
  - `3.2.1` Join / 首轮播报
  - `3.2.2` 真实打断
  - `3.2.3` 误打断恢复
  - `3.2.4` 断连 / 重连 cleanup
  - `3.2.5` Jaeger 结构验证
- 这种情况下，close review 只能判断“代码/测试/文档 closeout 是否成立”，不能替代实机语音体验验收。
