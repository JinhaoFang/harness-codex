# AGENTS.md

## 使命

- 确保编码智能体的工作可复现、可验证、可逆、可恢复且可演进。
- 将确定性正确性下沉到控制器中；将概率性工作保留在规划、评审和实施判断中。

## 仓库布局

- `AGENTS.md` = Codex 自动加载的仓库工作协议。
- `.codex/config.toml` = 项目 Codex 默认配置和角色注册表。
- `.codex/agents/*.toml` = 用于多智能体工作的精细化角色配置。
- `.agents/skills/*` = 仓库技能。
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

## 本地项目命令

在依赖此运行时之前，请更新这些命令以匹配目标仓库。

- install（安装）: `<fill-me>`
- dev（开发）: `<fill-me>`
- build（构建）: `<fill-me>`
- test（测试）: `<fill-me>`
- lint（代码检查）: `<fill-me>`

在运行相关的真实仓库命令之前，不得声称工作已完成。

## 硬性规则

- 不要为了修补流程问题而新增长期工件；优先强化现有 `AGENTS.md`、`plan.md`、`workflow.md`、review/evidence schema、subtask-pack 与 controller。
- 在冻结计划之前，必须将每个任务立足于当前代码库。
- 将 `DISCUSS -> PLAN` 视为最重 gate；在 draft plan 前，必须先澄清交付物、目标效果、必保要求、非目标、证据信号、写入边界、阶段顺序、审批点、删除 / 迁移条件与未决问题。
- `DISCUSS` 只有在“用户意图理解度 >= 95%”且“项目现实理解度 >= 95%”同时成立时才算完成；不得用“plan 已经写出来了”倒推 `DISCUSS` 已完成。
- 在计划评审通过之前不得实施。
- 在关闭评审通过之前不得归档。
- 保持 `plan.md` 仅关注目标事实。
- 保持 `workflow.md` 仅关注过程事实。
- 将评审和证据分开。
- 将子任务包视为衍生视图，绝不视为新的事实来源。
- 对于结构化写入、验证、归档、重新开启和包刷新，优先使用控制器命令。
- 当现实与文字描述冲突时，信任代码、测试、配置和运行时行为，而非过时的摘要。
- 不允许评审者角色修改业务代码。
- `plan-review` 必须完整核对任务要求层与 Goal truth 核心约束；World truth 只允许在显式记录抽样范围、依据与残余风险时抽样。
- 对迁移 / 删除 / 重组 / 重新分类类任务，review 必须回看原始 source materials，不能只看迁移后的输出物。
- 当 explorer / plan_reviewer / close_reviewer 的结果位于当前关键路径上时，主 agent 不得在结果返回前推进依赖该结果的清理、归档或完成性判断；单次 wait 超时不等于失败，等待时间是 20 mins。

## 最低关卡

- **理解 / 讨论 (Discuss / Understand)**：明确交付物、目标效果、非目标、必保要求、可授权决定、验收标准、阶段顺序、审批点、删除 / 迁移条件和未决问题，并达到用户 / 项目双 95% 理解度。
- **立足世界 (Ground in World)**：检查入口点、关键符号、现有测试、可复用机制和兼容性约束。
- **冻结目标事实 (Freeze Goal Truth)**：编写 `plan.md`，冻结交付物、效果、边界、不变量、验证 / 证据计划、回滚和子任务。
- **独立评审 (Independent Review)**：使用全新上下文进行计划评审和关闭检查。

## 角色

- `main`：编排、路由、决定调用哪个技能或角色，并推动任务状态流转。
- `explorer`：收集世界立足证据，不修改业务代码。
- `worker`：在定义的写入边界内精确实施一个子任务。
- `plan_reviewer`：独立评估计划的可执行性和立足依据。
- `close_reviewer`：独立评估交付就绪程度和偏差。
- `monitor`：等待、轮询并报告长时命令或 subagent 状态，不扩展任务范围。

## 控制器命令

使用这些命令作为确定性操作界面：

```bash
python .codex/tools/agentctl.py init-agentdocs
python .codex/tools/agentctl.py create-task --task-id T001 --title "任务标题"
python .codex/tools/agentctl.py update-current --task-id T001 --current-gate "Ground in World" --allowed-next-action "Freeze Goal Truth"
python .codex/tools/agentctl.py refresh-pack --task-id T001 --subtask S1
python .codex/tools/agentctl.py check-gate --task-id T001 --action implement
python .codex/tools/agentctl.py write-evidence --task-id T001 --subtask S1 --kind test --result PASS --purpose "已验证子任务" --command "<真实命令>"
python .codex/tools/agentctl.py write-review --task-id T001 --subtask S1 --review-type plan --decision PASS
python .codex/tools/agentctl.py archive --task-id T001
python .codex/tools/agentctl.py reopen --task-id T001 --trigger "scope-change" --reason "用户更改了验收标准"
```

## 技能路由

- 在进入 `$world-grounding` 或 `$freeze-plan` 之前，先按 `docs/agentic/spec/07-discuss-and-plan-contract.md` 收敛 DISCUSS 结论。
- 在起草或实质性修改计划之前使用 `$world-grounding`。
- 在将立足理解转化为 `plan.md` 时使用 `$freeze-plan`。
- 当包可能过期时，在实施或评审之前使用 `$refresh-subtask-pack`。
- 仅从 `plan_reviewer` 角色使用 `$plan-review`。
- 仅从 `worker` 角色使用 `$execute-subtask`。
- 在有意义的验证运行之后使用 `$evidence-capture`。
- 仅从 `close_reviewer` 角色使用 `$close-review`。
- 当范围变更、评审失败或必须恢复已归档工作时使用 `$reopen-fix`。

## “完成”的定义

- 相关子任务包是新鲜的。
- 实际运行了必要的仓库构建 / 测试 / lint 命令。
- 证据存在并指向真实的命令、文件或运行时产物。
- 当前阶段的独立评审已通过。
- `validate-refs` 通过。
- `workflow.md` 反映了真实的下一个合法动作。

## 如果指引内容增加

保持本文件实用性。将较长的原理或详细规则放在 `docs/agentic/` 或技能中，然后在此处链接它们。
