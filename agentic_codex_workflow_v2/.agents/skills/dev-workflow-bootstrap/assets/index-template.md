# .agentdocs/index.md（入口地图 / Context Map）

> 目标：给新会话一个必要、稳定、可导航的入口，同时明确当前默认任务、长期记忆、证据目录和 scratch 目录。

## 0) 快速入口（新会话默认只读）

- 仓库入口：<repo entry points / README>
- 仓库规则：AGENTS.md
- 默认 active workflow：<当前无默认 active workflow>
- 架构知识：.agentdocs/architecture/index.md
- 开发洞察：.agentdocs/insights.md
- 状态机契约：docs/dev/contracts/high-entropy-state-machine.md
- 证据契约：docs/dev/contracts/evidence-bundle.md
- Sub-agent 契约：docs/dev/contracts/subagent-delegation.md
- Archive Index：.agentdocs/archive/index.md

## 1) Context Map（按需检索）

- 看架构：<模块边界 / 生命周期 / 依赖方向>
- 看契约：<API / schema / invariants / config>
- 看验证：<测试 / lint / build / repro 入口>
- 看历史坑：.agentdocs/insights.md / .agentdocs/archive/
- 看证据：.agentdocs/tasks/<task-id>/evidence/
- 看 scratch：.agentdocs/tasks/<task-id>/scratch/

## 2) 当前任务（SSOT）

<!-- DEFAULT = 新会话默认先读的 workflow；同一时间应尽量只有一个 DEFAULT -->
<!-- ACTIVE = 并行任务，仅在明确允许并行时保留 -->
<!-- NONE -->

## 3) Governance（需要用户拍板）

- 新依赖 / 新基础设施 / 新外部服务
- public API / 对外契约变化
- 数据迁移 / 删除 / 不可逆变更
- 安全策略例外 / 权限口径变化
- 架构边界突破或跨层写入

## 4) 长期记忆（可复用）

- architecture：.agentdocs/architecture/
- insights：.agentdocs/insights.md

## 5) 命名与目录约定

- task root：`.agentdocs/tasks/<task-id>/`
- workflow：`.agentdocs/tasks/<task-id>/workflow.md`
- plan：`.agentdocs/tasks/<task-id>/plan.md`
- evidence：`.agentdocs/tasks/<task-id>/evidence/`
- scratch：`.agentdocs/tasks/<task-id>/scratch/`
- archive：`.agentdocs/archive/<task-id>/`
