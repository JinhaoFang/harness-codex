# 全局准则

## 风格

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 使命

- 确保编码工作可复现、可验证、可逆、可恢复且可演进，并且为项目的长期平滑演进消除隐性技术债。
- 将确定性正确性下沉到控制器中；将概率性工作保留在澄清、规划、评审和实施判断中。

## 0. Runtime 布局

- `AGENTS.md` = Codex 自动加载的仓库工作协议。
- `.codex/config.toml` = 项目 Codex 默认配置和角色注册表。
- `.codex/agents/*.toml` = 用于 Subagents（子代理协作）的 custom agents 角色配置（需 `name` / `description` / `developer_instructions`）。
- `.agents/skills/*` = 仓库技能（阶段 skill / 方法 skill / 评审 skill）。
- `.codex/tools/agentctl.py` = 确定性控制平面。
- `docs/agentic/spec/07-discuss-and-plan-contract.md` = `DISCUSS -> PLAN` 的最小冻结合同。
- `.agentdocs/insight.md` = 跨任务可复用的工程/迁移/治理经验（非真相层；禁止复制单次 workflow；必须带可复核 anchors）。
- `.agentdocs/architecture/` = 项目架构设计专题 SoT（非真相层；必须可用 code/tests/evidence 复核）。
- `.agentdocs/tasks/<task-id>/plan.md` = 目标事实。
- `.agentdocs/tasks/<task-id>/workflow.md` = 过程事实。
- `.agentdocs/tasks/<task-id>/reviews/*.json` = 评审结论。
- `.agentdocs/tasks/<task-id>/evidence/*.json` = 过程证据。
- `.agentdocs/tasks/<task-id>/subtask-packs/*.md` = 衍生摘要。
- 代码 / 测试 / 运行时行为 = 世界事实。
- `docs/agentic/` = 更深层的设计原理和迁移说明。

## 1. 基本偏好

- 先理解项目已有架构、规范、文档和相关代码，再进入设计或实现。
- 长期状态优先落文件，但**事实判断必须回到代码 / 测试 / 配置 / 运行结果**。
- 复杂任务优先拆成“理解证明、规格、执行、评审、终审、归档”几个阶段。

## 2. 工程偏好

- **捍卫 DRY (Don't Repeat Yourself)**：优先复用现有代码路径，积极标记 DRY 违反；确保任何逻辑、配置或知识点在系统中拥有单一、明确且权威的真源。
- **奉行 KISS (Keep It Simple, Stupid)**：简单即是高级；显式优于巧妙；追求代码的直观与自解释性，不鼓励使用隐晦的技巧（Hacky）或复杂的元编程逻辑。
- **践行 YAGNI (You Ain't Gonna Need It)**：只为当前明确的需求编写代码；拒绝过度工程，不过早抽象，不为“万一以后用到”的幻觉预留复杂度或扩层。
- **测试即契约**：充分的测试是硬性要求；行为验证、回归测试和边角 case 是代码完整性的核心，不应被随意省略。
- **追求“工程化适度”**：在简洁与健壮之间寻找平衡点；深思熟虑优先于盲目快改；最小 diff 优于破坏性的无意义重构。
- **架构可视化**：复杂设计、关键数据流、状态转换和非显然测试 setup 倾向使用 mermaid 图表达。
- **文档即代码**：修改附近已有 mermaid 图的代码时，图的维护是变更的一部分；过期的文档比没有文档更具误导性，必须同步更新或标记作废。
- **代码文件**：
  - 代码文件顶部必须包含模块说明
  - 函数如果需要可以加上 docstring 说明
  - 单文件 < 1000行。


## 3. 上下文策略

- 按需、最小化加载上下文；优先找真正相关的代码与文档，不做大范围无差别泛读。
- 文档负责压缩意图与经验，代码负责陈述当前事实。
- 新会话中，先读取索引与 task pack，再定向展开深文档。

## 4. 规格与执行分离

- 先冻结目标、范围、边界、契约和验收，再进入执行。
- issue 是 plan 派生出的子任务，不承担完整规格真源职责。
- 若执行时发现规格不足，先退回规格层，不边做边改口径。

## 5. 硬性规则

- 不要为了修补流程问题而新增长期工件；优先强化现有 `AGENTS.md`、`plan.md`、`workflow.md`、review/evidence schema、subtask-pack 与 controller。
- 在冻结计划之前，必须先把任务立足于当前代码库，并先把用户意图澄清到可冻结程度。
- 将 `DISCUSS -> PLAN` 视为最重 gate；在 draft plan 前，必须先澄清交付物、目标效果、终态（完成定义）与哪些不算完成、必保要求、非目标、证据信号、写入边界、阶段顺序、审批点、删除 / 迁移条件与未决问题。
- `DISCUSS` 不是主观“差不多懂了”的自评；必须通过结构化澄清循环、缺口扫描与 discuss summary 确认来收敛。
- `DISCUSS` 只有在“用户意图理解度 >= 95%”且“项目现实理解度 >= 95%”同时成立时才算完成；不得用“plan 已经写出来了”倒推 `DISCUSS` 已完成。
- draft `plan.md` 允许作为暴露歧义的澄清工具，但在 DISCUSS 未达标前：
  - 不得将其视为 frozen Goal truth
  - 不得请求 `plan-review`
  - 不得刷新 subtask pack 作为 review / implementation 的入口
  - 不得进入实现或 close-ready 判断
- 在计划评审通过之前不得实施。
- 在 task 级 `Task close-ready = YES` 之前不得归档；单个 subtask 的 close review PASS 不等于整个 task 可归档。
- `plan-review` / `close-review` verdict 必须走 controller 的 `request-review -> submit-review` 流程；`main` 可以请求 review，但不得自己提交 reviewer verdict。
- 保持 `plan.md` 仅关注目标事实。
- 保持 `workflow.md` 仅关注过程事实。
- 将评审和证据分开。
- 将子任务包视为衍生视图，绝不视为新的事实来源。
- 对于结构化写入、验证、归档、重新开启和包刷新，优先使用控制器命令。
- TDD 是方法 skill，不是 runtime gate，也不应被嵌入 stage / controller；但任何 code-bearing development task 在实现时都必须启用 `tdd`。
- owner-side 的工程方案挑战可以使用 `plan-eng-review`，但它不能替代正式 `plan-review` verdict。
- 当现实与文字描述冲突时，信任代码、测试、配置和运行时行为，而非过时的摘要。
- `parent -> subagent` 的交接应只提供 role、task id、subtask id、request id、当前目标和可选 extra focus；subagent 必须自己从 `.agentdocs/*` 与当前代码世界重建上下文。
- `.agentdocs/*` 是 subagent 的任务 / 过程同步层，不是世界真相替代层；代码 / tests / config / runtime 仍然是 world truth。
- 不允许评审者角色修改业务代码。
- `plan-review` 必须完整核对任务要求层与 Goal truth 核心约束；World truth 只允许在显式记录抽样范围、依据与残余风险时抽样。
- 对迁移 / 删除 / 重组 / 重新分类类任务，review 必须回看原始 source materials，不能只看迁移后的输出物。
- 所有 rereview 都必须重新做一次 full-scope review；上轮 findings 只能作为回归检查清单，不能成为新的 scope 边界。
- 当任何 subagent 的结果位于当前关键路径上时，主 agent 不得在结果返回前推进依赖该结果的清理、归档或完成性判断；默认 wait 时间是 30 mins，单次 wait 超时不等于失败。
- 在运行相关的真实仓库命令之前，不得声称工作已完成。

## 6. 最低关卡

- **理解 / 讨论 (Discuss / Understand)**：通过结构化澄清循环明确交付物、目标效果、非目标、必保要求、可授权决定、验收标准、阶段顺序、审批点、删除 / 迁移条件和未决问题，并达到用户 / 项目双 95% 理解度。
- **立足世界 (Ground in World)**：检查入口点、关键符号、现有测试、可复用机制和兼容性约束。
- **冻结目标事实 (Freeze Goal Truth)**：编写 `plan.md`，冻结交付物、效果、边界、不变量、验证 / 证据计划、回滚和子任务。
- **独立评审 (Independent Review)**：使用全新上下文进行计划评审和关闭检查。

## 7. subagent 路由矩阵

- `plan_reviewer`：当 grounded plan 已准备好并需要独立 verdict 时使用；主 agent 先请求 `plan-review`，再等待 reviewer 通过 `submit-review` 回写。
- `close_reviewer`：当实现证据已齐备并需要独立 close verdict 时使用；主 agent 先请求 `close-review`，再等待 reviewer 通过 `submit-review` 回写。
- `explorer`：当 world grounding 跨多个入口 / 符号 / source materials，或主会话已经被探索笔记、日志、堆栈跟踪污染时优先使用。
- `worker`：当一个 grounded subtask 的写入边界明确、`implement` gate 合法、active pack 新鲜，且实现已经超过“极小单文件修补”时默认优先使用；大多数 code-bearing development subtasks 默认交给 worker 执行。仅在改动极小、无需上下文隔离、或主会话直接修改更稳时，才保留在主会话。
- 所有 subagent 默认 wait 时间是 `30 mins`。
- 关键路径上的 subagent 未返回前，不得推进依赖该结果的下一步 gate。
- reviewer verdict 未通过 `submit-review` 落入 workflow 前，不得把其视为已完成 review。
- 任何重新 review 都优先新开 fresh reviewer 线程；若复用旧 reviewer，也必须按 fresh review 规则重新读取当前 truth。

## 8. subagent 交接契约

主 agent 负责路由，不负责替 subagent 重写完整工作法。

最小交接内容：
- role
- task id
- subtask id
- review request id（如果是 reviewer）
- current objective
- optional extra focus / required method overlay

subagent 的标准进入顺序：

```text
parent handoff
    |
    v
subtask pack
    |
    v
plan.md + workflow.md
    |
    v
latest relevant refs
    |
    v
minimum world truth
    |
    v
role-specific action
```

补充规则：
- `subagent-bootstrap` 是所有 subagent 的共享进入技能。
- `worker` 进入后叠加 `execute-subtask`；对 code-bearing development task 再强制叠加 `tdd`。
- `plan_reviewer` / `close_reviewer` 进入后叠加各自 review skill；extra focus 只能加严，不能缩窄必检范围。

## 9. 可选技能 / 模块激活索引

- 对任何 code-bearing development task：必须启用 `tdd`。
- 需要让任何 subagent 从 `.agentdocs/*` 自举、避免过度依赖主 agent recap 时：启用 `subagent-bootstrap`。
- 需要在 formal `plan-review` 前先做 owner-side 的工程方案挑战时：启用 `plan-eng-review`。
- 需要外部协作镜像、issue / PR traceability 或 `gh` 交互时：启用 `github-collaboration`。
- 需要并行执行空间、风险隔离或 reviewer 复现时：启用 `worktree-isolation`。
- 需要跨 session 恢复、中断后重进或大上下文清理后继续时：启用 `session-recovery`。
- 需要长期复用的业务 / API / UI 合同时：启用 `contract-artifacts`。
- 需要 repo 级工程护栏时：启用 `.githooks/*` 与对应 CI guardrails。

## 10. 控制器命令

使用这些命令作为确定性操作界面：

```bash
python .codex/tools/agentctl.py init-agentdocs
python .codex/tools/agentctl.py create-task --slug fastapi-backend-audit --title "FastAPI backend audit"
# 记下 create-task 输出里的 <task-id>；正常场景优先 --slug，--task-id 只作显式 override
python .codex/tools/agentctl.py update-current --task-id <task-id> --current-gate "Ground in World" --allowed-next-action "Freeze Goal Truth"
python .codex/tools/agentctl.py refresh-pack --task-id <task-id> --subtask S1
python .codex/tools/agentctl.py request-review --task-id <task-id> --review-type plan --subtask S1
python .codex/tools/agentctl.py submit-review --task-id <task-id> --review-type plan --subtask S1 --request-id <request-id> --reviewer-role plan_reviewer --decision PASS
python .codex/tools/agentctl.py check-gate --task-id <task-id> --action implement
python .codex/tools/agentctl.py write-evidence --task-id <task-id> --subtask S1 --kind test --result PASS --purpose "已验证子任务" --command "<真实命令>"
python .codex/tools/agentctl.py archive --task-id <task-id>
python .codex/tools/agentctl.py reopen --task-id <task-id> --trigger "scope-change" --reason "用户更改了验收标准"
```