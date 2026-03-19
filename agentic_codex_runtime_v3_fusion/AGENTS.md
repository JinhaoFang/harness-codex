# AGENTS.md

## 使命

- 确保编码智能体的工作可复现、可验证、可逆、可恢复且可演进。
- 将确定性正确性下沉到控制器中；将概率性工作保留在澄清、规划、评审和实施判断中。

## 仓库布局

- `AGENTS.md` = Codex 自动加载的仓库工作协议。
- `.codex/config.toml` = 项目 Codex 默认配置和角色注册表。
- `.codex/agents/*.toml` = 用于 Subagents（子代理协作）的 custom agents 角色配置（需 `name` / `description` / `developer_instructions`）。
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

- **理解 / 讨论 (Discuss / Understand)**：通过结构化澄清循环明确交付物、目标效果、非目标、必保要求、可授权决定、验收标准、阶段顺序、审批点、删除 / 迁移条件和未决问题，并达到用户 / 项目双 95% 理解度。
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
- 子代理默认启用但需要显式触发；每个子代理独立执行与消耗 token。
- 子代理继承父会话的沙箱策略；spawn 时会重新应用父会话的运行时覆盖（例如 approvals/`--yolo` 变更）。
- 交互式 CLI 可用 `/agent` 查看与切换线程；批准请求可能从非活动线程浮出。

## 控制器命令

使用这些命令作为确定性操作界面：

```bash
python .codex/tools/agentctl.py init-agentdocs
python .codex/tools/agentctl.py create-task --slug fastapi-backend-audit --title "FastAPI backend audit"
# 记下 create-task 输出里的 <task-id>；正常场景优先 --slug，--task-id 只作显式 override
python .codex/tools/agentctl.py update-current --task-id <task-id> --current-gate "Ground in World" --allowed-next-action "Freeze Goal Truth"
python .codex/tools/agentctl.py refresh-pack --task-id <task-id> --subtask S1
python .codex/tools/agentctl.py check-gate --task-id <task-id> --action implement
python .codex/tools/agentctl.py write-evidence --task-id <task-id> --subtask S1 --kind test --result PASS --purpose "已验证子任务" --command "<真实命令>"
python .codex/tools/agentctl.py write-review --task-id <task-id> --subtask S1 --review-type plan --decision PASS
python .codex/tools/agentctl.py archive --task-id <task-id>
python .codex/tools/agentctl.py reopen --task-id <task-id> --trigger "scope-change" --reason "用户更改了验收标准"
```
