# Multi-Agent Inheritance Contract (V3)

> V3 采用“共享基线 + 角色增量覆盖”模型，避免多 agent 既完全同构、又完全失控。

## 1. 默认共享的基线
- 项目级 / 目录级 AGENTS
- 通用 skills
- 通用 MCP
- approval / sandbox 的会话级基线
- 当前 task pack 中的任务约束

## 2. 允许按角色覆盖
- `developer_instructions`
- `model`
- `reasoning effort`
- `sandbox mode`
- 专属 skills
- 专属 MCP

## 3. 设计原则
1. 共享任务事实，避免角色各自发明世界观
2. 角色只覆盖“做事方式”，不覆盖“任务真源”
3. explorer / reviewer / worker 的输出契约必须不同
4. 多 agent 稳定性来自任务接口设计，而不是角色名称本身
