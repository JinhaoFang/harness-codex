# Agentic Codex Runtime v3

[English](README.md) | **中文**

> 让 AI 编程 Agent 的开发过程变得**可复现、可验证、可回滚、可断点重续、可持续演进、上下文不腐烂**。

## 这是什么？

一个面向 AI 编程 Agent（Codex、Claude 等）的确定性运行时框架。它提供：

- **真相模型** — 清晰区分目标真相（`plan.md`）、过程真相（`workflow.md`）和世界真相（代码/测试/运行时）。
- **控制器** — CLI 工具（`agentctl.py`）执行关卡检查、管理状态转换、产出可验证的制品。
- **技能体系** — 可插拔的阶段/方法/评审技能（world-grounding、freeze-plan、execute-subtask、tdd、plan-review、close-review 等）。
- **子 Agent 协作** — 结构化交接契约，支持多 Agent 协作，含自举和上下文恢复。

## 仓库结构

```
codex_harness/
├── agentic_codex_runtime_v3_fusion/   # 主运行时包（复制到目标仓库根目录使用）
│   ├── AGENTS.md                       # 项目级 Agent 协议
│   ├── AGENTS.global.md                # 全局模板（~/.codex/AGENTS.md）
│   ├── .codex/
│   │   ├── config.toml                 # Codex 配置与 Agent 注册表
│   │   ├── agents/                     # 子 Agent 角色定义
│   │   ├── tools/agentctl.py           # 确定性控制面
│   │   └── templates/                  # Plan、workflow、evidence、review 模板
│   ├── .agents/skills/                 # 运行时技能
│   ├── .agentdocs/                     # 任务工作区（SSOT）
│   ├── .github/workflows/              # CI 护栏
│   └── docs/agentic/spec/              # 设计规格文档
└── docs/                               # 参考资料 & 迁移指南
```

## 快速开始

### 前置条件

- Python 3.9+
- Git
- AI 编程 Agent（OpenAI Codex CLI、Claude Code 或类似工具）

### 安装到目标仓库

1. 将运行时包复制到项目根目录：

   ```bash
   cp -r agentic_codex_runtime_v3_fusion/* /path/to/your-project/
   ```

2.（可选）设置全局协议：

   ```bash
   cp agentic_codex_runtime_v3_fusion/AGENTS.global.md ~/.codex/AGENTS.md
   ```

3. 初始化运行时工作区：

   ```bash
   python .codex/tools/agentctl.py init-agentdocs
   ```

4. 创建第一个任务：

   ```bash
   python .codex/tools/agentctl.py create-task --slug my-first-task --title "我的第一个任务"
   ```

5.（可选）启用仓库护栏：

   ```bash
   bash .githooks/install.sh
   ```

### 推荐工作循环

```
Discuss → world-grounding → freeze-plan → refresh-subtask-pack
  →（可选：plan-eng-review）→ plan-review
  → execute-subtask（代码任务需叠加 tdd）
  → evidence-capture → close-review → archive
```

## 架构原则

| 原则 | 说明 |
|------|------|
| **真相分离** | `plan.md` = 目标，`workflow.md` = 过程，代码/测试 = 世界 |
| **确定性控制** | `agentctl.py` 处理状态转换；Agent 负责判断 |
| **可插拔技能** | 核心阶段 + 可选方法/评审技能 |
| **独立评审** | 评审使用全新上下文，禁止自审 |
| **TDD 作为方法** | 所有代码开发任务的必选方法叠加层 |
| **子 Agent 自举** | 子 Agent 从 `.agentdocs/*` 自行重建上下文 |

## 文档

- [设计规格文档](agentic_codex_runtime_v3_fusion/docs/agentic/spec/) — 编号规格文档（00-08）
- [控制器参考](agentic_codex_runtime_v3_fusion/docs/agentic/reference/) — 命令参考与概览
- [Fusion 决策清单](agentic_codex_runtime_v3_fusion/docs/agentic/spec/08-fusion-decision-checklist.md) — 哪些模块是核心、哪些是可选
- [参考资料](docs/references/) — Agent 工程指南与设计参考

## 核心技能

| 技能 | 阶段 | 说明 |
|------|------|------|
| `world-grounding` | 立足 | 将任务锚定到当前代码库现实 |
| `freeze-plan` | 计划 | 编写并冻结 `plan.md` 作为目标真相 |
| `refresh-subtask-pack` | 计划 | 生成派生子任务包 |
| `plan-review` | 评审 | 独立计划评审裁决 |
| `execute-subtask` | 执行 | 实现已立足的子任务 |
| `evidence-capture` | 执行 | 捕获验证证据 |
| `close-review` | 评审 | 独立关闭评审裁决 |
| `reopen-fix` | 修复 | 附带范围变更原因重新打开 |

## 可选模块

- `tdd` — 测试驱动开发方法叠加层
- `subagent-bootstrap` — 子 Agent 自上下文重建
- `plan-eng-review` — Owner 侧工程方案挑战（非关卡）
- `worktree-isolation` — 在隔离的 Git Worktree 中并行执行
- `session-recovery` — 跨会话上下文恢复
- `github-collaboration` — 通过 `gh` CLI 实现 Issue/PR 可追溯性
- `contract-artifacts` — 长期复用的业务/API/UI 合同

## 参与贡献

请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE)
