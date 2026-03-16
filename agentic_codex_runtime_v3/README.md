# Agentic Codex Runtime v3

一个 Codex 原生的启动器/运行时，将 v3 智能体工程设计转化为可运行的仓库布局。

## 该软件包提供的内容

- 一个简洁的根目录 `AGENTS.md`，Codex 可自动加载。
- 项目级 `.codex/config.toml`，包含多智能体角色连接配置。
- 位于 `.codex/agents/` 的精细化角色配置。
- 位于 `.agents/skills/` 的仓库技能。
- 位于 `.codex/tools/agentctl.py` 的确定性控制器。
- 位于 `.agentdocs/` 下的运行时事实存储。
- 位于 `docs/agentic/` 下的 v3 规范和迁移说明。

## 核心设计

- `plan.md` 存储**目标事实**。
- `workflow.md` 存储**过程事实**。
- 代码 / 测试 / 运行时行为存储**世界事实**。
- `reviews/*.json` 存储评审结论。
- `evidence/*.json` 存储过程证据。
- `subtask-packs/*.md` 是衍生摘要，而非新的事实层。

## 快速开始

1. 将此软件包复制到您希望 Codex 运行的仓库根目录。
2. 编辑 `AGENTS.md` 中的 **Local project commands**（本地项目命令）部分，使构建 / 测试 / lint 命令与目标仓库匹配。
3. 根据需要调整 `.codex/config.toml`，配置审批策略、沙箱和角色深度。
4. 初始化运行时存储：

   ```bash
   python .codex/tools/agentctl.py init-agentdocs
   ```

5. 创建任务框架：

   ```bash
   python .codex/tools/agentctl.py create-task --task-id T001 --title "示例任务"
   ```

   `create-task` 只会创建 skeleton，不会自动生成可用于 review / implementation 的 pack。

6. 从仓库根目录启动 Codex。

## 推荐工作循环

1. 主智能体明确意图并初始化任务。
2. 主智能体使用 `world-grounding`，并在有用时使用 `explorer` 角色。
3. 主智能体通过 `freeze-plan` 编写 `plan.md`。
4. 主智能体刷新子任务包。
5. 主智能体请求独立的 `plan_reviewer` 进行评审。
6. 仅在计划评审通过后，`worker` 才会执行子任务。
7. Worker 记录证据。
8. 主智能体请求独立的 `close_reviewer` 进行评审。
9. 仅在关闭评审通过后进行归档。

## 重要实现决策

- `agentctl.py` 始终保持为脚本，而非技能。
- 技能解释调用控制器的**时机和方式**；它们不取代确定性控制。
- 评审者角色默认为只读。
- `AGENTS.md` 保持简短实用；更深层的原理位于 `docs/agentic/` 中。
