# Codex / Claude Code 平台映射

## 1. 目标

本规范先定义系统本体，再映射到平台表面。

系统本体：
- Goal truth
- Process truth
- World truth
- Process evidence
- deterministic control plane
- rules / skills injection

平台表面：
- Codex 的 `AGENTS.md` / skills / `.codex/config.toml` / multi-agent / MCP
- Claude Code 的 `CLAUDE.md` / skills / subagents / hooks / memory

## 2. Codex 映射

### 2.1 AGENTS.md
用于 durable project guidance，应保持小而稳定。

在本规范中的职责：
- 仓库级宪法
- 红线与角色边界
- 指向 controller 与模板的入口

### 2.2 Skills
用于 reusable workflows 与 domain expertise。

在本规范中的职责：
- specialist workflow
- 任务特定方法注入
- review / implementation 的按需扩展

### 2.3 Multi-agents
用于并行或隔离上下文执行。

在本规范中的职责：
- fresh-context review
- exploration / implementation 分离
- 大任务并行探索或分工

### 2.4 Config / MCP
属于 runtime orchestration / external integration。

在本规范中的职责：
- 工具接入
- 运行时策略
- 角色配置

## 3. Claude Code 映射

### 3.1 CLAUDE.md
用于每次会话起始加载的持续指令。

在本规范中的职责：
- 项目级 always-on guidance
- coding standards / architecture guardrails
- review checklists 的薄入口

### 3.2 Skills
用于 on-demand knowledge 与 workflows。

### 3.3 Subagents
用于隔离上下文、角色分化与并行处理。

### 3.4 Hooks
用于自动化与规则执行；适合处理确定性前后置动作。

## 4. 平台无关规则

无论 Codex 还是 Claude Code，都应遵守：
- 文档不能覆盖代码世界
- review 必须尽量 fresh context
- skills / hooks 不能成为制度主权
- 派生 digest 可以生成，但不应升级为真相层
