# Agentic Codex Runtime v3 Fusion 审计

日期: 2026-03-17

范围:
- `agentic_codex_runtime_v3_fusion/`
- 对照参考 `agentic_codex_runtime_v3/`
- 对照参考 `coding-agent-flow/`
- 对照设计母规范 `docs/references/design_structure_V2.md`

## 审计结论

`agentic_codex_runtime_v3_fusion` 的融合方向是正确的，且总体可行。

它最重要的正确性在于:

- 没有让 `coding-agent-flow` 的 GitHub-first、Harness-first、PRD-first 去反向塑形 `v3` 的 truth model。
- 保住了 `plan.md / workflow.md / reviews / evidence / subtask-pack` 作为 runtime core。
- 把 GitHub、worktree、session recovery、contracts、hooks/CI 都降到了 optional modules，而不是把它们提升成新的长期真相层。

但当前形态仍然是:

- 架构方向正确
- 工程上基本可行
- 机制闭环不够完整

更准确地说，它现在更像:

- `v3 runtime core`
- 加上一组设计边界正确的 optional modules

而不是一套已经完全闭环、所有新约束都被 deterministic control plane 接住的融合 runtime。

## 主要发现

### 1. [High] 融合后新增的关键计划字段没有被 controller 强制校验

`fusion` 的 `plan.md` 模板新增了这些关键字段:

- `Observable effect`
- `Demo sentence of success`
- `Terminal completion definition`

见:

- `agentic_codex_runtime_v3_fusion/.codex/templates/plan.md:15`
- `agentic_codex_runtime_v3_fusion/.codex/templates/plan.md:16`
- `agentic_codex_runtime_v3_fusion/.codex/templates/plan.md:27`

这些字段正是融合后最重要的 DISCUSS 强化点，直接对应:

- 目标效果是否明确
- 成功时最短 demo sentence 是否明确
- 终态定义是否锁死

但 `agentctl.py` 的 `plan_gate_errors()` 仍只检查旧版字段:

- `Problem`
- `Goal`
- `Deliverable`
- `Why now`
- 旧版 Acceptance 字段

见:

- `agentic_codex_runtime_v3_fusion/.codex/tools/agentctl.py:301`
- `agentic_codex_runtime_v3_fusion/.codex/tools/agentctl.py:306`

这意味着:

- 一个没有填写 `Observable effect` 的计划，仍可能通过 plan completeness
- 一个没有填写 `Terminal completion definition` 的计划，仍可能被当成 review-ready

判断:

- 设计意图是对的
- 但还停留在模板和 skill 说明层
- 没有真正落到 deterministic enforcement

这是当前最重要的融合缺口。

### 2. [High] `fresh pack` 是制度要求，但系统实际上只检查“pack 是否存在”

`fusion` 在文档和 skill 中明确要求 `subtask-pack` 必须是 fresh:

- `agentic_codex_runtime_v3_fusion/.agents/skills/execute-subtask/SKILL.md:10`
- `agentic_codex_runtime_v3_fusion/.agents/skills/session-recovery/SKILL.md:17`
- `agentic_codex_runtime_v3_fusion/docs/agentic/reference/controller-commands.md:23`

其中 `controller-commands.md` 明写:

- `plan-review` 前必须满足 `fresh pack`
- `implement` / `close-review` 前必须有 `fresh pack`

但 `agentctl.py` 的 `check-gate()` 实际只做这类检查:

- pack ref 是否存在
- pack 文件是否存在

见:

- `agentic_codex_runtime_v3_fusion/.codex/tools/agentctl.py:1014`
- `agentic_codex_runtime_v3_fusion/.codex/tools/agentctl.py:1034`
- `agentic_codex_runtime_v3_fusion/.codex/tools/agentctl.py:1045`

系统没有做以下任何一种 freshness 绑定:

- pack 是否晚于当前 `plan.md`
- pack 是否晚于当前 `workflow.md`
- pack 是否携带 plan/workflow revision
- pack 是否因 evidence / external refs / review 状态变化而失效

`refresh-pack` 只写了 `Generated at`，见:

- `agentic_codex_runtime_v3_fusion/.codex/tools/agentctl.py:792`

这会带来两个实际问题:

- 长任务 / 多 session 下，pack stale 只能靠 agent 主观判断
- optional modules 越多，staleness 来源越多，系统越容易“口头要求 fresh，实际上继续拿旧 pack 干活”

判断:

- 这不否定融合可行性
- 但会直接削弱融合后 runtime 的可靠性

### 3. [Medium] DISCUSS 被强化了，但在冻结计划前缺少可恢复的结构化承载物

`fusion` 增加了 `discuss-clarification`，这是明显进步。它把 DISCUSS 从“差不多懂了”的主观判断，升级成结构化澄清循环，并要求产出 discuss summary:

- `agentic_codex_runtime_v3_fusion/AGENTS.md:41`
- `agentic_codex_runtime_v3_fusion/.agents/skills/discuss-clarification/SKILL.md:13`
- `agentic_codex_runtime_v3_fusion/.agents/skills/discuss-clarification/SKILL.md:127`

但在 plan 真正冻结之前，系统里没有一个结构化、可恢复的 discuss summary 对象。

当前可持久化对象只有:

- `workflow.md` 的 Discuss readiness 布尔位
- `workflow.md` 的 minimal events
- draft `plan.md`

见:

- `agentic_codex_runtime_v3_fusion/.codex/templates/workflow.md:16`
- `agentic_codex_runtime_v3_fusion/.codex/templates/workflow.md:44`

问题在于:

- readiness 布尔位太薄，不能承载已澄清的关键结论
- minimal events 只是事件日志，不是结构化澄清结果
- draft `plan.md` 在规范上又不能被视为 frozen Goal truth

因此一旦出现:

- 多轮 DISCUSS
- 跨 session 澄清
- 用户多次修正边界

恢复时仍然会依赖:

- 人工回读对话
- 草稿计划侧写
- agent 的上下文纪律

这说明 `fusion` 在 DISCUSS 这一层，概念已经增强，但恢复闭环还没有完全补齐。

### 4. [Medium] `docs/contracts/*` 的定位正确，但没有进入 controller 的引用校验图

`fusion` 对长期合同文档的处理是合理的:

- 只在跨 task、跨 reviewer、可长期复用时才创建
- 明确“补充而不是替代 `plan.md`”

见:

- `agentic_codex_runtime_v3_fusion/docs/contracts/README.md:3`
- `agentic_codex_runtime_v3_fusion/.agents/skills/contract-artifacts/SKILL.md:19`

这是比 `coding-agent-flow` 更好的边界处理。

但当前问题是:

- `validate-refs()` 并不认识 `docs/contracts/*`
- controller 也不会检查它们与当前 plan/task 的 traceability

见:

- `agentic_codex_runtime_v3_fusion/.codex/tools/agentctl.py:859`
- `agentic_codex_runtime_v3_fusion/.codex/tools/agentctl.py:907`

这意味着:

- 这些文档可以被写出来
- 也可以被团队逐步依赖
- 但 runtime 没有对其 freshness / traceability / ref validity 做最小保障

判断:

- 当前作为 optional knowledge object 是可行的
- 一旦真正开始频繁依赖，系统支撑会偏弱

### 5. [Medium] `fusion` 的 `AGENTS.md` 比 `v3` 更短，但新增模块更多，导致 auto-loaded guidance 反而变弱

`v3` 的 `AGENTS.md` 在 controller 命令后还有两段关键内容:

- 技能路由
- 完成定义

见:

- `agentic_codex_runtime_v3/AGENTS.md:92`
- `agentic_codex_runtime_v3/AGENTS.md:104`

而 `fusion` 的 `AGENTS.md` 到 controller 命令示例就结束了，全文共 96 行:

- `agentic_codex_runtime_v3_fusion/AGENTS.md`

结果是:

- `fusion` 增加了更多模块
- 但核心入口 guidance 并没有同步增强
- 新模块何时触发、何时不该触发，更依赖使用者记忆而不是 always-on guidance

这不会直接破坏 truth model，但会降低运行时自解释能力。

### 6. [Low] `External refs` 的设计边界是对的，但目前只是一条字符串型 pointer，不是更强的外部镜像协议

`fusion` 对 GitHub 的处理总体是正确的:

- GitHub 只做 mirror
- controller 只记录 `External refs`
- 不把 issue / PR 变成 SoT

见:

- `agentic_codex_runtime_v3_fusion/.agents/skills/github-collaboration/SKILL.md:22`
- `agentic_codex_runtime_v3_fusion/.codex/templates/workflow.md:34`
- `agentic_codex_runtime_v3_fusion/.codex/tools/agentctl.py:1223`

当前 `External refs` 的实现是最小够用的:

- 支持合并多个 `gh:issue#123` / `gh:pr#456`
- 能带入 `workflow.md`
- 能透传到 `subtask-pack`

见:

- `agentic_codex_runtime_v3_fusion/.codex/tools/agentctl.py:139`
- `agentic_codex_runtime_v3_fusion/.codex/tools/agentctl.py:825`

这本身不是错误，但它意味着:

- 外部镜像关系还比较弱
- 系统不会验证这些 refs 是否存在
- 系统也不会区分“当前主协作 issue”和“历史引用”

如果后续只把它保持在 traceability pointer 层，这没问题。
如果以后希望把 GitHub 协作进一步体系化，则还需要额外的 adapter 约束。

## 为什么我认为融合方向仍然是正确的

尽管存在上述问题，我仍然认为融合方向正确，原因是这些问题大多属于:

- 机制覆盖不足
- controller 未完全跟上
- optional module integration 强度偏弱

而不是根本的架构边界错误。

以下关键决策我认为是对的:

- `plan.md` 仍然是唯一 task-local Goal truth
- `workflow.md` 仍然是唯一 Process truth
- `subtask-pack` 仍然是派生视图
- `reviews/*.json` 与 `evidence/*.json` 仍然分离
- 不引入 `harness-tasks.json` / `harness-progress.txt`
- 不让 GitHub issue / PR 升格成 runtime truth
- 不把 TDD / TestCases / PRD/API/UI 设为每个 task 的强制前置对象

见:

- `agentic_codex_runtime_v3_fusion/README.md:5`
- `agentic_codex_runtime_v3_fusion/docs/agentic/spec/08-fusion-decision-checklist.md:7`
- `agentic_codex_runtime_v3_fusion/docs/agentic/spec/08-fusion-decision-checklist.md:31`

## 可行性判断

### 现在是否可用

可以用，但更适合:

- 理解边界清楚的任务
- 使用者已经理解 `v3` truth model 的场景
- 愿意人工遵守 freshness / discuss discipline 的团队

### 现在是否适合长程自治

还不完全适合。

主要阻碍不是 optional modules 本身，而是:

- 新融合出来的 DISCUSS 强化字段没有被 controller 强制接住
- pack freshness 还不是系统事实
- DISCUSS 跨 session 的恢复承载仍然偏薄

### 现在是否比“直接把 flow 整套塞进 v3”更好

是，明显更好。

因为当前问题都属于“半闭环”，而不是“边界被破坏”。
如果反过来把 `flow` 整套宪法化，问题会升级成:

- truth model 被破坏
- review independence 被破坏
- GitHub / Harness 越权
- 第二状态账本长期存在

这会比当前状态更难修。

## 问题分级

### 必须补机制

- 新增 plan 字段必须进入 controller completeness 检查
- `fresh pack` 必须从“口头要求”提升成可判定状态

### 应该补机制

- 给 DISCUSS 前冻结阶段一个更可恢复的结构化承载方式
- 让 `docs/contracts/*` 至少进入最小 traceability 校验
- 恢复 `AGENTS.md` 中的 skill routing / done definition 入口 guidance

### 可以后置

- `External refs` 更细粒度的结构化协议
- 更强的 GitHub adapter 规范

## 最终判断

`agentic_codex_runtime_v3_fusion` 的融合:

- 在方向上是正确的
- 在对象边界上是健康的
- 在工程落地上是基本可行的
- 在机制闭环上还不够完整

因此最准确的评价不是“融合错了”，而是:

它已经完成了正确的架构取舍，但还没有把最关键的新融合点 fully operationalize。

如果后续要继续推进，优先级应该是:

1. 先补 controller 对新字段和 freshness 的接管
2. 再补 DISCUSS / contracts 的恢复与 traceability
3. 最后再考虑更丰富的 GitHub / adapter 能力

