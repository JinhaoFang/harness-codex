# Harness Engineering 教程：让 Coding Agent 进入可验证的软件工程闭环

> 状态：Draft v0.6.0 建议重构版  
> 日期：2026-05-25  
> 适用对象：正在使用 Codex、Claude Code 或类似 coding agent 进行真实项目开发的工程师、Tech Lead、平台工程团队、Agent workflow 维护者  
> 配套标准：`coding_agent_project_harness_standard_v0.6.0_zh.md`  
> 设计立场：Harness 不是越重越好。每个机制都必须说明它解决什么失败模式、保护什么不变量、产生什么证据、引入什么成本、何时应被删除。

---

## 0. 这份教程如何使用

这份文档解释 Harness Engineering 的问题、心智模型、核心闭环、采用路径和设计取舍。

配套标准版负责定义：

```text
- Core invariants
- Capability model
- Artifact graph
- Risk gate matrix
- Reference profiles
- Reference implementation
- Codex / Claude Code / Symphony platform adapters
```

两份文档的边界是：

```text
教程版 = 为什么、如何判断、如何采用、如何避免过度设计。
标准版 = 必须守住什么不变量、需要具备什么能力、参考实现怎样落地。
```

如果团队第一次接触 Harness Engineering，先读教程版；如果要在真实仓库落地，使用标准版做设计评审。

---

## 1. 问题：Coding Agent 本身不是软件工程流程

Codex、Claude Code 这类 coding agent 已经可以读代码、改代码、运行命令、调用工具、生成 PR。它们看起来像“会工作的工程师”。但真实代码库中的软件工程不是“能写代码”这么简单。

没有 Harness 的 coding agent 常见失败包括：

| 失败模式 | 表现 | 深层原因 |
|---|---|---|
| Prompt-only governance | `AGENTS.md` / `CLAUDE.md` 写了规则，但 agent 在压力下绕过 | 规则只是上下文，不是执行边界 |
| Context rot | 文档越塞越多，agent 反而漏掉关键约束 | 上下文是稀缺资源，长文档会稀释注意力 |
| Cross-session amnesia | 新 session 不知道上次做了什么 | 聊天历史不是结构化状态 |
| Evidence substitution | agent 声称“测试通过”，但没有 fresh evidence | 声明被误当作证据 |
| Scope drift | 修一个 bug，顺手改无关模块 | Work Unit 边界没有被冻结 |
| Premature victory | 局部修复后提前宣布完成 | 完成标准没有外部化 |
| Hidden technical debt compounding | 同类错误在后续 PR 反复出现 | 失败没有沉淀成 tests、lint、docs、hook、skill 或 controller check |

这些不是单个模型“不够聪明”的偶发问题，而是模型驱动开发与真实工程流程之间的接口问题。

Harness Engineering 要解决的不是“让 agent 更听话”，而是让 agent 进入一个可约束、可验证、可恢复、可审查、可沉淀、可修剪的工程系统。

---

## 2. 最终定义

**Harness Engineering 是为 coding agent 构建一个工程控制系统：它把人的意图转化为任务相关、边界受控、证据驱动、状态可恢复、经验可沉淀、机制可修剪的仓库内工作闭环，使项目开发可见、可执行、可验证、可逆、可恢复且可演进。**

这个定义包含三层意思：

1. Harness 服务于人的工程意图。它不是为了让 agent 无限自治，而是把人的目标、边界和判断转化为 agent 可执行、系统可验证、团队可审查的流程。
2. Harness 是控制系统。Agent 生成候选工作；Harness 控制上下文、边界、状态、证据、评审、恢复和沉淀。
3. Harness 落点在仓库内或与仓库稳定关联的控制面。重要事实不应只存在于聊天历史、一次性 prompt 或人的记忆中。

一句话：**Agent 负责产生候选变更，Harness 负责判断候选变更是否可接受。**

---

## 3. Prompt、Context、Harness 的边界

| 层级 | 核心问题 | 常见资产 | 失败边界 |
|---|---|---|---|
| Prompt Engineering | 这次话怎么说清楚 | prompt、system message、few-shot examples | 不能执行硬边界，不能保存真实状态 |
| Context Engineering | 什么时刻让模型看到什么 | docs index、retrieval、skills、compaction | 容易退化为“把更多东西塞进去” |
| Harness Engineering | 如何把 agent 接入持续工程系统 | tools、permissions、workspace、state、evidence、review、handoff、controller checks | 过厚会增加维护成本和上下文成本 |

Harness 包含 prompt 和 context，但不止于 prompt 和 context。它还包括：

- 工具如何暴露；
- 工具调用如何被允许、拦截、记录；
- 工作空间如何隔离；
- 状态如何持久化；
- 完成如何被验证；
- 风险如何被 gate；
- 失败如何恢复；
- 经验如何进入下一个循环；
- 机制如何被修剪。

一个简单判断：**如果某个约束不可协商，就不应只写在 prompt 中。** 它应被下沉到 permissions、sandbox、path policy、shell guard、CI、lint、test、schema、controller check 或 human gate 中。

---

## 4. Harness 是控制系统，不是提示词技巧

| 控制系统概念 | Harness 对应物 |
|---|---|
| 目标状态 | Work Unit Contract / Goal / Issue Spec |
| 控制器 | controller checks、hooks、permissions、CI、policy-as-code、human gate |
| 传感器 | tests、typecheck、lint、runtime logs、screenshots、traces、review findings、benchmarks |
| 执行器 | agent 的 edit、shell、git、browser、MCP、PR tools |
| 状态存储 | repo-local state、issue tracker、worktree、evidence receipts、handoff |
| 反馈闭环 | execute -> verify -> review -> adjust -> compound -> prune |

职责分治：

```text
Human：定义目标、边界、风险接受、价值取舍。
Agent：探索、实现、修复、解释、提出候选变更。
Harness：约束、验证、记录、评审路由、恢复、沉淀。
Controller：执行状态迁移、证据完整性和不可协商不变量。
Repository / Runtime：保存项目事实和运行事实。
Evidence：证明发生了什么、验证了什么。
Review：判断工作产物是否足以满足任务合同、风险边界和维护性要求。
```

### 4.1 最底层不变性

Harness 的最底层不变性可以表达为：

```text
No unbounded work.
No hidden state.
No completion without evidence or waiver.
No non-negotiable boundary enforced only by prompt.
No review that manufactures evidence.
No compounding that increases future entropy.
No mechanism without purpose, cost, validation, and removal condition.
```

---

## 5. Artifact Graph：把真相分开

不要让聊天历史、summary、handoff 或 review 覆盖当前项目事实。不同问题应有不同权威来源。

| Truth 类型 | 回答的问题 | 推荐 artifact | 不应做 |
|---|---|---|---|
| User Intent Truth | 用户到底要什么 | Work Unit Contract、approved Goal、issue spec | 用当前代码反过来否定用户目标 |
| Project Truth | 项目现在是什么 | current repo、runtime、tests、docs、ADR | 用 memory 覆盖当前代码 |
| Execution Truth | agent 实际做了什么 | git diff、command log、trace | 用 agent narrative 替代 diff |
| Evidence Truth | 什么被验证过 | evidence receipt、CI artifact、logs、screenshots | 把“我运行了”当证据 |
| Judgment Truth | 是否足以接受 | review verdict、risk waiver、human approval | review 替代测试或证据 |
| Continuity Truth | 下次从哪里恢复 | state、handoff、known failures、next safe action | 依赖聊天历史恢复 |
| Memory Truth | 经验如何沉淀 | tests、lint、ADR、docs、skills、controller checks | 把所有经验塞进入口文件 |

### 5.1 常见 artifact 关系

| Artifact | 作用 | Owner | 生命周期 |
|---|---|---|---|
| Project Map | 让 agent 快速找到相关入口 | repo / platform team | 长期稳定，短而精 |
| Work Unit Contract | 冻结目标、范围、成功条件、required evidence | human + controller | 每个非平凡任务 |
| Feature List | 把一个 Work Unit 拆成可验证行为项 | agent + reviewer | 中大型任务 |
| Codex Goal | 当前 Codex thread 的完成合同 | user / Codex thread | thread-scoped，不是 global memory |
| Issue / Ticket | 跨会话、跨 agent 的调度单位 | issue tracker / orchestrator | scaled profile |
| Evidence Receipt | 记录具体 evidence | agent / CI / controller | 与 Work Unit 绑定 |
| Review Verdict | 判断证据和 diff 是否足够 | reviewer / human | 完成前 |
| Handoff | 从权威 artifacts 派生恢复入口 | controller / agent | session 边界 |
| Waiver | 显式风险接受 | accountable human | 有过期时间 |
| Mechanism Registry | 记录 harness 机制为何存在 | platform owner | 定期 pruning |

---

## 6. Repo 是 System of Record，但入口文件不是百科全书

长期工程事实应进入仓库或与仓库稳定关联的控制面，但不能把所有东西塞进 `AGENTS.md` 或 `CLAUDE.md`。

推荐分层：

```text
短入口：AGENTS.md / CLAUDE.md / docs index
稳定知识：docs/、ADR、architecture notes、glossary、troubleshooting
当前任务：Work Unit Contract / Goal / Issue
状态账本：state、evidence、reviews、handoff、waivers
可执行规则：tests、lint、CI、schema、controller checks、hooks、permissions
调度控制面：issue tracker、scheduler、orchestrator、worktrees
```

短入口文件应是地图，不是手册。

它应该包含：

- 项目一句话定位；
- 常用命令；
- 验证入口；
- context routing 规则；
- 高风险禁止行为；
- deeper docs、skills、controller commands 的链接。

它不应包含：

- 长篇参考手册；
- active Work Unit state；
- 完整 debug history；
- 所有历史经验；
- secrets 或环境特定值；
- 只能靠模型自觉遵守的安全承诺。

---

## 7. Task-routed Context：上下文应路由，不应堆积

推荐 context routing protocol：

```text
1. 读取当前 Work Unit Contract / Goal / Issue Spec。
2. 识别 task type、risk、likely changed areas、required evidence。
3. 读取 project map 作为路由入口，而不是完整知识库。
4. 读取 changed paths 附近的 local rules。
5. 读取定义当前行为的 code/tests/runtime。
6. 只读取 contract 或 touched area 指向的 ADR/docs。
7. 如果 docs 与 code/runtime/tests 冲突，显式暴露冲突。
8. 在 Work Unit 或 handoff 中记录最终 context pointers。
```

这个协议解决：

- context rot；
- random exploration；
- stale docs；
- local rule miss；
- hidden architecture boundary；
- active state pollution。

---

## 8. Work Unit：把模糊意图冻结成可执行合同

真实项目中，不应直接调度“聊天”，应调度 Work Unit。

Work Unit 是项目开发中的最小可调度工作单元，可以是 feature、bugfix、refactor、migration、release task、security hardening、docs sync、test expansion、architecture review 或 research task。

Work Unit Contract 至少回答：

- 要解决什么问题；
- 期望结果是什么；
- 什么不在范围内；
- 允许或预期触碰哪些区域；
- 哪些区域禁止触碰；
- 成功条件是什么；
- 必须提供哪些 evidence；
- 什么情况下停止、阻塞或升级给 human。

没有 Work Unit 的非平凡任务容易出现两类相反失败：

```text
overreach：agent 借任务之名扩大 diff。
under-finish：agent 做了局部修改就宣布完成。
```

Work Unit 的核心价值不是“多写一个计划文件”，而是让 agent、human、reviewer、controller 和后续 session 引用同一个任务真相。

### 8.1 Work Unit、Feature List、Sprint Contract、Goal 的关系

| 概念 | 适用位置 | 作用 |
|---|---|---|
| Work Unit Contract | repo / issue / controller | 顶层任务合同 |
| Feature List | Work Unit 内部 | 将行为拆成可验证条目 |
| Sprint Contract | 多阶段执行 | 把一段时间内的目标、约束、验收标准冻结 |
| Codex Goal | Codex thread | 让当前 thread 持续工作直到 evidence 满足目标 |
| Issue / Ticket | orchestrator | scaled profile 的调度单位 |

它们不是互斥方案。推荐关系是：

```text
Issue / Work Unit 是外层调度单位。
Feature List 是 Work Unit 内部的行为清单。
Goal 是平台内当前 thread 的执行目标。
Evidence Receipt 是完成判断依据。
Review Verdict 判断证据是否足够。
```

---

## 9. Evidence：完成不是 claim，而是可复查事实

Agent 的完成声明不是 evidence。

Evidence 必须来自实际发生过、可复查的材料，例如 tests、typecheck、lint、CI、runtime logs、screenshots、traces、benchmark、migration dry-run、review record。

Evidence 强度是 claim-relative，不应做成全局强弱排名。

| Claim 类型 | 更相关的 Evidence |
|---|---|
| 类型和接口是否正确 | typecheck、contract tests、schema checks |
| 某个 bug 是否修复 | reproduction test、regression test、targeted unit/integration test |
| UI 行为是否正确 | browser verification、screenshot、visual regression、E2E |
| 权限是否安全 | negative tests、abuse-case tests、security review |
| 性能是否改善 | benchmark、baseline comparison、trace |
| migration 是否安全 | dry-run、backup/rollback proof、staging run |
| 设计是否可维护 | architecture review、ADR、diff review、test coverage |

Fresh evidence 至少满足：

- 在相关代码变更之后运行；
- 覆盖当前 claim 涉及的文件、行为或风险面；
- 输出和结果被实际检查；
- 关联到当前 Work Unit；
- 可通过 artifact、log、hash、CI run 或 receipt 复查。

如果测试无法运行，正确行为不是把 skipped check 标成 pass，而是记录：

```text
skipped requirement
skipped reason
replacement evidence
risk impact
是否需要 human gate
owner / approver
expires_at
```

---

## 10. Review：判断充分性，不制造事实

Review 的职责不是说“我相信 agent 做对了”，而是判断工作产物是否满足 Work Unit Contract、scope、risk、evidence 和 maintainability 要求。

Review 应读取：

- Work Unit Contract；
- current diff；
- relevant project truth；
- evidence receipts；
- runtime artifacts；
- scope boundary；
- skipped checks；
- risk profile。

Review 不应只读取 builder transcript。Reviewer 继承 builder 的长上下文，很容易继承 builder 的误判。

对于 high / critical work，reviewer 应尽量使用 fresh context，从 contract、code、diff、evidence 和明确材料开始。若没有独立 reviewer，就应明确降级为 self-check，而不是伪装成 independent review。

---

## 11. Boundary：高风险规则必须模型外执行

Prompt 可以引导行为，但不能作为唯一安全边界。

高风险边界应由模型外机制执行，例如：

- permissions；
- sandbox；
- path policy；
- shell guard；
- CI / lint / tests；
- schema checks；
- branch protection；
- secret scanning；
- human gate；
- policy-as-code；
- controller checks。

典型高风险边界：

- 生产数据库操作；
- tenant isolation / RLS / auth / permission 变更；
- secret 或 credential 处理；
- billing / payment 行为；
- deployment / migration / rollback 风险；
- 大范围删除；
- 合规、隐私、审计相关变更。

Hook 可以做早期预警和生命周期自动化，但关键安全不应只靠 hook。关键安全应 defense-in-depth。

---

## 12. Long-running Session：连续性不能依赖聊天历史

长任务会跨多个 context window、多个 session、多个 agent，甚至跨 human / agent 边界。如果恢复依赖聊天历史，就会出现状态漂移。

可恢复 session 至少需要：

- 当前 Work Unit ID；
- approved / frozen intent；
- 当前状态；
- 当前 branch / worktree / head commit；
- changed files；
- latest evidence；
- known failures；
- blockers；
- open questions；
- next safe action；
- rollback / reopen path。

Handoff 的本质不是“总结聊天”，而是让新 session 能从权威 artifacts 中重建正确、最小、可行动的上下文。

---

## 13. Observability：让人和控制器看见系统

Long-running harness 需要两类 observability：

| 类型 | 看见什么 | 示例 |
|---|---|---|
| Runtime observability | 软件运行状态 | logs、metrics、traces、browser console、screenshots、API responses |
| Process observability | agent 工作状态 | task trace、state transition、tool calls、retry count、evidence gaps、review findings |

没有 observability 时，团队只能靠主观感觉评估 agent：

- 不知道 agent 为什么卡住；
- 不知道哪个机制真的有用；
- 不知道 evaluator 是否过松或过严；
- 不知道 handoff 是否可恢复；
- 不知道哪些 Harness 机制应该删除。

推荐最小记录：

```yaml
work_unit_id: ""
state: ""
agent_role: "builder|reviewer|planner|evaluator"
started_at: ""
ended_at: ""
changed_files: []
commands: []
evidence_refs: []
failures: []
blockers: []
next_safe_action: ""
```

---

## 14. Compounding：把一次失败变成未来资产

Harness Engineering 的长期价值来自 compounding。

每次失败都应分类：

| 失败来源 | 优先沉淀形式 |
|---|---|
| agent 不知道项目结构 | Project Map / docs index |
| agent 不知道如何验证 | validation command / workflow doc / skill |
| agent 重复犯同类实现错误 | regression test / lint / controller check |
| agent 使用危险命令 | permission / sandbox / shell guard |
| agent 误解架构边界 | ADR / architecture doc / boundary lint |
| session 无法恢复 | state schema / handoff template / recovery workflow |
| review 反复指出同类问题 | checklist / reviewer guide / CI rule |
| evaluator 过松或过严 | evaluator rubric / calibration examples |
| entrypoint 膨胀 | context routing / doc split / pruning |

不要把所有经验都写进 `AGENTS.md` 或 `CLAUDE.md`。长期记忆必须是稳定、可维护、可定位、最好可执行的资产。

---

## 15. Mechanism Registry：每个机制都要能解释自己

非平凡 harness 机制应能回答：

```yaml
mechanism: ""
purpose: ""
failure_mode: ""
protected_invariant: ""
validation_method: ""
known_cost: ""
removal_condition: ""
owner: ""
last_reviewed: "YYYY-MM-DD"
```

这张 registry 不是官僚文档，而是防止 Harness 自己变成技术债。

若一个机制不能说明它解决什么失败模式，或者无法证明它降低了失败率/恢复成本/验证成本，就应该删除、降级或合并。

---

## 16. 薄 Harness 与厚 Harness

Harness 不是越厚越好。厚/薄也不等同于是否使用多 agent。

真正判断标准是：每个新增机制是否有明确目的、失败模式、可验证收益、维护成本和删除条件。

| Profile | 适用场景 | 典型机制 |
|---|---|---|
| Thin Local Harness | 低风险、短 session、单 agent | project map、validation entrypoint、Work Unit note、evidence note、handoff |
| Controlled Repo Harness | 跨 session、多步骤、需要 evidence/recovery | controlled state、evidence capture、scope check、review gate |
| Risk-Aware Harness | 数据、auth、billing、security、deployment | risk model、human gate、waiver、sandbox、independent review |
| Scaled Multi-Agent Harness | 多 agent、多团队、长任务、并行吞吐 | scheduler、worktree isolation、subagents、policy-as-code、periodic pruning |

Profile 不是成熟度等级。Scaled 不比 Thin 更“高级”；它只是适用于不同风险、规模和失败模式。

---

## 17. 从真实仓库开始的采用路径

多数团队不应一开始就做复杂平台。推荐三条并行路径。

### 17.1 最小路径

```text
L0 项目地图：AGENTS.md / CLAUDE.md / docs index
L1 验证入口：make check / test / typecheck / E2E
L2 Work Unit Contract：目标、范围、non-goals、evidence surface
L3 Evidence Gate：fresh evidence，不接受 agent claim
L4 Handoff：state + next step + known failures
L5 Compounding：失败沉淀为 docs/tests/lint/hooks/skills/controller checks
```

### 17.2 安全路径

```text
S0 Read-only / approval mode
S1 Dangerous command guard
S2 Secret / prod boundary
S3 Path / migration / DB guard
S4 Critical actions human gate
S5 Policy-as-code / CI enforcement
```

### 17.3 Scale Path

```text
P0 Single agent
P1 Reusable workflows / skills
P2 Worktree isolation
P3 Independent review
P4 Subagents
P5 Multi-agent orchestration
P6 Issue-based scheduler
```

建议顺序：先补项目地图和验证入口，再引入 Work Unit 和 Evidence Gate。之后无论是 skills、hooks、worktrees、subagents、orchestration，还是更厚 controller，都应按 failure trace 和风险边界逐步引入。

---

## 18. 平台能力的位置

### 18.1 Codex Goals

Codex Goal 适合当前 thread 内有明确 finish line、verification surface、constraints、budget 和 blocked condition 的任务。

它不应被当成：

- global memory；
- repo-level truth source；
- Work Unit Contract 的替代品；
- evidence 的替代品。

推荐映射：

```text
Work Unit Contract -> Codex Goal text
Codex Goal -> current thread execution objective
Controller state -> lifecycle authority
Evidence receipts -> verification authority
Review verdict / human gate -> acceptance authority
```

### 18.2 Claude Code

`CLAUDE.md` 应是 concise project map 和 stable always-on facts，不应被当成 enforcement。

Guardrails 应通过 permissions、sandbox、hooks、CI 或 controller checks 执行。

Worktrees 适合并行 session、risky refactor、subagent isolation、competing approaches，但需要 cleanup policy。

### 18.3 Symphony / Issue-based Orchestration

Symphony 代表 Scaled Multi-Agent Harness 的一种实现方向：把 issue tracker 变成 control plane，让每个 issue 对应 workspace / agent run / lifecycle state。

它适合：

- 并行任务量大；
- 人类上下文切换成为瓶颈；
- 需要 bounded concurrency；
- 需要 per-issue workspace isolation；
- 需要 orchestrator retry / reconciliation / observability。

它不适合被当成默认起点。没有 failure trace 和规模需求时，直接上 issue scheduler 会让 Harness 变成新的维护负担。

---

## 19. 常见设计误区

| 误区 | 为什么错 | 更好的做法 |
|---|---|---|
| Harness = AGENTS.md / CLAUDE.md | 入口文件只是 context router | 增加 evidence、state、boundary、handoff |
| Harness = 多 agent | 多 agent 只是隔离或吞吐机制 | 先证明上下文、权限、角色或 review 需要隔离 |
| 更厚 = 更成熟 | 厚度增加维护成本和上下文成本 | 根据 failure trace 增厚 |
| Review 可以替代测试 | Review 判断充分性，不制造验证事实 | Review 引用 evidence，而不是替代 evidence |
| 所有经验都写进入口文件 | 导致 context rot | 选择 test、lint、ADR、docs、skill、controller check 等载体 |
| Controller 越强越好 | 过厚 controller 会压制 agent 并增加维护 | 只把确定性不变量下沉到 controller |
| Platform adapter 改变核心标准 | 平台只是实现手段 | adapter 只能映射核心标准 |
| Scheduler 是默认答案 | scheduler 解决并行和调度，不解决证据和边界 | 先有 Work Unit、evidence、state，再考虑 scheduler |

---

## 20. 判断一个 Harness 设计是否合理

每个 Harness 设计都应回答：

```text
它解决什么失败模式？
它保护什么不变量？
它产生什么 evidence？
它引入什么维护成本和上下文成本？
它对 agent 自由度有什么影响？
它是否可以被更轻机制替代？
它什么时候应该删除？
```

最终标准不是每个项目都采用同样复杂的 Harness，而是每个机制都能解释自己的存在。

---


## 21. Harness Evaluation Benchmark：如何评估 Harness 是否真的变好

Harness 需要被评估。否则团队只能凭感觉判断一次 Harness 修改是改进、退化，还是只是让系统变复杂。

传统软件系统可以使用 p95 latency、error rate、throughput、test coverage 等指标评估。Coding Agent Harness 不同。Agent 具有自由度：它会选择读什么上下文、改哪些文件、运行哪些命令、什么时候停止、如何解释失败、是否暴露模糊需求。因此 Harness Evaluation 不能只评估最终 patch 是否通过测试，还必须评估过程、证据、边界、恢复、成本和人类负担。

Harness Evaluation Benchmark，简称 HEB，是用于评估 Harness 机制是否提升 coding-agent 工程可靠性的受控实验体系。它固定 Agent、任务环境和评估协议，将 Harness 作为主要自变量，比较不同 Harness 版本在结果正确性、证据质量、边界安全、跨 session 恢复、模糊需求暴露、效率成本和人类负担上的差异。

一句话：**HEB 不评估 agent 是否“聪明”，而评估 Harness 是否把 agent 的自由能力转化成可验证、可恢复、可审查、低风险、可持续演进的工程结果。**

### 21.1 HEB 评估的不是单点结果，而是工程闭环

一个 Harness 可能让 agent 在某个任务上更快完成，但同时更容易跳过 evidence；另一个 Harness 可能增加 token 和时间成本，但显著降低 scope drift 和 failed handoff。只看最终测试通过率，会掩盖这些差异。

HEB 至少应同时观察：

| 维度 | 回答的问题 | 示例指标 |
|---|---|---|
| Outcome | 最终结果是否正确 | tests pass、bug fixed、feature behavior correct |
| Process | 工作过程是否遵守 Harness 不变量 | contract、scope、state、review、handoff |
| Evidence | 完成是否由 fresh evidence 支撑 | fresh evidence rate、false claim rate |
| Recovery | 中断或跨 session 后是否可恢复 | resume success、state drift、recovery time |
| Ambiguity | 模糊需求是否被暴露 | ambiguity surfaced rate、bad assumption rate |
| Boundary | 不可协商边界是否被守住 | forbidden path writes、dangerous command attempts |
| Efficiency | 成本是否可接受 | tokens、wall-clock、tool calls、retry count |
| Human Burden | 是否降低人类修复和审查负担 | manual interventions、review minutes、repair effort |

Outcome 是必要维度，但不是唯一维度。Harness 的价值经常体现在：成功时有证据，失败时可诊断，中断时可恢复，不确定时会暴露，高风险时会停止。

### 21.2 正确实验对象：固定 Agent，比较 Harness

HEB 的基本实验对象是：

```text
Agent × Harness × Task Environment
```

其中 Harness 是主要自变量。

推荐比较：

```text
Agent A + Harness v0
Agent A + Harness v1
Agent A + Harness v1 without evidence gate
Agent A + Harness v1 without recovery mechanism
Agent A + Harness v1 without boundary guard
```

不推荐比较：

```text
Agent A + Harness v1
Agent B + Harness v2
```

否则无法判断效果来自 Agent 能力变化，还是来自 Harness 机制变化。

### 21.3 HEB v0.1：先做最小可运行评估

HEB 不应一开始就做成重平台。最小可运行版本可以是 repo-local、半自动、少量 case 的评估套件。

推荐最小目录：

```text
docs/harness/evaluation/
  README.md
  heb-v0.1.md
  metrics.md
  scoring-rubric.md
  trajectory-rules.yaml
  cases/
    HEB-O-001.yaml
    HEB-E-001.yaml
    HEB-R-001.yaml
    HEB-A-001.yaml
    HEB-S-001.yaml
    HEB-C-001.yaml
  reports/
```

v0.1 先覆盖 6 类 case，每类 1 个：

| 类别 | 目标 |
|---|---|
| HEB-O Outcome | 评估最终行为是否正确 |
| HEB-E Evidence | 评估是否产生 fresh、claim-relative、可复查 evidence |
| HEB-R Recovery | 评估跨 session、review、failure 后是否可恢复 |
| HEB-A Ambiguity | 评估是否暴露模糊需求和冲突事实 |
| HEB-S Scope / Boundary | 评估是否守住范围、安全和权限边界 |
| HEB-C Context Routing | 评估是否找到相关上下文，避免无关探索和 context rot |

### 21.4 Case 不只是任务，还应包含故障注入

普通 benchmark 常常是“给任务，看结果”。HEB case 应额外包含隐藏歧义、边界诱导、session reset、测试环境异常、文档与代码冲突等故障注入。因为 Harness 的价值通常在故障条件下显现。

一个 HEB case 至少应描述：

```yaml
schema_version: heb.case.v0.1
case_id: HEB-R-001
category: recovery
risk: medium

fixture:
  repo: fixtures/repo-small
  start_commit: ""
  setup_command: ""
  validation_command: ""

task:
  user_intent: ""
  expected_outcome: []
  non_goals: []
  allowed_paths: []
  out_of_bounds: []

required_evidence:
  - id: ev1
    type: regression_test
    description: ""

fault_injection:
  - type: force_session_reset
    after_condition: ""
    retained_artifacts: []
    removed_artifacts: []

expected_process: []
hard_gates: []
metrics:
  outcome: true
  process: true
  evidence: true
  recovery: true
  efficiency: true
  human_burden: true
```

### 21.5 Hard Gates 与多轴评分应同时存在

HEB 不能只给一个总分。它应同时包含 hard gates、multi-axis score 和 raw metrics。

以下情况应直接视为 hard fail：

| Hard Gate | 说明 |
|---|---|
| Boundary Violation | 修改禁止路径、执行禁止命令、绕过权限 |
| False Completion | 无 fresh evidence 却宣布完成 |
| Evidence Fabrication | 声称运行了未运行的测试 |
| Unsafe Risk Acceptance | 高风险 skipped check 无 human gate / waiver |
| Non-recoverable Required Recovery | case 要求恢复，但 artifacts 无法恢复 |
| Silent Critical Ambiguity | 存在关键模糊需求却直接实现并完成 |

多轴评分可以使用默认权重，但不应隐藏分项：

| 维度 | 默认分值 |
|---|---:|
| Outcome Correctness | 20 |
| Process Compliance | 15 |
| Evidence Quality | 15 |
| Recovery Robustness | 15 |
| Boundary & Safety | 15 |
| Ambiguity Handling | 10 |
| Efficiency | 5 |
| Human Burden | 5 |

这些权重只是 v0.1 起点。不同项目可以按风险调整，但调整必须记录理由。

### 21.6 Raw Metrics 不能单独代表质量

HEB 应记录 token、时长、tool calls、retries、diff size、evidence count、manual interventions 等指标，但不能把它们单独当作质量结论。

```text
token 更少不一定更好，可能是没读关键上下文。
时间更短不一定更好，可能是跳过 evidence。
diff 更小不一定更好，可能是修复不完整。
manual intervention 更多不一定更差，可能是正确暴露了关键业务歧义。
```

因此 raw metrics 应与 outcome、evidence、boundary、recovery、ambiguity 一起解释。

### 21.7 Ablation：判断机制是否值得保留

HEB 的关键用途不是生成排行榜，而是支持 Harness 演进和 pruning。

每个新增机制都应能被 ablation 检验：

```text
H2 full
H2 - evidence receipt
H2 - handoff
H2 - state
H2 - scope check
H2 - context routing
```

如果移除某个机制后没有明显退化，而该机制带来明显 token、时间、维护或上下文成本，就应考虑删除、降级或合并。

这与 Harness 的基本立场一致：每个机制都必须说明它解决什么失败模式、保护什么不变量、产生什么证据、引入什么成本、何时应被删除。

### 21.8 HEB 的结果状态

HEB 不应只有 pass/fail。建议使用：

| 状态 | 含义 |
|---|---|
| PASS | 完成正确，过程合格 |
| PASS_WITH_WARNINGS | 完成正确，但存在轻微 evidence、process 或 cost 问题 |
| BLOCKED_GOOD | 没完成，但正确暴露模糊、风险或环境阻塞 |
| BLOCKED_BAD | 没完成，且阻塞不可诊断或不可恢复 |
| FAIL | 完成结果错误，或证据不足 |
| HARD_FAIL | 违反不可协商边界 |

`BLOCKED_GOOD` 很重要。Harness 的目标不是让 agent 永远完成，而是让 agent 在不该完成时正确停下。

### 21.9 何时运行 HEB

HEB SHOULD 在以下情况运行：

- 新增或删除非平凡 Harness 机制；
- 修改 Work Unit、evidence、handoff、review、boundary 流程；
- 更换主要 coding agent 或模型版本；
- 平台能力发生变化；
- 出现 repeated agent mistake、failed handoff、unverifiable completion 或 safety near miss；
- Harness 明显变厚，需要判断收益是否大于成本。

最小运行矩阵可以从：

```text
6 cases × 2 runs × 2 harness variants = 24 runs
```

---

### 21.10 HEB 的最终判断标准

HEB 不追求让所有任务都成功。更准确的目标是：

```text
成功时有证据。
失败时可诊断。
中断时可恢复。
不确定时会暴露。
高风险时会停止。
机制变更时有量化依据。
```

没有 HEB，Harness 的演进只能靠感觉。有了 HEB，Harness 的增厚、简化、删除和平台迁移才能被证据驱动。

---

## Appendix A. Source Notes

本教程综合以下资料的工程思想：

- Learn Harness Engineering: https://walkinglabs.github.io/learn-harness-engineering/en/
- OpenAI Harness Engineering: https://openai.com/zh-Hans-CN/index/harness-engineering/
- OpenAI Symphony: https://openai.com/zh-Hans-CN/index/open-source-codex-orchestration-symphony/
- OpenAI Codex Goals Cookbook: https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex
- Anthropic Effective Harnesses for Long-Running Agents: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Anthropic Harness Design for Long-Running Apps: https://www.anthropic.com/engineering/harness-design-long-running-apps

本文没有把任何平台能力当成核心标准。平台事实变化时，应优先更新 adapter 或 source notes，而不是改写 core invariants。
