# Agentic Codex Workflow

> 让 AI 编程 Agent 的开发过程变得**可复现、可验证、可回滚、可断点重续、可持续演进、上下文不腐烂**。

## 概述

Agentic Codex Workflow 是一套面向 AI Coding Agent（如 Claude Code、OpenAI Codex）的多 Agent 协作工作流框架。它通过严格的**状态机控制**和**双平面模型**，确保开发任务从理解、规划、实现到归档的全流程可控与可审计。

### 核心设计原则

- **控制平面不能覆盖事实平面**：文档约束动作，代码/测试/运行结果反映真实状态
- **理解度未达 95% 禁止开工**：目标、范围、验收、风险任一不明确即停止
- **结构化写回优先**：review/evidence/event 通过脚本完成，避免手工维护。脚本要做到一条命令能更新到所有相关的结构化内容，手工维护可能会遗漏
- **Task Pack 是执行入口**：所有 sub-agent 必须基于 task pack 派发
- **上下文恢复**：当新开会话/上下文窗口重置时，进度文件+git 历史=完全恢复

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Policy Layer (AGENTS.md)                │
│         状态机 · 真源优先级 · Task Pack 规范                  │
├─────────────────────────────────────────────────────────────┤
│                  Orchestration Layer (.codex/)              │
│         角色配置 · 调度决策 · Review Mode                    │
├─────────────────────────────────────────────────────────────┤
│                 Capability Layer (.agents/skills/)          │
│         Router · Specialist · Tooling Skills               │
├─────────────────────────────────────────────────────────────┤
│                     State Layer (.agentdocs/)               │
│         workflow.md · plan.md · task-packs · reviews        │
├─────────────────────────────────────────────────────────────┤
│                   Controller Layer (taskctl.py)             │
│         目录落位 · 模板渲染 · 校验 · 结构化写入              │
└─────────────────────────────────────────────────────────────┘
```

## Skills 模块

| Skill                          | 用途                                                       |
| ------------------------------ | ---------------------------------------------------------- |
| `dev-workflow-router`          | 任务总入口，判断 entropy、状态机位置、是否进入 multi-agent |
| `dev-workflow-bootstrap`       | 初始化或恢复 `.agentdocs/tasks/<task-id>/` 工作台          |
| `dev-write-plan`               | 起草和冻结实施计划                                         |
| `dev-review-plan`              | 计划评审                                                   |
| `dev-build-phase`              | 实现阶段执行                                               |
| `dev-close-review`             | 交付前评审                                                 |
| `dev-final-review-and-archive` | 最终评审与归档                                             |
| `dev-gh-create-issue`          | GitHub Issue 创建                                          |
| `dev-memory-router`            | 记忆路由决策                                               |
| `dev-structured-writeback`     | 结构化写回（review/evidence/event）                        |
| `dev-review-router`            | 评审路由                                                   |
| `dev-agentdocs-check`          | 工作台状态检查                                             |

## High-Entropy 状态机

```
DISCUSS → ALIGN_PROOF → BOOTSTRAP → ISSUE_SYNC → PLAN_DRAFT → PLAN_REVIEW → BUILD → CLOSE_REVIEW → ARCHIVE
```

**硬门禁：**

- `ALIGN_PROOF` 未完成 → 禁止写 plan
- `PLAN_REVIEW = PASS` 前 → 禁止进入 BUILD
- `CLOSE_REVIEW = PASS` 前 → 禁止进入 ARCHIVE

## 目录结构

```
.
├── agentic_codex_workflow_v2/
│   ├── AGENTS.md                    # 仓库工作协议（宪法级）
│   ├── .agents/
│   │   └── skills/                  # 能力模块
│   └── docs/
│       └── dev/
│           ├── contracts/           # 契约定义
│           └── system/              # 系统边界
├── references/                      # 工程参考文档
│   ├── agent-engineering-guide.md
│   ├── designing-agent-tools.md
│   └── ...
└── .agentdocs/                      # 运行时状态（生成）
    ├── index.md
    ├── tasks/<task-id>/
    │   ├── workflow.md
    │   ├── plan.md
    │   ├── task-packs/
    │   ├── reviews/
    │   └── evidence/
    └── archive/
```

## 快速开始

1. **配置项目**：将 `AGENTS.md` 复制到你的项目根目录
2. **初始化工作台**：调用 `dev-workflow-bootstrap` skill
3. **提交任务**：通过 `dev-workflow-router` 路由到正确的处理流程
4. **按状态机推进**：遵循 High-Entropy 循环完成开发

## 参考

- `docs/dev/contracts/` - 详细契约定义（状态机、Task Pack、Evidence 等）
- `docs/` - Agent 工程指南与最佳实践

## License

MIT
