# Repository Working Agreement

> 把开发过程变成 **可复现、可验证、可回滚、可断点重续、可持续演进** 的工程活动。
>
> **最高优先级原则：控制平面不能覆盖事实平面。**
>
> - 要做什么：看用户确认 + 已冻结 plan
> - 现在是什么：看代码 / 测试 / 配置 / 运行结果
> - 是否做成：看 verification / evidence / reviewer 抽样

## 0. 先记住这 8 条硬规则

1. **代码是当前事实真源，文档是运行时控制入口。** 进入 BUILD 后，代码 / 测试 / 配置 / 运行结果优先级高于文档叙述。
2. **理解度未达到 95% 不得开工。** 目标、范围、非目标、当前事实、写入边界、验收、风险、待决问题任一不清楚，视为未达标。
3. **先证明理解，再写 plan；先通过 plan review，再进入 build。**
4. **Task Pack 是所有执行与评审角色的第一入口。**
5. **结构化写回优先，且 review / evidence 不混用。** review bundle 记录 judgment，evidence bundle 记录 facts；`reviews/*.json` 不得充当 `Evidence Ref`。
6. **并行 writer 仅在写域独立、worktree 独立、任务独立时允许。**
7. **主 agent 只负责 route / state / delegation / reroute，不承担手工书记员。**
8. **凡是可以被结构化、幂等执行、schema 校验的内容，优先下沉到 controller 脚本。**

---

## 1. 5 层模块模型（系统级边界）

### 1.1 Policy Layer（稳定层）

定义不变量与规则：

- `AGENTS.md`
- `docs/dev/contracts/*`

职责：

- 定义状态机、真源优先级、task pack 最低字段、review 规则、结构化写回要求。

不负责：

- 不定义具体哪个角色去做某一步
- 不绑定具体 skill 实现

### 1.2 Orchestration Layer（编排层）

定义当前如何调度执行：

- `.codex/config.toml`
- `.codex/agents/*.toml`
- workflow router / review router

职责：

- 选择角色
- 决定是否进入 multi-agent
- 决定当前 phase / review mode / next legal action

### 1.3 Capability Layer（能力层）

定义可复用能力模块：

- `.agents/skills/*`

职责：

- 提供可渐进加载的 specialist 能力
- 主 agent 知道能力目录；执行角色按需深读完整技能手册

规则：

- Router 类 skill：短、薄、可隐式触发
- Specialist 类 skill：边界窄，默认不应被主 agent 深读
- Tooling 类 skill：尽量只是脚本调用封装

### 1.4 State Layer（状态层）

定义运行时 SSOT：

- `.agentdocs/index.md`
- `.agentdocs/tasks/<task-id>/workflow.md`
- `.agentdocs/tasks/<task-id>/plan.md`
- `.agentdocs/tasks/<task-id>/task-packs/*`
- `.agentdocs/tasks/<task-id>/reviews/*`
- `.agentdocs/tasks/<task-id>/evidence/*`
- `.agentdocs/archive/*`

职责：

- 持久化当前任务状态
- 提供跨会话恢复锚点
- 为可视化与审计提供稳定输入

状态所有权：

- `plan.md`：冻结后的规格真源（目标、范围、验收、契约、阶段拆分、回滚）
- `workflow.md`：运行时状态真源（当前 state、phase 进度、review 结论、事件、归档结果）
- `task-packs/*`：当前 phase 的最小派发包；只保存 digest 与 source pointers，不复制完整规格
- `reviews/*.json`：独立技术评审结论真源
- `evidence/*.json`：事实证据真源

### 1.5 Controller Layer（执行接口层）

定义确定性接口：

- `.codex/workflow/taskctl.py`
- `.codex/workflow/templates/*`

职责：

- 目录落位
- 模板渲染
- task pack 校验
- delegation brief 生成
- review/evidence/event 的结构化写入
- skill lint
- archive / index sync

原则：

- skill 不应依赖仓库里零散脚本路径；优先通过 controller 提供的稳定入口完成结构动作。

---

## 2. 双平面模型

### 2.1 控制平面

用于让任务可控、可恢复、可审计：

- `AGENTS.md`
- `task pack`
- `workflow.md`
- `plan.md`
- `reviews/`
- `archive/`

### 2.2 事实平面

用于回答“系统现在实际是什么”：

- 代码
- 测试
- 配置
- 命令输出 / 日志
- 页面行为 / 运行时证据
- 结构化 evidence bundle

### 2.3 真源优先级

#### 未来意图真源

1. 用户确认后的需求 / 决策
2. 当前 plan 中冻结的目标、范围、验收、边界

#### 当前事实真源

1. 代码
2. 测试
3. 配置
4. 运行结果 / 日志 / UI 行为
5. 文档
6. 历史 workflow / archive / insights

规则：

- 控制平面可以**约束动作**，不能**覆盖事实**。
- 任何 BUILD 任务都必须把事实平面的锚点写进 plan / task pack。
- `workflow.md` 不复制完整 plan；`task pack` 不成为第三份规格；`review` 与 `evidence` 各自保留独立引用。

---

## 3. 唯一正常路径（High-Entropy）

High-Entropy 任务只能按这一条顺序推进：
`DISCUSS -> ALIGN_PROOF -> BOOTSTRAP -> ISSUE_SYNC -> PLAN_DRAFT -> PLAN_REVIEW -> BUILD -> CLOSE_REVIEW -> ARCHIVE`

硬门禁：

- `ALIGN_PROOF` 未完成：禁止写 plan、禁止派发 writer
- `PLAN_REVIEW = PASS` 前：禁止进入 `BUILD`
- `CLOSE_REVIEW = PASS` 前：禁止进入 `ARCHIVE`
- 用户纠偏导致 `Goal / Scope / Acceptance / Contract` 任一项变化时：必须回退到 `PLAN_DRAFT`
- 发现 `build-before-review`、证据缺失、review 中断、task pack 过期或状态冲突时：必须进入 `EXCEPTION_RECOVERY`

---

## 4. 新会话与开工前对齐

### 4.1 最小开工顺序

1. 读取项目级 `AGENTS.md`
2. 读取 `.agentdocs/index.md`
3. 定位唯一活动任务
4. 恢复当前 phase 的 task pack
5. 定向读取 pack 中列出的 deep refs
6. 若要执行实现：补做最小 Git 检查
   - `git status --short --branch`
   - `git diff --stat`
   - `git diff --name-only`

### 4.2 95% 理解度检查表

以下 8 项任意 1 项不明确，就视为未达到 95%：

- 目标
- 范围
- 非目标
- 当前事实锚点
- 写入边界
- 验收方式
- 风险点
- 待决问题

### 4.3 ALIGN_PROOF 必须回答

- 我理解这次要交付什么？
- 明确不做什么？
- 当前系统真实状态由哪些代码 / 测试 / 配置锚点证明？
- 哪些是计划意图，哪些是当前事实？
- 还有哪些问题必须先问清？

---

## 5. Task Pack 是所有 sub-agent 的第一入口

每次进入 `PLAN_REVIEW / BUILD / CLOSE_REVIEW` 前，都必须存在当前 phase 的 task pack。

Task pack 至少包含：

- Task Identity
- Current State / Allowed Next State
- Understanding Proof
- Spec Source
- Review Inputs
- Frozen Decisions
- Must Read
- Verified Adjacent Context
- Current Truth Anchors（代码 / 测试 / 配置 / 运行结果）
- Write Boundary
- Invariants
- Verification Obligations
- Open Risks / Escalations
- Previous Findings（若为复核轮次）

没有 task pack：

- 不得派发 reviewer
- 不得启动 worker
- 不得声称“当前上下文已足够”

说明：

- task pack 是 phase-scoped digest，不是 plan / workflow 的并行完整版
- review 类 task pack 必须把当前 review 轮次真正要复核的 code / architecture / evidence 输入冻结出来

---

## 6. Skills 加载模型

- `.agents/skills/` 是 **discoverability surface**：让主 agent 先知道“有哪些能力存在”。
- `.codex/` 是 **runtime control surface**：放角色配置、controller、workflow runtime。

规则：

1. 主 agent 可以知道 specialist skill 的 metadata，但不默认深读完整 `SKILL.md`
2. 真正被委派的 specialist 角色才读取完整手册与 reference checklist
3. 长 checklist、长案例、边界细节应放 `references/`，而不是塞满 `SKILL.md`
4. `SKILL.md` 本体应尽量薄，至少包含：
   - When to use
   - When NOT to use
   - Inputs
   - Outputs / Write Contract / Escalation

---

## 7. 多 agent 运行协议

### 7.1 角色职责

- **main agent**：route、state transition、选择 role、选择 skill、reroute；不充当手工书记员
- **explorer**：探索事实、缩小上下文、写 findings / scratch / evidence stub
- **worker**：在明确 write boundary 内实现与验证
- **plan_reviewer / close_reviewer**：基于代码 / 架构 / 测试 / 日志 / evidence 做独立技术判断；有分析权和否决权，没有实现权、改写权、调度权；允许写 task-scoped review bundle
- **monitor**：等待、轮询、简报

### 7.2 固定 6 段 sub-agent 指令接口

每次委派都应明确：

1. `Identity`
2. `Boundary`
3. `Objective`
4. `Procedure`
5. `Output Contract`
6. `Escalation`

说明：

- 主 agent 的 spawn 指令只给最小流程骨架，不重写 specialist checklist
- 完整 checklist 由被委派角色自己加载 specialist skill

### 7.3 委派包必须包含

- `Role`
- `Task Pack`
- `Goal`
- `Review Mode`（review 场景必填）
- `Must Read`
- `Current Truth Anchors`
- `Write Boundary`
- `Escalation Rule`
- `Output Contract`

### 7.4 写入规则

- **结构化写入优先**：review bundle / evidence / workflow event / archive manifest / index sync / delegation brief 优先用脚本完成
- **自由手写仅用于语义内容本体**：例如 plan 正文、实现代码、分析结论
- reviewer / explorer 可以 `workspace-write`，但只能写 task-scoped 工件或结构化产物，不直接改业务代码
- reviewer 的 `Required Changes / Required Follow-ups` 必须是最小修改闭包，不得写成替代性完整 plan、替代性实现方案或替代性路由方案

### 7.5 并行 writer 规则

只有满足其一时才允许多个 writer 并行：

1. 任务天然独立可并行，且写域完全独立
2. 使用独立 worktree
3. 完成并行任务后需要进行工作区的检查

禁止：

- 同一 worktree 中两个写入型 agent 并发写同一写域
- reviewer 与 worker 在同一写域中交叉改动

---

## 8. deterministic controller（taskctl）

统一入口：

```bash
python .codex/workflow/taskctl.py <subcommand>
```

推荐 subcommand：

- `create-task`
- `check-transition`
- `advance-state`
- `make-pack`
- `validate-pack`
- `emit-delegation-brief`
- `record-review`
- `record-evidence`
- `record-workflow-event`
- `sync-index`
- `lint-skills`
- `archive-task`

规则：

- 能由 controller 稳定完成的动作，不应手工维护
- controller 产出的结构文件必须可审阅、可追踪、可供后续可视化读取
- review / evidence / archive manifest 这类结构化工件默认以 JSON 为唯一持久化格式
- 能被路径、字段、存在性、枚举值、状态机与引用类型稳定判定的问题，应优先进入 controller / canonical preflight，而不是交给 reviewer 肉眼兜底
- 若 controller 失败，主 agent 只能报告失败与最小恢复动作，不得悄悄手改让结果“看起来通过”

---

## 9. Plan 必须显式包含的块

每份 high-entropy plan 必须至少包含：

1. `Understanding Proof`
2. `What I Need / My Requirements / You Decide`
3. `Current Truth Anchors`
4. `Must-Haves`
5. `Verification Ladder`
6. `Reviewer Recheck Plan`
7. `UAT`
8. `Issue Breakdown`
9. `Rollback / Migration`
