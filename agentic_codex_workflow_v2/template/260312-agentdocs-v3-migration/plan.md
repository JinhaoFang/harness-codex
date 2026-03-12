---
task_id: 260312-agentdocs-v3-migration
slug: agentdocs-v3-migration
title: Agentdocs V3 运行模型迁移
workflow: .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md
issue: N/A
status: ARCHIVED
updated_at: 2026-03-12 11:37 +0800
---

# Plan：Agentdocs V3 运行模型迁移

## 0) 元信息
- Task ID: 260312-agentdocs-v3-migration
- Workflow: .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md
- Issue: N/A
- Status: ARCHIVED
- Updated At: 2026-03-12 11:37 +0800

---

## 1) Understanding Proof
- Goal Restatement: 把当前 `.agentdocs/` 从“V2 过渡态 + 失效入口”迁到可运行的 V3 热路径：恢复合法 active task 入口，重写 `index.md` 的导航结构，并把旧 index 中仍有价值的长期信息迁移到合适的位置，而不是直接删除。
- Explicit Non-Goals:
  - 不修改业务代码与运行时代码行为。
  - 不全量回填历史 archive task 的 V3 JSON review/evidence/archive-manifest。
  - 不重写全部 legacy workflow 正文。
  - 不在本轮处理“完成任务镜像到 GitHub issue”的仓库外流程。
- Why This Task Exists Now: `AGENTS.md`、`docs/dev/contracts/*`、`taskctl.py` 和模板已经切到 V3，但当前 `.agentdocs/index.md` 仍指向一个已删除的 task，`.agentdocs/tasks/` 为空，热路径已不再满足 V3 的新会话恢复合同。
- 95% Understanding Check: YES
- Missing Pieces:
  - `archive-manifest` 的精确 schema 目前未冻结，但用户已确认历史 archive 的形式合法性可忽略，因此不阻塞本轮范围。

---

## 2) What I Need / My Requirements / You Decide
### 2.1 What I Need
- User Outcome: 新会话进入 `.agentdocs/` 时，能找到真实 active task、正确的长期文档入口和清晰的 legacy/archive 兼容边界。
- Deliverable: 一个新的 V3 task bundle、更新后的 `.agentdocs/index.md`、补充后的 `.agentdocs/insights.md`、`.agentdocs/archive/index.md`，以及描述兼容策略的 task-scoped 文档。
- Acceptance Signal: `index.md` 不再指向缺失 task；重要信息有明确迁移去向；新 task pack 能通过当前 `taskctl validate-pack`。

### 2.2 My Requirements
- Hard Constraints:
  - `index.md` 的既有有效信息不能直接丢弃，必须分析后迁移到 index / insights / architecture / legacy reference 中的一个明确目的地。
  - 历史 archive task 的“形式不合法”不作为本轮阻塞。
  - 新任务与热路径从现在开始要遵守 V3。
- Preferred Constraints:
  - 结构性写回优先使用 `taskctl.py`。
  - 尽量不改动已归档任务正文，只修热路径与长期文档。
  - 对旧路径继续采用低破坏兼容方式。
- Non-Negotiables:
  - `.agentdocs/index.md` 只能指向真实存在的 active task。
  - `.agentdocs/insights.md` 只承接跨任务可复用的长期经验与稳定口径。
  - 不能制造新的双 SoT。

### 2.3 You Decide
- Agent Decision Space:
  - V3 index 的信息架构与导航顺序。
  - “历史 archive 只读兼容，新任务严格 V3”的具体写法。
- Decisions Requiring User Confirmation:
  - 当前无新增用户决策阻塞；若发现某段“全局重要记忆”必须提升为新的长期 architecture SoT，再单独升级。
- Escalation Triggers:
  - 若某段旧 index 内容必须改写现有 `architecture/*.md` 的事实口径。
  - 若热路径迁移会打断当前 repo 内已有引用。

---

## 3) 当前事实锚点（Current Truth Anchors）
### 3.1 Code Paths
- Path 1: `.agentdocs/index.md`
- Path 2: `.agentdocs/insights.md`
- Path 3: `.agentdocs/archive/260308-agentdocs-v2-migration/workflow.md`
- Path 4: `.agentdocs/archive/260308-backend-architecture-reorg/workflow.md`
- Path 5: `.codex/workflow/taskctl.py`
- Path 6: `.codex/workflow/templates/index.template.md`
- Path 7: `docs/dev/contracts/session-minimum-align.md`
- Path 8: `docs/dev/contracts/task-pack-layout.md`
- Path 9: `docs/dev/contracts/task-archive-lifecycle.md`
- Path 10: `docs/dev/contracts/structured-writeback.md`

### 3.2 Key Symbols / Entry Points
- Symbol 1: `taskctl.py::cmd_create_task`
- Symbol 2: `taskctl.py::cmd_make_pack`
- Symbol 3: `taskctl.py::cmd_validate_pack`
- Symbol 4: `taskctl.py::cmd_sync_index`
- Symbol 5: `taskctl.py::CURRENT_TASKS_SECTION_MARKER`

### 3.3 Tests / Checks
- Existing Tests:
  - `test -f .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md`
  - `rg -n "DEFAULT:|## 2\\) 当前任务（SSOT\\)|260309-taskctl-controller-hardening" .agentdocs/index.md`
  - `python .codex/workflow/taskctl.py validate-pack --pack .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/BUILD-task-pack.md`
  - `find .agentdocs/archive -maxdepth 2 -type f | sort`
- Missing Tests:
  - 当前没有针对 `.agentdocs/index.md` 热路径合法性的自动检查。
  - 当前没有针对历史 archive 与新 V3 task 并存策略的 lint / verify 入口。

### 3.4 Config / Env / Runtime
- Config Anchors:
  - `AGENTS.md`
  - `docs/dev/contracts/high-entropy-state-machine.md`
  - `docs/dev/contracts/current-truth-anchors.md`
  - `docs/dev/contracts/deterministic-controller.md`
- Runtime Evidence:
  - 当前 `.agentdocs/archive/260312-agentdocs-v3-migration/` 已存在，并承担唯一 active V3 task。
  - 当前 `.agentdocs/index.md` 已指向真实 active task，且不再引用已删除的 `260309-taskctl-controller-hardening`。
  - 当前 `.agentdocs/archive/index.md` 已存在，并列出 2 个历史 archive task bundle。
  - 历史 `BUILD` task pack 无法通过当前 `validate-pack`。
- Notes:
  - 本任务以“文档/控制面文件 + controller 行为”为当前事实锚点，不以旧 workflow 叙述代替当前状态。

---

## 4) 背景与目标
- Problem: 当前 `.agentdocs/` 处于 V2 迁移后遗留状态：`index.md` 仍保留 V2 当前任务入口且指向缺失 task，热路径没有真实 active task；同时旧 index 中堆积了导航、长期记忆、legacy reference 等多类信息，已经不适合作为 V3 新会话入口。
- Goal: 在不丢失旧 index 有效信息的前提下，建立一个可运行的 V3 `.agentdocs` 热路径，把“导航”“长期记忆”“legacy reference”“archive reference”重新分层，并用新的 task bundle 承接本轮迁移。
- In Scope:
  - 新建并启用一个真实的 V3 active task bundle。
  - 重构 `.agentdocs/index.md` 为 V3 入口，同时迁移旧 index 中的长期有效内容。
  - 补 `.agentdocs/archive/index.md`。
  - 扩展 `.agentdocs/insights.md`，承接旧 index 中适合长期沉淀的“全局重要记忆”。
  - 冻结 legacy archive 与新 V3 task 的兼容策略。
- Out of Scope:
  - 不全量回填历史 archive 的 JSON review/evidence/runtime-events/archive-manifest。
  - 不批量重写所有 `architecture/*.md`。
  - 不处理 GitHub issue 镜像流程。
  - 不修改业务代码。
- Success Criteria:
  - `.agentdocs/index.md` 恢复为有效热路径入口，并指向真实 active task。
  - `.agentdocs/archive/index.md` 存在并能导航已归档任务。
  - 旧 index 中的长期有效内容有明确迁移落点，且无信息无故丢失。
  - 本任务生成的 V3 task pack 可通过当前 `validate-pack`。

---

## 5) Memory Lookup 与 Context Coverage
### 5.1 Memory Lookup
- architecture Inputs:
  - `AGENTS.md`
  - `.agentdocs/index.md`
  - `.agentdocs/insights.md`
  - `.agentdocs/archive/260308-agentdocs-v2-migration/workflow.md`
  - `.agentdocs/archive/260308-backend-architecture-reorg/workflow.md`
  - `.codex/workflow/taskctl.py`
  - `.codex/workflow/templates/index.template.md`
  - `docs/dev/contracts/session-minimum-align.md`
  - `docs/dev/contracts/task-pack-layout.md`
  - `docs/dev/contracts/task-archive-lifecycle.md`
  - `docs/dev/contracts/structured-writeback.md`
- insights Inputs:
  - `.agentdocs/insights.md`
- Reused Rules:
  - 新任务必须有真实 task-scoped 目录。
  - `PLAN_REVIEW / BUILD / CLOSE_REVIEW` 必须绑定当前 phase task pack。
  - 结构性热路径更新优先走 controller 或与其兼容的模板结构。
- Re-validation Needed:
  - BUILD 前按新矩阵逐项确认旧 index 信息去向是否仍然成立。

### 5.2 Context Coverage Contract
- Must Read:
  - `AGENTS.md`
  - `.agentdocs/index.md`
  - `.agentdocs/insights.md`
  - `.codex/workflow/taskctl.py`
  - `.codex/workflow/templates/index.template.md`
  - `docs/dev/contracts/session-minimum-align.md`
  - `docs/dev/contracts/high-entropy-state-machine.md`
  - `docs/dev/contracts/task-pack-layout.md`
  - `docs/dev/contracts/task-archive-lifecycle.md`
  - `docs/dev/contracts/structured-writeback.md`
  - `docs/dev/contracts/current-truth-anchors.md`
- Adjacent Scan:
  - `.agentdocs/archive/260308-agentdocs-v2-migration/**`
  - `.agentdocs/archive/260308-backend-architecture-reorg/**`
  - `.agentdocs/architecture/*.md`
  - `.agentdocs/workflow/*.md`
- Unread But Potentially Relevant:
  - `docs/dev/system/module-boundaries.md`
- Coverage Decision: SUFFICIENT
- Coverage Notes:
  - 已确认当前热路径失效事实、V3 controller 期望、旧 index 的主要内容结构和用户认可的兼容边界；destination matrix 与 hard routing rule 已冻结，当前足够支撑 BUILD 收尾与后续 `CLOSE_REVIEW`。

### 5.3 Scratch Promotion Rule
- Scratch Dir: .agentdocs/archive/260312-agentdocs-v3-migration/scratch/
- Allowed Scratch Content:
  - 旧 index 段落去向映射草案
  - “全局重要记忆”分流草案
  - index / insights 重构提纲
- Promotion Required Before Build:
  - 任何会影响信息去向、兼容边界、入口结构的决定都必须写回 `plan.md` / `workflow.md`，不能只留在 scratch。
- Scratch Close Condition:
  - `index.md`、`insights.md`、`archive/index.md` 的目标结构已冻结，review 不再依赖 scratch 才能理解改动。

---

## 6) 已拍板事项（Decision Freeze）
### 6.1 技术 / 依赖 / 基础设施
- Selected:
  - 新建 V3 task-scoped 任务作为当前唯一 active task。
  - 历史 archive 维持 Markdown-only 只读兼容，不回填全部结构化工件。
  - 旧 `index.md` 的长期有效信息按语义迁移，而不是整段原样保留在热路径。
- Version / Constraint:
  - 以当前 `AGENTS.md`、`docs/dev/contracts/*`、`taskctl.py` 为 V3 真源。
  - 不引入新依赖。
- Rejected Alternatives + Why:
  - 直接把旧 index 覆盖成新模板：会丢失长期记忆与历史导航信息。
  - 回填所有历史 archive 到 V3 strict：用户已明确不是本轮目标，投入产出比过低。
  - 继续保留失效的 V2 当前任务入口：会让新会话恢复继续断裂。
- Rollback Switch (if any):
  - 若新的 index 信息架构被证明不稳定，可回退为“V3 热路径 + 旧内容暂存区”的保守版本，但不能回退到失效 task 链接。

### 6.2 数据 / 协议 / 公共口径
- Frozen Contracts:
  - `.agentdocs/index.md` 只承载热路径导航、当前任务入口、治理入口和必要的长期入口，不再承载大段“全局重要记忆”正文。
  - 旧 index 中适合长期复用的经验优先进入 `.agentdocs/insights.md`；若某条更属于专题架构事实，则在 index / insights 中指向 `architecture/*.md`，不重复复制。
  - 历史 archive task 允许维持 V2/Markdown 兼容形态，不作为本轮阻塞。
  - 新 task 从本轮开始使用 V3 workflow / plan / task pack 合同。

### 6.3 旧 Index 顶层区块 Destination Matrix
| Old Section | Destination | Action |
|---|---|---|
| `V2 当前任务入口` | `index.md` `## 2) 当前任务（SSOT）` | 用真实 V3 active task 替换失效 V2 指针 |
| `V2 / Legacy 兼容规则` | `index.md` compatibility note + legacy appendix note | 压缩为热路径兼容说明，并保留 legacy/workflow-done 的可读边界 |
| `产品文档` | `index.md` quick/context pointer | 继续作为顶层导航入口 |
| `长期知识` | `index.md` 长期入口 | 保留到 `insights.md` / `architecture/` 的导航 |
| `架构文档` | `index.md` architecture pointers | 保留为 canonical 导航，不迁出 index |
| `兼容层说明` | `index.md` compatibility note | 压缩保留 |
| `Legacy workflow 参考文档` | `index.md` legacy appendix | 继续保留列表作为 reference appendix |
| `Realtime / Chat / Voice 已归档任务（workflow/done）` | `index.md` legacy `workflow/done` appendix | 继续保留列表，明确它们不属于新 `archive/` 模型 |
| `Skills` | `index.md` legacy/deprecated note | 不再作为热路径顶层 section，但保留历史注记，避免无目的丢失 |
| `全局重要记忆` | split: `insights.md` / existing `architecture/*` reference / `index.md` operation notes | 按下面的分流矩阵执行 |

### 6.4 全局重要记忆 Routing Matrix
| Old Lines | Theme | Destination | Rule |
|---|---:|---|---|
| 85 | 产品/范围记忆 | `insights.md` | 进入产品/边界类长期记忆 |
| 86-90 | Electric / media / rate limit 稳定架构事实 | existing `architecture/*` reference | 只指向现有 `backend_data_and_sync.md`、`media_storage_and_files.md`、`backend_system_overview.md`，不复制正文 |
| 91-103 | Chat / Responses / SessionHistory / attachments 行为口径 | `insights.md` temporary source-linked entries | 当前没有单一现成 architecture home 的细粒度条目，先进入 `insights.md` 临时分组 |
| 104-120 | Realtime / LiveKit / internal responses 协作规则 | split: existing `architecture/*` reference + `insights.md` temporary entries | 边界事实指向现有 architecture；协议坑点进入 source-linked insights |
| 121-172 | runtime/tools/config/tracing/ops 决策与坑点 | split: existing `architecture/*` reference + `insights.md` temporary entries | 边界/配置/观测不变量指向现有 architecture；细粒度兼容坑点进入 source-linked insights |
| 173 | “涉及相关领域先读 skills” 操作提示 | `index.md` context map note | 继续作为热路径操作提示 |
| 174 | `pre-push-check` 操作提示 | `index.md` verification/governance note | 继续作为热路径验证提醒 |

### 6.5 Hard Routing Rule（insights vs architecture）
- 本任务不创建也不改写任何 `architecture/*.md` canonical 正文。
- 若旧 index 条目有明确现成 architecture SoT，则只在 `index.md` 或 `insights.md` 中指向该文档，不复制正文。
- 若旧 index 条目没有明确现成 architecture home，则先进入 `insights.md` 的 source-linked temporary 分组，并在后续任务中再决定是否升级为专题 SoT。
- 详细映射工作底稿保留在 `.agentdocs/archive/260312-agentdocs-v3-migration/scratch/index-destination-matrix.md`，但 BUILD 只能执行已在本 plan 冻结的矩阵与规则。

---

## 7) 契约与边界
### 7.1 Invariants
- Invariant 1: 旧 index 中的有效信息不能被无目的地删除；每一类信息都必须有明确去向。
- Invariant 2: `.agentdocs/index.md` 只能指向真实存在的 active task。
- Invariant 3: 不能为了 V3 热路径收口而破坏 legacy workflow / archive 的只读可访问性。

### 7.2 Interfaces / Data / Errors / Compatibility
- Inputs:
  - 旧 `.agentdocs/index.md`
  - `.agentdocs/insights.md`
  - `.agentdocs/architecture/*.md`
  - `.agentdocs/archive/*`
  - V3 contracts / controller / templates
- Outputs:
  - 更新后的 `.agentdocs/index.md`
  - 更新后的 `.agentdocs/insights.md`
  - 新增 `.agentdocs/archive/index.md`
  - 当前任务的 workflow / plan / task pack / review / evidence 工件
- Public API / Schema Changes:
  - 无业务 API 变化；仅 `.agentdocs` 热路径入口和文档导航变化。
- Error Strategy:
  - 若某条旧 index 记忆无法在本轮可靠归类，则先迁入 `insights.md` 的临时分类段并保留来源说明，而不是直接丢弃。
- Compatibility Strategy:
  - `.agentdocs/workflow/*.md` 继续作为 legacy reference layer 保留。
  - 已归档 V2 task bundle 不做全量结构化回填。
  - 当前新 task 作为唯一 active V3 task，承担热路径合法恢复。
  - `BUILD` 允许新增 `archive/index.md`，但不允许把历史 `workflow/done` 旧归档冒充为新 archive bundle。

### 7.3 Edge Cases
- Boundary Case 1: “全局重要记忆”里的条目有三类语义混杂：产品边界、架构事实、工程坑点；不能一刀切全部塞进 `insights.md` 而不分层。
- Boundary Case 2: 某些 legacy workflow 文档在旧 index 中仍被标注为“进行中”，但在 V3 里只能作为 reference，不能继续伪装成当前 task。
- Boundary Case 3: `Skills` 顶层 section 不再属于热路径核心导航，但为避免无目的删除，本轮保留为 deprecated note，而不是直接从 repo 入口层消失。
- Timeout / Retry / Idempotency / Concurrency:
  - 文档任务，串行执行；不并行写同一热路径文件。

---

## 8) Must-Haves
### 8.1 Truths
- Truth 1: 当前 `.agentdocs/index.md` 指向一个缺失 task，热路径已失效。
- Truth 2: 当前 `.agentdocs/tasks/` 在本任务创建前为空，没有真实 active task。
- Truth 3: 历史 archive task pack 不能通过当前 V3 `validate-pack`，说明旧 bundle 不是当前运行合同。
- Truth 4: reviewer `r1` 已明确要求在 BUILD 前冻结闭合 destination matrix 与 hard routing rule。

### 8.2 Artifacts
- Artifact 1: `.agentdocs/index.md`
- Artifact 2: `.agentdocs/insights.md`
- Artifact 3: `.agentdocs/archive/260312-agentdocs-v3-migration/workflow.md`
- Artifact 4: `.agentdocs/archive/260312-agentdocs-v3-migration/plan.md`
- Artifact 5: `.codex/workflow/taskctl.py`
- Artifact 6: `docs/dev/contracts/task-pack-layout.md`
- Artifact 7: `.agentdocs/archive/260312-agentdocs-v3-migration/scratch/index-destination-matrix.md`

### 8.3 Key Links
- Link 1: `AGENTS.md`
- Link 2: `.agentdocs/archive/260308-agentdocs-v2-migration/workflow.md`
- Link 3: `.agentdocs/archive/260308-backend-architecture-reorg/workflow.md`
- Link 4: `docs/dev/contracts/session-minimum-align.md`
- Link 5: `docs/dev/contracts/structured-writeback.md`
- Link 6: `.agentdocs/archive/260312-agentdocs-v3-migration/reviews/plan-review-r1.json`

---

## 9) Verification Ladder
- Static:
  - 检查 `index.md` 是否恢复 V3 当前任务入口与长期导航结构。
  - 检查 `archive/index.md` 是否存在并列出 archive task。
  - 检查旧 index 的长期有效内容是否已有明确落点。
- Command:
  - `test -f .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md`
  - `rg -n "## 2\\) 当前任务（SSOT\\)|DEFAULT:|ACTIVE:" .agentdocs/index.md`
  - `python .codex/workflow/taskctl.py validate-pack --pack .agentdocs/archive/260312-agentdocs-v3-migration/task-packs/BUILD-task-pack.md`
  - `find .agentdocs/archive -maxdepth 2 -type f | sort`
  - `git diff -- .agentdocs`
- Behavioral:
  - 新会话从 `index.md` 可以找到真实 active task、长期 insights、长期 architecture 和 archive index。
  - 打开旧 index 原有内容后，读者仍能找到对应的新落点。
- Human:
  - 抽样检查至少 3 条旧 index 信息，确认分别被迁移到 index / insights / legacy reference 的正确位置。
- Mapping:
  - 抽样检查顶层区块矩阵与“全局重要记忆”分流矩阵是否闭合。
- Minimum Required For PASS:
  - 当前 task 成为唯一合法 active 入口。
  - `archive/index.md` 建立完成。
  - 至少一批“全局重要记忆”已迁入 `insights.md` 并带有清晰分组。
  - reviewer 认可 destination matrix 与 hard routing rule 足以支撑 BUILD。

---

## 10) Reviewer Recheck Plan
- Plan Reviewer Recheck:
  - 重点检查旧 index 顶层区块矩阵与“全局重要记忆”分流矩阵是否闭合，compat strategy 是否收窄、是否避免了“删旧内容但没落点”的风险。
- Close Reviewer Recheck:
  - 抽样检查 `index.md`、`insights.md`、`archive/index.md` 和本任务 task pack。
- Escalation To FULL_REVIEW If:
  - 迁移过程中发现必须调整现有 `architecture/*.md` 的 canonical 口径。
  - 迁移范围扩展到历史 archive 的结构化回填。

---

## 11) Issue Breakdown（issue 是 plan 的子结构）
### Issue 1 — 恢复 V3 热路径入口
- Goal: 建立真实 active task、修复 `index.md` 的当前任务入口并补 `archive/index.md`。
- Depends On: 当前任务 align / plan 冻结。
- Write Boundary:
  - `.agentdocs/index.md`
  - `.agentdocs/archive/index.md`
  - `.agentdocs/archive/260312-agentdocs-v3-migration/**`
- Verify:
  - 当前 task 可从 index 导航进入。
  - archive index 可导航历史任务。
- Rollback Note: 如信息架构争议过大，可先保守保留旧内容区，但不能恢复缺失 task 链接。

### Issue 2 — 迁移旧 index 的长期信息
- Goal: 把旧 index 的“全局重要记忆”等长期信息迁到 `insights.md` 或明确指向 `architecture/*.md`。
- Depends On: Issue 1 完成且 compat strategy 冻结。
- Write Boundary:
  - `.agentdocs/index.md`
  - `.agentdocs/insights.md`
  - `.agentdocs/archive/260312-agentdocs-v3-migration/**`
- Verify:
  - 抽样旧条目可找到新落点。
  - index 不再内嵌大段长期记忆正文。
- Rollback Note: 如个别条目暂时无法归类，可先放入 `insights.md` 临时分组并保留来源。

### Issue 3 — 冻结 index destination matrix 与 routing rule
- Goal: 让 BUILD 只执行已闭合的信息去向矩阵，不再在实现时临时决定旧 index 条目的落点。
- Depends On: reviewer `r1` findings
- Write Boundary:
  - `.agentdocs/archive/260312-agentdocs-v3-migration/plan.md`
  - `.agentdocs/archive/260312-agentdocs-v3-migration/workflow.md`
  - `.agentdocs/archive/260312-agentdocs-v3-migration/task-packs/**`
  - `.agentdocs/archive/260312-agentdocs-v3-migration/scratch/index-destination-matrix.md`
- Verify:
  - reviewer 能逐项复核顶层区块矩阵与全局记忆分流矩阵
  - 规则明确禁止本轮 architecture canonical rewrites
- Rollback Note: 如个别条目暂时无法归类，可先放入 `insights.md` 临时分组并保留来源。

---

## 12) 分阶段规格（<= 7 phases）
说明：
- `workflow.md` 的 Phase Board 只跟踪执行 phase
- `PLAN_REVIEW / CLOSE_REVIEW` 的结论写在 workflow review sections，不把 `reviews/*.json` 当作 phase evidence

### P1 — 对齐当前失效状态与迁移边界
- Goal: 证明当前 `.agentdocs` 热路径为什么失效，以及本轮为何不是“全量 archive 修复”任务。
- Output:
  - 当前任务 workflow / plan 对齐完成
  - 旧 index 内容分类与迁移边界冻结
  - reviewer `r1` findings 回写
- Files / Modules Touched:
  - `.agentdocs/archive/260312-agentdocs-v3-migration/**`
- Write Boundary:
  - `.agentdocs/archive/260312-agentdocs-v3-migration/**`
- Truth Anchors To Recheck:
  - `.agentdocs/index.md`
  - `.codex/workflow/taskctl.py`
  - `docs/dev/contracts/*`
- Verify:
  - 新 task 成功创建
  - 当前理解与用户确认一致
  - destination matrix 与 hard routing rule 已进入 plan
- Evidence Bundle:
  - `.agentdocs/archive/260312-agentdocs-v3-migration/reviews/plan-review-r3.json`
- Checkpoint Policy:
  - `PLAN_REVIEW` 前必须冻结 compat strategy
- Risks / Notes:
  - 如果边界未收口，后续 index 改动很容易再次混淆“导航”和“记忆”

### P2 — 重构热路径入口
- Goal: 把 `index.md` 改造成 V3 热路径入口，并补 `archive/index.md`。
- Output:
  - 新版 `index.md`
  - `archive/index.md`
- Files / Modules Touched:
  - `.agentdocs/index.md`
  - `.agentdocs/archive/index.md`
- Write Boundary:
  - `.agentdocs/index.md`
  - `.agentdocs/archive/index.md`
- Truth Anchors To Recheck:
  - 当前 task 文件实际存在
  - archive 目录实际内容
- Verify:
  - 当前 task 从 index 可达
  - stale task 引用消失
- Evidence Bundle:
  - E02
- Checkpoint Policy:
  - 若旧内容还没迁移完，先保留迁移说明，不直接删除
- Risks / Notes:
  - index 过度精简会丢失旧信息

### P3 — 迁移长期记忆并收口兼容说明
- Goal: 把旧 index 的长期有效记忆迁到 `insights.md` 并明确 legacy/archive 兼容层。
- Output:
  - 更新后的 `insights.md`
  - 收口后的 index 兼容说明
- Files / Modules Touched:
  - `.agentdocs/insights.md`
  - `.agentdocs/index.md`
- Write Boundary:
  - `.agentdocs/insights.md`
  - `.agentdocs/index.md`
- Truth Anchors To Recheck:
  - 旧 index 中“全局重要记忆”原文
  - 现有 `architecture/*.md`
- Verify:
  - 抽样条目迁移成功
  - 无新的双 SoT
- Evidence Bundle:
  - E03
- Checkpoint Policy:
  - close review 前必须有人类可读迁移对照
- Risks / Notes:
  - 需要避免把架构专题事实错误抽象成 insights

### P4 — 复核并进入 BUILD
- Goal: 修复 review findings 后重新生成 PLAN_REVIEW task pack，争取进入 BUILD。
- Output:
  - refreshed `PLAN_REVIEW` task pack
  - `plan-review-r3.json`
  - `BUILD-task-pack.md`
- Files / Modules Touched:
  - `.agentdocs/archive/260312-agentdocs-v3-migration/**`
- Write Boundary:
  - `.agentdocs/archive/260312-agentdocs-v3-migration/**`
- Truth Anchors To Recheck:
  - `.agentdocs/index.md`
  - `.agentdocs/insights.md`
  - `.agentdocs/archive/260312-agentdocs-v3-migration/task-packs/PLAN_REVIEW-task-pack.md`
- Verify:
  - `PLAN_REVIEW` findings 被关闭
  - phase truth 在 workflow / plan / pack 之间对齐
  - round-3 `PASS` 已记录并放行 `BUILD`
- Evidence Bundle:
  - `.agentdocs/archive/260312-agentdocs-v3-migration/reviews/plan-review-r3.json`
- Checkpoint Policy:
  - reviewer 未 PASS 前不进入 BUILD
- Risks / Notes:
  - 若 reviewer 仍认为矩阵不闭合，则继续留在 `PLAN_DRAFT`

---

## 13) 风险、迁移与回滚
### 13.1 Top Risks
1. 旧 index 的信息被过度压缩，迁移后找不到原有长期记忆。
2. 为了修热路径，误把历史 archive 也纳入 V3 严格改造，导致范围失控。
3. 某些“全局重要记忆”本质上属于 architecture SoT，若直接复制到 insights 会制造重复事实源。

### 13.2 Migration / Rollback
- Code Rollback: 文档任务，无业务代码回滚。
- Dependency Rollback: 无依赖变更。
- Data / Config Rollback: 若新的 index 结构不可接受，可回滚 `.agentdocs/index.md` / `.agentdocs/insights.md` / `.agentdocs/archive/index.md` 到修改前版本，同时保留当前 task bundle 作为分析记录。
- Rollback Verification:
  - `git diff -- .agentdocs`
  - `test -f .agentdocs/archive/260312-agentdocs-v3-migration/workflow.md`

---

## 14) UAT（非阻塞）
- Persona / Operator: 新会话 coding agent / 仓库维护者
- Preconditions:
  - `.agentdocs/archive/260312-agentdocs-v3-migration/` 已存在
  - `index.md` / `insights.md` / `archive/index.md` 已更新
- Steps:
  1. 从 `.agentdocs/index.md` 开始读取
  2. 定位默认 active task
  3. 跳转到 `insights.md` 与 `archive/index.md`
  4. 抽样对照一条旧 index 的长期记忆
- Expected Result:
  - 当前 task、长期 insights、archive index 均可达
  - 旧长期记忆有清晰新落点
- What To Screenshot / Observe:
  - index 顶部入口
  - 当前任务 SSOT 段
  - insights 新增分组

---

## 15) Governance Check
- Needs User Decision:
  - 当前无新增待决项
- Already Decided:
  - 旧 index 内容不能直接删除，必须分析迁移
  - 历史 archive 的形式合法性可忽略
  - 冻结 compat strategy，并执行内容迁移
- Open Questions (<= 3):
  - 当前无阻塞性 open question；reviewer `r1` 的两个问题已按 destination matrix 与 hard routing rule 收口
