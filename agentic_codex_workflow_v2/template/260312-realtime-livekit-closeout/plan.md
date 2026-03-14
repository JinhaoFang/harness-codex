---
task_id: 260312-realtime-livekit-closeout
slug: realtime-livekit-closeout
title: 快速开发版收尾：Realtime + LiveKit
workflow: .agentdocs/archive/260312-realtime-livekit-closeout/workflow.md
issue: N/A
status: draft
updated_at: 2026-03-12 21:33 +0800
---

# Plan：快速开发版收尾：Realtime + LiveKit

## 0) 元信息

- Task ID: 260312-realtime-livekit-closeout
- Workflow: .agentdocs/archive/260312-realtime-livekit-closeout/workflow.md
- Issue: N/A
- Status: DRAFT
- Updated At: 2026-03-12 21:33 +0800

---

## 1) Understanding Proof

- Goal Restatement: 以代码/测试/配置事实为准，给 realtime/livekit 做一次“但完整”的 closeout：把真实剩余项补齐，把 README/legacy workflow 的状态漂移收束到单一 task-scoped SSOT。
- Explicit Non-Goals:
  - 不继续开发 `WS realtime TTS`、更深的性能优化、听感优化、弱网策略扩展。
  - 不重开 FastAPI / runtime 主干审计；本轮只处理 realtime 关联的闭包。
  - 不把 observability Phase 1、media 主线、attachments awareness follow-up 混入本轮。
  - 不维护整条 legacy realtime workflow 链为“第二套活 SoT”；只更新最关键的误导性状态。
- Why This Task Exists Now:
  - 前一轮 `fastapi + agent` 收尾已经归档；接下来按顺序进入 `realtime`。
  - realtime/livekit 的实现已经远超最初 SoT 文档，但 workflow 链仍残留大量已过时 TODO，容易误导后续判断“到底还差什么”。
- 95% Understanding Check: YES
- Missing Pieces:
  - <none>

---

## 2) What I Need / My Requirements / You Decide

### 2.1 What I Need

- User Outcome:
  - 你能明确回答：realtime/livekit 现在究竟还剩什么，并且该结论能由代码/测试/配置/任务文档复核。
- Deliverable:
  - 本 task 的 `workflow.md + plan.md + findings/*.md`
  - 必要的代码/文档修复：`openai` 显式依赖、README/关键 workflow 状态统一
  - `E4` 手动验收清单与自动化回归范围
  - 对应 evidence bundle 与 review artifacts
- Acceptance Signal:
  - realtime closeout 范围内的真实尾项都被处理或受控下沉为 follow-up；
  - targeted lint/tests 通过；
  - 文档不再把已完成项描述成未完成；
  - `E4` 清单可直接执行。

### 2.2 My Requirements

- Hard Constraints:
  - livekit-agent 不得绕过 FastAPI 直连 runtime/DB。
  - 推理仍通过 `/internal/responses`；interrupt 仍通过 `/internal/system/responses/interrupt`。
  - 不引入新服务/新架构/新长期模块。
  - `PLAN_REVIEW=PASS` 前不进入 BUILD；`CLOSE_REVIEW=PASS` 前不进入 ARCHIVE。
- Preferred Constraints:
  - 优先“收束状态与证据”，避免“顺手再做一点”导致 scope 漂移。
  - 只更新最关键的 legacy realtime 文档，不回头大规模维护整个 `workflow/` 历史链。
  - 优先补自动化回归；无法自动化的部分写死为手动验收步骤和判据。
- Non-Negotiables:
  - 代码事实优先于文档叙述。
  - `false interruption resume` 不再当成待开发功能；如果要处理，只处理“文档状态”。

### 2.3 You Decide

- Agent Decision Space:
  - 我可以自行决定哪些 legacy TODO 判定为“已完成但未回填”。
  - 我可以自行决定自动化回归的具体测试组合，只要覆盖最容易回归的 realtime 风险点。
  - 我可以自行决定要更新哪些最关键的 legacy workflow 文档，以修改消除误导。
- Decisions Requiring User Confirmation:
  - <none>
- Escalation Triggers:
  - 若 `openai` 显式依赖补齐必须引入额外升级/锁文件大改；
  - 若 closeout 过程中发现 realtime 主链仍存在未预期的结构性缺口；
  - 若需要把 scope 扩展到 `WS TTS`、性能调优或额外体验功能。

---

## 3) 当前事实锚点（Current Truth Anchors）

### 3.1 Code Paths

- `.agentdocs/archive/260312-realtime-livekit-closeout/findings/realtime-closeout-sync-snapshot-2026-03-12.md`
- `.agentdocs/workflow/2602102130-realtime-livekit-agent-task.md`
- `.agentdocs/workflow/2602121821-livekit-agent-e3-hardening-tracing-task.md`
- `.agentdocs/workflow/2602131031-realtime-livekit-fix-execution-task.md`
- `.agentdocs/workflow/2602131414-realtime-e3-enhancements-voice-mode-e4-task.md`
- `.agentdocs/workflow/2602131555-livekit-agent-false-interruption-resume-task.md`
- `services/livekit_agent/**`
- `tests/services/livekit_agent/**`
- `services/agentscope_runtime/agent/factory.py`
- `tests/services/agentscope_runtime/test_voice_mode_prompt.py`
- `src/app/api/v1/rtc.py`

### 3.2 Key Symbols / Entry Points

- `services/livekit_agent/app/worker_entrypoint.py`
- `services/livekit_agent/adapters/fastapi_internal_client.py`
- `services/livekit_agent/adapters/dashscope_asr.py`
- `services/livekit_agent/adapters/livekit_text_stream.py`
- `services/livekit_agent/core/interruption_gate.py`
- `services/livekit_agent/adapters/livekit_audio_publisher.py`
- `services/agentscope_runtime/agent/factory.py::build_model_generate_kwargs`

### 3.3 Tests / Checks

- Existing Tests:
  - `tests/services/livekit_agent/adapters/test_fastapi_internal_client.py`
  - `tests/services/livekit_agent/adapters/test_livekit_text_stream.py`
  - `tests/services/livekit_agent/core/test_interruption_gate.py`
  - `tests/services/livekit_agent/core/test_text_chunker.py`
  - `tests/services/livekit_agent/pipelines/test_realtime_text_to_speech.py`
  - `tests/services/agentscope_runtime/test_voice_mode_prompt.py`
  - `tests/api/v1/test_rtc_token.py`
- Missing Tests:
  - closeout 级别尚未统一写出“自动化回归组合”
  - 未见明确针对 `disconnect cleanup / connection_generation` 的直接测试锚点

### 3.4 Config / Env / Runtime

- Config Anchors:
  - `docker-compose.yml`
  - `services/livekit_agent/core/config.py`
  - `services/livekit_agent/pyproject.toml`
  - `services/livekit_agent/uv.lock`
- Runtime Evidence:
  - `services/livekit_agent/README.md`
  - Jaeger UI（文档验收目标）
- Notes:
  - `E4` 有手动验收成分；实际运行 evidence 依赖 compose / App / Playground / Jaeger 环境。

---

## 4) 背景与目标

- Problem:
  - realtime/livekit 文档链经过多轮 E3/E4、fix-plan、执行记录叠加后，存在“主线文档未回填、子任务已落地、README 仍停留旧说法”的混合状态。
- Goal:
  - 把 realtime/livekit 收敛到一个可信的 closeout 状态：真实尾项完成、文档不误导、验收与回归路径清晰。
- In Scope:
  - truth alignment + findings snapshot
  - `openai` 显式依赖补齐
  - `README` + 关键 legacy workflow 状态统一
  - `E4` 手动验收清单 + 自动化回归范围
  - targeted lint/tests + evidence
- Out of Scope:
  - `WS realtime TTS`
  - 新的体验增强（除 closeout 所需文档统一外）
  - 额外 observability/media/agent 范围
- Success Criteria:
  - realtime/livekit closeout 只剩“明确记录的后续优化”，而不再混杂“实际上已完成但文档没回填”的旧 TODO。

---

## 5) Memory Lookup 与 Context Coverage

### 5.1 Memory Lookup

- architecture Inputs:
  - `.agentdocs/architecture/backend_system_overview.md`
  - `.agentdocs/architecture/agent_runtime_overview.md`
  - `.agentdocs/architecture/agent_observability_and_eventing.md`
- insights Inputs:
  - `.agentdocs/insights.md`（仅在 closeout 中沉淀出跨任务经验时回写）
- Reused Rules:
  - `docs/dev/contracts/high-entropy-state-machine.md`
  - `docs/dev/contracts/task-pack-layout.md`
- Re-validation Needed:
  - <none>

### 5.2 Context Coverage Contract

- Must Read:
  - `AGENTS.md`
  - `.agentdocs/workflow/2602102130-realtime-livekit-agent-task.md`
  - `.agentdocs/workflow/2602121821-livekit-agent-e3-hardening-tracing-task.md`
  - `.agentdocs/workflow/2602131031-realtime-livekit-fix-execution-task.md`
  - `.agentdocs/workflow/2602131414-realtime-e3-enhancements-voice-mode-e4-task.md`
  - `.agentdocs/workflow/2602131555-livekit-agent-false-interruption-resume-task.md`
  - `.agentdocs/archive/260312-realtime-livekit-closeout/findings/realtime-closeout-sync-snapshot-2026-03-12.md`
- Adjacent Scan:
  - `.agentdocs/workflow/2602131329-realtime-optimization-next-steps.md`
  - `tests/e2e/test_agent_voice_transcript_e2e.py`
- Unread But Potentially Relevant:
  - `tests/e2e/test_voice_business_domains_e2e.py`
- Coverage Decision: SUFFICIENT
- Coverage Notes:
  - 当前已足够支持冻结 closeout 范围；E2E 细节只在需要扩展回归范围时继续展开。

### 5.3 Scratch Promotion Rule

- Scratch Dir: .agentdocs/archive/260312-realtime-livekit-closeout/scratch/
- Allowed Scratch Content:
  - workflow TODO 对账草稿、测试矩阵草稿、手动验收步骤草稿
- Promotion Required Before Build:
  - 所有“范围 / 验收 / 写入边界 / 真实剩余项”的结论必须提升到 plan/workflow/findings
- Scratch Close Condition:
  - CLOSE_REVIEW 前不再存在依赖 scratch 才能理解的结论

---

## 6) 已拍板事项（Decision Freeze）

### 6.1 技术 / 依赖 / 基础设施

- Selected:
  - 本轮 closeout 只处理 `E4`、显式依赖、状态统一
- Version / Constraint:
  - 维持现有 realtime 架构与服务边界
- Rejected Alternatives + Why:
  - 把 `WS TTS` 或更大范围体验优化一起做：会把 closeout 变成新功能开发
  - 重新维护整条 legacy workflow 历史链：成本高且会继续制造第二套 SoT
- Rollback Switch (if any):
  - 文档与依赖声明变更可直接回滚；测试变更保持闭包

### 6.2 数据 / 协议 / 公共口径

- Frozen Contracts:
  - livekit-agent 只经 FastAPI internal contract 进入推理/控制面
  - `lk.transcription` 仍是 Playground 可见文本流口径
  - `false interruption resume` 已实现，closeout 仅统一其状态表达

---

## 7) 契约与边界

### 7.1 Invariants

- Realtime plane 不直连 runtime/DB
- `traceparent + baggage` 仍是跨服务观测主路径
- `interrupt` 语义不因 closeout 而改变
- 不为 closeout 引入额外后台服务或长期模块

### 7.2 Interfaces / Data / Errors / Compatibility

- Inputs:
  - legacy realtime workflow、realtime 代码、服务测试、README、compose 配置
- Outputs:
  - task-scoped SSOT、必要的代码/文档修复、验证证据
- Public API / Schema Changes:
  - 默认不改 public API；若仅补依赖声明/文档/测试，不引入契约变化
- Error Strategy:
  - 优先修复；无法在本轮自动化闭环的部分写成明确手动 UAT
- Compatibility Strategy:
  - 关键 legacy workflow 仍保留为 reference，但不再允许其结论与代码事实冲突

### 7.3 Edge Cases

- Boundary Case 1:
  - 主 SoT 仍写未完成，但后续子任务和代码已实现 —— 以代码事实 + 新 task SSOT 为准
- Boundary Case 2:
  - 依赖是 transitive 可运行，但未显式声明 —— 视为 closeout 范围内的工程风险
- Timeout / Retry / Idempotency / Concurrency:
  - 本轮不改变已实现的 retry/interrupt 策略，只验证与统一口径

---

## 8) Must-Haves

### 8.1 Truths

- realtime 主链路已经实现到较高完成度，本轮不是从头补功能
- 真实尾项集中在 `E4`、显式依赖、文档漂移三类

### 8.2 Artifacts

- `.agentdocs/archive/260312-realtime-livekit-closeout/workflow.md`
- `.agentdocs/archive/260312-realtime-livekit-closeout/plan.md`
- `.agentdocs/archive/260312-realtime-livekit-closeout/findings/realtime-closeout-sync-snapshot-2026-03-12.md`
- `.agentdocs/archive/260312-realtime-livekit-closeout/evidence/*.json`

### 8.3 Key Links

- `.agentdocs/index.md`
- `.agentdocs/archive/260312-fastapi-agent-closeout/workflow.md`
- `.agentdocs/workflow/2602102130-realtime-livekit-agent-task.md`

---

## 9) Verification Ladder

- Static:
  - `UV_CACHE_DIR=.uv_cache uv run ruff check services/livekit_agent services/agentscope_runtime tests/services/livekit_agent tests/services/agentscope_runtime`
- Command:
  - `ASTRAFLOW_TEST_USE_UVLOOP=1 UV_CACHE_DIR=.uv_cache uv run pytest -q tests/services/livekit_agent tests/services/agentscope_runtime/test_voice_mode_prompt.py tests/api/v1/test_rtc_token.py`
- Behavioral:
  - 写出 `E4` 手动验收清单（Playground/App/Jaeger/interrupt/disconnect）
- Human:
  - 抽样核对 3 类条目：已完成、文档漂移、真实未完成
- Minimum Required For PASS:
  - truth matrix 完成 + `openai` 依赖风险处理 + README/workflow 状态统一 + targeted lint/tests 通过 + `E4` 清单落盘

---

## 10) Reviewer Recheck Plan

- Plan Reviewer Recheck:
  - 范围是否严格冻结在 `E4 / explicit dependency / doc drift`
  - 是否错误重开了已完成的 `false interruption resume` / `5xx 重试` / `voice mode` 功能
- Close Reviewer Recheck:
  - README 与关键 workflow 是否与代码事实一致
  - `openai` 显式依赖是否真正消除“传递依赖风险”
  - `E4` 验收与回归是否足以复核 closeout 结论
- Escalation To FULL_REVIEW If:
  - 需要修改 public contract、重开架构边界、或引入超出 closeout 的新功能

---

## 11) Issue Breakdown（issue 是 plan 的子结构）

### Issue 1 — Realtime truth alignment

- Goal:
  - 输出一份可复核的 realtime closeout 真相清单：哪些已完成、哪些是文档漂移、哪些是真缺口
- Depends On:
  - 无
- Write Boundary:
  - `.agentdocs/archive/260312-realtime-livekit-closeout/*`
- Verify:
  - findings 与代码/测试/legacy workflow 抽样对齐
- Rollback Note:
  - 文档变更可直接回滚

### Issue 2 — Close true code/doc gaps

- Goal:
  - 处理 `openai` 显式依赖、README 漂移、关键 workflow 状态统一
- Depends On:
  - Issue 1
- Write Boundary:
  - `services/livekit_agent/pyproject.toml`
  - `services/livekit_agent/uv.lock`
  - `services/livekit_agent/README.md`
  - 必要的 `.agentdocs/workflow/*.md`
  - `.agentdocs/archive/260312-realtime-livekit-closeout/*`
- Verify:
  - ruff + targeted pytest；文档抽样
- Rollback Note:
  - 依赖/文档修改可单独回滚

### Issue 3 — E4 acceptance and regression pack

- Goal:
  - 固化 closeout 级别的手动验收与自动化回归范围
- Depends On:
  - Issue 1
- Write Boundary:
  - `.agentdocs/archive/260312-realtime-livekit-closeout/*`
  - 必要时补充 `tests/services/livekit_agent/**`
- Verify:
  - checklist 可执行；新增/更新测试能证明最关键风险点
- Rollback Note:
  - 测试/文档可单独回滚

---

## 12) 分阶段规格（<= 7 phases）

说明：

- `workflow.md` 的 Phase Board 只跟踪执行 phase
- `PLAN_REVIEW / CLOSE_REVIEW` 的结论写在 workflow review sections，不把 `reviews/*.json` 当作 phase evidence

### P1 — Truth alignment + drift matrix

- Goal:
  - 完成 realtime 文档链与代码事实的 closeout 分类
- Output:
  - findings snapshot
  - 本 task workflow/plan 的对齐引用
- Files / Modules Touched:
  - `.agentdocs/archive/260312-realtime-livekit-closeout/*`
- Write Boundary:
  - 仅 task-scoped 文档
- Truth Anchors To Recheck:
  - `.agentdocs/workflow/2602102130-realtime-livekit-agent-task.md`
  - `.agentdocs/workflow/2602131031-realtime-livekit-fix-execution-task.md`
  - `services/livekit_agent/app/worker_entrypoint.py`
  - `tests/services/livekit_agent/**`
- Verify:
  - findings 与代码/测试抽样一致
- Evidence Bundle:
  - `.agentdocs/archive/260312-realtime-livekit-closeout/evidence/P1-*.json`
- Checkpoint Policy:
  - 进入 P2 前必须冻结“真缺口 vs 文档漂移”列表
- Risks / Notes:
  - 避免把已完成项重新带回实现范围

### P2 — Explicit dependency + doc-state cleanup

- Goal:
  - 关闭 closeout 范围内的真实代码/文档尾项
- Output:
  - `openai` 显式依赖补齐
  - README 与关键 workflow 状态统一
- Files / Modules Touched:
  - `services/livekit_agent/pyproject.toml`
  - `services/livekit_agent/uv.lock`
  - `services/livekit_agent/README.md`
  - 必要的 `.agentdocs/workflow/*.md`
  - `.agentdocs/archive/260312-realtime-livekit-closeout/*`
- Write Boundary:
  - 仅限 realtime 相关文件
- Truth Anchors To Recheck:
  - `services/livekit_agent/adapters/dashscope_asr.py`
  - `services/livekit_agent/README.md`
  - `.agentdocs/workflow/2602131555-livekit-agent-false-interruption-resume-task.md`
- Verify:
  - ruff + targeted pytest
- Evidence Bundle:
  - `.agentdocs/archive/260312-realtime-livekit-closeout/evidence/P2-*.json`
- Checkpoint Policy:
  - 进入 P3 前，文档不应再把已完成项描述成未完成
- Risks / Notes:
  - `uv.lock` 可能需要谨慎更新

### P3 — E4 acceptance + minimum regression

- Goal:
  - 把 E4 从“口头共识”变成 closeout 可执行清单
- Output:
  - 手动验收 checklist
  - 自动化回归范围
  - 必要时补测
- Files / Modules Touched:
  - `.agentdocs/archive/260312-realtime-livekit-closeout/*`
  - 必要时 `tests/services/livekit_agent/**`
- Write Boundary:
  - 只补 closeout 所需测试/文档
- Truth Anchors To Recheck:
  - `.agentdocs/workflow/2602121821-livekit-agent-e3-hardening-tracing-task.md`
  - `.agentdocs/workflow/2602131414-realtime-e3-enhancements-voice-mode-e4-task.md`
  - `docker-compose.yml`
- Verify:
  - checklist 完整；新增/更新测试通过
- Evidence Bundle:
  - `.agentdocs/archive/260312-realtime-livekit-closeout/evidence/P3-*.json`
- Checkpoint Policy:
  - CLOSE_REVIEW 前必须给出“能怎么验、验什么算通过”的明确答案
- Risks / Notes:
  - 实机/Jaeger 运行 evidence 受环境影响，必要时降级为明确 UAT 义务

---

## 13) 风险、迁移与回滚

### 13.1 Top Risks

1. `openai` 依赖声明与锁文件对齐不当，导致服务依赖说明与实际安装状态脱节
2. 为了清理 workflow 状态而过度修改 legacy 文档链
3. `E4` 验收清单写得过宽或过窄，不能支撑 closeout 结论

### 13.2 Migration / Rollback

- Code Rollback:
  - 依赖声明、README、测试、workflow 变更都应保持小步提交点，可按文件回滚
- Dependency Rollback:
  - 若 `openai` 显式声明或锁文件更新引入异常，回滚 `services/livekit_agent/pyproject.toml` 与 `services/livekit_agent/uv.lock`
- Data / Config Rollback:
  - 本轮不引入数据迁移；配置只允许声明/文档调整
- Rollback Verification:
  - `ruff` + targeted pytest 重新通过

---

## 14) UAT（非阻塞）

- Persona / Operator:
  - backend / realtime owner
- Preconditions:
  - `docker compose` 能启动 FastAPI、runtime、livekit、livekit-agent、otel-collector、jaeger
  - 可使用自研 App 或 Agents Playground 接入房间
- Steps:
  1. 加房并确认 join 成功
  2. 发送语音，确认 user transcript / assistant delta 在 `lk.transcription` 可见
  3. 播报中途打断，确认“尽快静音 + 不续播历史”
  4. 断连/重连，确认不会续播历史 backlog
  5. 在 Jaeger 查看关键 spans 与 `astraflow.*` 字段
- Expected Result:
  - 主链路可跑、interrupt 体验受控、TextStream 可见、Jaeger 可诊断
- What To Screenshot / Observe:
  - Playground/App 文本流
  - Jaeger operation / attributes
  - 关键日志中的 `(user_id, session_id, request_id, trace_id)`

---

## 15) Governance Check

- Needs User Decision:
  - NO
- Already Decided:
  - closeout 范围冻结为 `E4 / explicit dependency / doc-state cleanup`
  - 不混入 `WS TTS` 与进一步优化
- Open Questions (<= 3):
  - <none>
