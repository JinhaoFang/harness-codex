# V2 → V3 落地策略（不照搬 V2）

状态：DRAFT（仅策略，不改实现）  
日期：2026-03-15  
范围：把 `agentic_codex_workflow_v2/` 的“可运行流程实现”升级/迁移到 `agentic-engineering-spec-v3/` 的“薄规范 + 最小控制面”。

> 本文目标：在不破坏 V2 可用性的前提下，把 V3 的**权力分配**（truth / gate / controller / pack / brief）落成可运行系统；并明确哪些 V2 设计应被降级/停止新写入，而不是复刻。

---

## 0. 结论先行（迁移的核心不是改名）

V3 相对 V2 的根本变化是三件事：

1. **从“长状态链 SSOT”迁移为“Gate 闭环”**：不要求固定的 `DISCUSS -> ... -> ARCHIVE` 状态链，但要求 Gate A/B/C/D 的闭环与独立审查成立。  
   参见：`spec/03-runtime-and-review.md`、`spec/05-migration-from-legacy.md`
2. **对象最小化 + 去厚持久化**：`plan.md` 纯 Goal truth；`workflow.md` 纯 Process truth；`subtask-pack` 为派生 digest；`delegation-brief` 为 session wrapper（默认不持久化）。  
   参见：`spec/01-truth-model.md`、`spec/06-object-minimization.md`、`templates/*`
3. **重新分配权力**：deterministic control plane（controller）负责 gate/引用/结构化写回与再生；reviewer 负责裁决但不实现；skills 仅作为方法注入层。  
   参见：`controller/README.md`、`controller/COMMANDS.md`

因此：V3 落地不是把 V2 的 controller/skills/template 原样搬到新目录，而是要把 V2 的“运行性能力”**重构成**符合 V3 权力分配与对象边界的实现。

Gate 口径（V3）：
- Gate A：Understand
- Gate B：Ground in World
- Gate C：Freeze Goal truth
- Gate D：Independent Review

---

## 1. 约束与不变量（必须守住）

### 1.1 不变量（从 V2 继承，但以 V3 术语表述）

- **World truth 永远以 code/tests/runtime 为准**；文档只能约束动作，不得覆盖世界真实情况。  
  对齐：`spec/01-truth-model.md`
- **先 Ground in World，再 Freeze Goal truth**；冻结通过独立 review 前不得进入实现；实现完成后必须独立 close review。  
  对齐：`spec/03-runtime-and-review.md`
- **review 与 evidence 分离**：review 记录 judgment；evidence 记录过程事实；互不混写。  
  对齐：`controller/COMMANDS.md`
- **deterministic 能稳定做对的动作必须下沉到 controller**（引用校验、结构化写回、pack 再生等）。  
  对齐：`templates/AGENTS.md`、`controller/README.md`

### 1.2 本轮迁移的硬边界（Non-goals）

为避免把迁移变成“系统重写”，本策略明确不做：

- 不要求把历史 archive 的旧 workflow / pack / ledger 全量改写为 V3 模板或 V3 JSON schema。
- 不要求在迁移期强制所有项目立刻切换为复杂的多 subtask 拆分；允许默认单 subtask（更易迁移，仍符合 V3）。
- 不把 `delegation-brief` 变成新的长期工件（只能临时生成/可丢弃）。
- 不把 pack/brief 当作真相层；任何“恢复方便”的厚摘要都不得回流成为后续规划依据（必须 fresh grounding）。
- **本轮不做 skills 的完全重构。** V3 skills 需要重切片，但该工作单独立项；当前仅保证 controller + 模板 + 最小运行闭环可用。

补充说明：
- “迁移不是重写”在执行上可以理解为：**不要求重写全部历史工件**；但允许重写/替换 V2 中不符合 V3 边界的实现方式。V2 中符合 V3 的好设计可以调整后纳入 V3。

---

## 2. 目标态（V3 可运行形态）定义

### 2.1 长期一等对象（必须存在且可审计）

- `plan.md`（Goal truth）
- `workflow.md`（Process truth）
- `reviews/*.json`（judgment）
- `evidence/*.json`（process evidence）
- code/tests（World truth）

对应：`spec/06-object-minimization.md`

### 2.2 派生视图与临时 wrapper（必须可再生/可丢弃）

- `subtask-pack.md`：派生 digest，服务当前 subtask；可再生。  
  对应：`templates/subtask-pack.md`
- `delegation-brief.md`：session wrapper；建议临时生成，不作为长期对象。  
  对应：`templates/delegation-brief.md`

### 2.3 最小 controller 命令面（必须落成 deterministic 实现）

V3 controller 的“最小命令面”必须可用（至少 CLI 级别），并具备引用与边界校验：

- `check-gate`
- `write-review`
- `write-evidence`
- `refresh-pack`
- `validate-refs`
- `archive`
- `reopen`

对应：`controller/COMMANDS.md`

---

## 3. V2 → V3 构件映射（Keep / Rewrite / Deprecate）

> 目的：定义“哪些保留为兼容读取、哪些停止新写入、哪些重写为 V3 目标态”，避免照搬。

### 3.1 关键映射表

| V2 构件 | V3 构件/定位 | 策略 | 说明 |
|---|---|---|---|
| 长状态链（`DISCUSS -> ... -> ARCHIVE`） | Gate A/B/C/D（闭环） | **Rewrite** | V3 仅保留门禁语义，不要求固化全部中间状态名（`spec/05-migration-from-legacy.md`）。 |
| `workflow.v2.template.md` 的 Build Log / Ledger / Memory / Issue 段落 | `templates/workflow.md`（薄 Process truth） | **Deprecate**（停止新写入） | 迁移期可读旧段落，但新写入必须收敛到 V3 workflow 的最小字段。 |
| `plan.v2.template.md`（厚 plan） | `templates/plan.md`（纯 Goal truth） | **Rewrite** | 把过程账本类内容（coverage、长清单）从 plan 移出或改为引用/派生。 |
| `task-pack`（phase-scoped digest） | `subtask-pack`（subtask digest） | **Rewrite** | pack 必须 subtask-scoped，且可再生；不成为新真相层。 |
| `delegation-brief.template.md`（可持久化） | delegation brief（临时） | **Deprecate**（默认不落盘） | 可生成用于一次委派，但不作为长期审计对象。 |
| V2 `taskctl.py`（实现型 controller） | V3 controller（最小命令面） | **Refactor** | 不是“换目录”，而是按 v3 命令面与对象边界拆分/收口。 |
| V2 router/specialist/tooling skills | V3 skills（方法注入层） | **Re-slice** | V3 skills 更薄：world-grounding / reuse-check / plan-review / close-review / subtask-pack-refresh；路由与编排应更多交给 main + controller，而不是写入厚 checklist。 |

### 3.2 “停止新写入”清单（迁移分界线）

在进入 V3 目标态后，必须停止新写入（只读兼容）：

- `workflow.md` 中的厚段落账本（build log、issue sync、memory routing catalog、handoff snapshot 等）
- 任何为了恢复方便而复制的摘要（尤其是会在下一轮被当作事实的 recap）
- 任何把 delegation brief 当作长期对象的落盘行为

对应：`spec/05-migration-from-legacy.md`、`spec/06-object-minimization.md`

---

## 4. 分阶段落地路线（每步可验收、可回滚）

### Phase 0 — 冻结迁移契约（不改实现）

产出：
- 本策略文档冻结版本（明确：对象边界、停止新写入清单、验收门禁）。

验收：
- 对照 `spec/*` 不冲突；团队能用同一口径解释“什么是长期对象、什么是派生物、什么必须 fresh context”。

回滚：
- 无需回滚（只新增文档）。

### Phase 1 — 引入 V3 模板作为“目标态 reference”（不替换 V2）

产出：
- 统一对外宣告：V3 的 `templates/*` 为新任务的推荐模板，但不强制迁移旧任务。

验收：
- 能清晰区分：旧任务继续按旧模板读取，新任务按 V3 模板产出长期对象。

回滚：
- 移除推荐/标记即可；不影响 V2 运行。

### Phase 2 — controller 先落“最小命令面”（不引入长状态链）

产出：
- 实现 `controller/COMMANDS.md` 的最小命令面（CLI/API 均可，但必须 deterministic）。
- `validate-refs` 必须先落地（先有一致性校验，后谈迁移写入）。
 - 提供脚本化 bootstrap：一键初始化 `.agentdocs/`；并支持“一键开始某个 task / subtask”的最小文件落位（类似 V2 的脚手架体验，但产物必须符合 V3 对象边界）。

验收：
- 能对 `plan/workflow/reviews/evidence/pack` 做引用完整性检查，并能稳定写入 review/evidence。

回滚：
- controller 新命令与旧 `taskctl.py` 并存；出现问题可以回退使用旧写回方式，但不允许引入新的厚持久化。

### Phase 3 — subtask 模型落地（pack 从 phase 改为 subtask）

产出：
- 引入 `subtask-pack-refresh` 的 deterministic 生成流程：从 `plan.md` + `workflow.md` + 必要 evidence/review 引用再生 pack。
- `workflow.md` 只记录：当前 active subtask、gate、pointers、recovery、minimal events（参照 `templates/workflow.md`）。

验收：
- 任意中断后都能通过 `plan/workflow + validate-refs + refresh-pack` 恢复进入当前 subtask。

回滚：
- 如果 subtask 切分不稳定，可把 subtask 粒度先设为“单一 subtask”（仍符合 V3）；但不得回滚到长状态链 SSOT。

### Phase 4 — skills 重切片（从“流程技能”迁移为“方法注入技能”）

产出：
- 形成 v3 样式 skills：`world-grounding / reuse-check / plan-review / close-review / subtask-pack-refresh` 的调用约定与输出契约。

验收：
- reviewer 能在 fresh context 下只依赖 plan + pointers + pack + code/evidence 做裁决，不需要继承 builder 的厚上下文。

回滚：
- skills 可回退到人工执行 checklist，但 controller 写回与对象边界不回退。

### Phase 5 — V2 旧写入点全面退役（只读兼容）

产出：
- 明确：旧 workflow 厚段落只读；新写入不得再产生。

验收：
- 新任务的长期对象稳定保持“薄”；pack/brief 可再生/可丢弃；review/evidence JSON 可机器处理。

回滚：
- 只读兼容永久保留；不需要把历史重写成 V3。

---

## 5. 验收与证据（迁移任务本身如何证明“已落地”）

迁移不是“看起来更简洁”，而是必须能用证据证明：

- **引用完整性**：`validate-refs` 对典型任务通过；broken refs 可定位与修复。
- **闭环成立**：至少有一个新任务完全按 Gate A/B/C/D 跑通，并有 review/evidence JSON 产物。
- **可恢复**：中断后能只靠 plan/workflow + refresh-pack 回到当前 subtask。
- **不引入新厚对象**：没有新增“为了恢复而复制的摘要”成为新的长期依赖。

---

## 6. 未决问题（需要你拍板的地方）

已拍板（来自当前仓库使用约束）：

1. **目录落位**：本仓库只提供模板与规范；在真正使用 V3 时才需要在目标项目统一 `.agentdocs/`。controller/脚本应支持在目标 repo 中一键初始化 `.agentdocs/`。
2. **subtask 粒度默认值**：允许默认单 subtask。
3. **旧 V2 artifacts 的兼容窗口**：`task-packs/` 完全不需要兼容与保留（不作为迁移读取入口）。
4. **controller 形态**：倾向实现一个新的 controller（按 V3 `controller/COMMANDS.md`），而不是沿用 V2 `taskctl.py`。
