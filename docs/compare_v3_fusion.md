# Agentic Codex Runtime v3 vs v3 Fusion 差异对比

日期: 2026-03-18  
对比范围:

- `agentic_codex_runtime_v3/`
- `agentic_codex_runtime_v3_fusion/`

本文件只回答一个问题: `fusion` 相比 `v3` 多了什么、改了什么、因此使用方式哪里不同。

## 1. 总体结论

`agentic_codex_runtime_v3_fusion` 是 `agentic_codex_runtime_v3` 的超集:

- 保留 v3 的 runtime core 与 truth model 设计不变。
- 在 v3 core 之上，吸收了少量工程化协作设计，主要以 optional modules 形式存在。
- 明显强化了 `DISCUSS -> PLAN` 的澄清机制与对外协作/恢复/隔离工作区的可选能力。

## 2. 文件与目录层面的差异

### 2.1 仅 fusion 存在的内容

Optional modules 与附加规范:

- `.githooks/*` (repo guardrails): `install.sh`, `pre-commit`, `pre-push`, `README.md`
- `.github/workflows/security-checks.yml` (repo guardrails)
- `.agents/skills/contract-artifacts/`
- `.agents/skills/discuss-clarification/`
- `.agents/skills/github-collaboration/`
- `.agents/skills/session-recovery/`
- `.agents/skills/worktree-isolation/`
- `docs/contracts/*` (可选的长期合同文档体系)
- `docs/agentic/reference/optional-modules.md`
- `docs/agentic/spec/08-fusion-decision-checklist.md`

示例/归档痕迹:

- `.agentdocs/archive/T000-v3-audit/*` (一个被归档的样例 task)
- `.agentdocs/archive/index.md` 额外包含 `T000-v3-audit` 的条目

### 2.2 v3 与 fusion 都存在但内容不同的文件

- `README.md` (定位从 v3 runtime 说明变为 runtime core + optional modules)
- `AGENTS.md` (从“含路由说明”变为“更薄的宪法 + 更强的 DISCUSS 规则”)
- `.codex/templates/plan.md` (计划字段强化)
- `.codex/templates/workflow.md` (新增 external refs 指针位)
- `.codex/templates/subtask-pack.md` (新增 external refs)
- `.agents/skills/freeze-plan/SKILL.md` (与 discuss-clarification 的前置关系更明确)
- `.agents/skills/world-grounding/SKILL.md` (明确区分: repo grounding != user intent clarification)
- `.codex/tools/agentctl.py` (支持 external refs 写回与 pack 透传)
- `docs/agentic/reference/controller-commands.md` (补充 external refs 用法)
- `docs/agentic/spec/02-architecture-and-modules.md` (补充 optional modules 的边界)
- `docs/agentic/spec/05-migration-from-legacy.md` (补充吸收工程模板时的边界条款)
- `docs/agentic/spec/07-discuss-and-plan-contract.md` (DISCUSS 的执行方式与 “discuss summary”)

## 3. 规范与使用方式差异 (核心变化点)

### 3.1 `DISCUSS -> PLAN` 的“澄清”被显式制度化

v3:

- `DISCUSS` 规则主要体现为: 在冻结 `plan.md` 前必须澄清关键歧义并达成双 95% 理解度。
- 技能路由说明集中在 `AGENTS.md` 末尾的“技能路由”段落里。

fusion:

- 额外提供了 `discuss-clarification` 技能，把 DISCUSS 变成可执行的澄清循环。
- `docs/agentic/spec/07-discuss-and-plan-contract.md` 更强调:
  - 每轮只问高价值的 2-3 个问题
  - readiness gap 扫描
  - 在进入 `freeze-plan` 之前产出并确认 `discuss summary`
- `AGENTS.md` 明确允许 draft `plan.md` 作为澄清工具，但禁止把 draft plan 倒灌成 frozen truth (并禁止在 DISCUSS 未达标前做 plan-review / refresh-pack / implement)。

### 3.2 允许“外部协作镜像”，但必须降级为指针

v3:

- workflow 与 subtask-pack 不承载外部系统指针位。

fusion:

- `workflow.md` 新增 `External refs` 指针位，用于记录外部协作镜像(例如 GitHub issue/PR)。
- `agentctl.py update-current` 新增 `--external-ref`，允许把外部 refs 写回到 `workflow.md`。
- `refresh-pack` 会把 `workflow.md` 的 `External refs` 透传进 `subtask-pack.md`，以便参与者在 pack 中看到外部协作上下文，但仍不改变 truth model (外部系统不是 SoT)。

### 3.3 “可拔插模块”的边界被单独写成规范

v3:

- runtime core 的设计边界在 v3 spec 里隐含表达，没有对“可选模块”给出独立的分类说明。

fusion:

- 明确把 hooks、GitHub、worktree、session recovery、contracts 都定义为 runtime core 之外的 optional modules。
- 单独提供 `docs/agentic/reference/optional-modules.md` 和 `docs/agentic/spec/08-fusion-decision-checklist.md` 来解释:
  - 允许吸收什么
  - 必须放弃什么
  - 为什么不能污染 truth model 和 deterministic control plane

## 4. 关键文件差异摘要

### 4.1 `AGENTS.md`

v3:

- 包含“技能路由”和“完成定义”的集中说明，参与者可直接按该段落选择技能与完结信号。

fusion:

- 更强调 DISCUSS 不是主观自评，需要结构化澄清循环和 discuss summary。
- 把“技能路由/完成定义”等更偏操作手册性质的内容从 `AGENTS.md` 移除，倾向于让 skills 与 `docs/agentic/*` 承载细节。

### 4.2 `plan.md` 模板

v3:

- Goal 区包含 `Problem / Goal / Deliverable / Why now`。
- Acceptance 区包含 `Success criteria / User-visible acceptance signal / Out-of-scope guardrail / Not acceptable completion definitions`。

fusion:

- Goal 区新增:
  - `Observable effect`
  - `Demo sentence of success`
- Acceptance 区新增:
  - `Terminal completion definition`
- 这些字段使得 fusion 更偏 “contract-first / evidence-first planning”: 先锁外部可观察效果与终态，再进入实现自由度讨论。

### 4.3 `workflow.md` 与 `subtask-pack.md` 模板

v3:

- workflow pointers 只覆盖 plan/pack/evidence/review 的 repo 内引用关系。

fusion:

- workflow pointers 增加 `External refs`。
- subtask-pack 增加 `External refs` 区块，用于呈现外部协作镜像，但仍不赋予其真相权力。

### 4.4 Skills

fusion 新增 skills:

- `discuss-clarification`: DISCUSS 澄清循环与 discuss summary
- `github-collaboration`: 外部协作镜像(并要求写回 external refs)
- `session-recovery`: 跨 session 恢复检查(明确不引入第二账本)
- `worktree-isolation`: worktree 隔离执行(明确不把 worktree 变成真相层对象)
- `contract-artifacts`: 可选长期合同文档(明确不替代当前 task 的 `plan.md`)

fusion 修改的 core skills:

- `freeze-plan`: 强化“前置条件必须先完成澄清与世界立足”，并更明确 draft vs frozen 的边界。
- `world-grounding`: 更明确区分 repo grounding 与 user intent clarification，鼓励把意图歧义退回 `discuss-clarification`。

### 4.5 Controller (`agentctl.py`)

v3:

- controller 只处理 repo 内的 truth objects 与派生 pack 再生，不承载外部系统镜像指针。

fusion:

- 支持 `update-current --external-ref ...` 写入 workflow 的 `External refs`。
- pack 再生时把 external refs 透传到 pack，降低参与者寻找协作上下文的成本。

### 4.6 文档体系

fusion 相比 v3 额外强调:

- optional modules 的分类与边界 (`docs/agentic/reference/optional-modules.md`)
- 融合吸收的决策清单与红线 (`docs/agentic/spec/08-fusion-decision-checklist.md`)
- 可选长期合同文档体系 (`docs/contracts/*`)

## 5. 使用建议 (何时选 v3，何时选 fusion)

如果仓库不需要外部协作镜像、worktree 隔离、session 恢复或长期合同文档约束，优先选 v3，保持 runtime core 尽可能薄。

如果仓库确实需要这些工程能力，且团队能接受把它们严格降级为 optional modules，不允许污染 truth model，则可以选 fusion，并只按需启用对应模块与技能。

