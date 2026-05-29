# Coding Agent Project Harness

[English](README.md) | **中文**

> 让 AI 编程 Agent 的开发过程变得**可复现、可验证、可回滚、可断点重续、可持续演进、上下文不腐烂**。

## 这是什么？

一个便携式实现脚手架，用于在真实代码库中使用 Codex、Claude Code 或类似编程 Agent，而不会将 harness 变成第二个产品。

实现 intentionally 采用**控制器轻量但不变量重量**的设计：

- 代码仓库和运行时是项目真相的来源
- 非平凡工作从工作单元合约开始
- Agent 工作受显式写入和风险边界约束
- 完成需要新证据或豁免
- 评审裁决与证据收据分离
- 交接和状态从权威制品生成，而非聊天摘要
- 每个非平凡机制都有目的、验证方法、成本和移除条件

## 仓库结构

```
codex_harness/
├── harness-implementation-project-module3A/  # 主 harness 实现（复制到目标仓库）
│   ├── README.md                              # 项目概览
│   ├── CLAUDE.md                              # Claude Code 项目指南
│   ├── AGENTS.md                              # Codex 项目指南
│   ├── .harness/                              # 工作单元生命周期、证据、评审
│   ├── harness/cli/harnessctl.py              # 控制器 CLI
│   ├── harness/hooks/                         # 确定性守护脚本
│   ├── harness/schemas/                       # 制品的 JSON Schema
│   ├── harness/templates/                    # 合约、交接、评审模板
│   ├── skills/                                # 平台中立技能目录
│   ├── .claude/                               # Claude Code 适配器示例
│   ├── .codex/                                # Codex 适配器示例
│   └── docs/harness/                          # 详细生命周期文档
├── docs/                                      # 参考资料
│   ├── coding_agent_project_harness_standard_v0.6.2.md
│   └── harness_engineering_tutorial_v0.6.0.md
└── reference_project/                          # 参考实现
```

## 快速开始

### 前置条件

- Python 3.9+
- Git
- AI 编程 Agent（OpenAI Codex CLI、Claude Code 或类似工具）

### 安装到目标仓库

使用 `scripts/adopt.py` 仅复制目标仓库需要的层级：

```bash
cd harness-implementation-project-module3A
python3 scripts/adopt.py /path/to/repo --profile thin
```

采用配置：

| 配置 | 说明 |
|------|------|
| **thin** | 便携式入口文件、核心控制器、hooks、schemas、templates、核心文档、最小技能集 |
| **controlled** | thin + 测试、CI 示例、完整生命周期技能集 |
| **codex** | controlled + Codex 平台适配器 |
| **claude** | controlled + Claude Code 平台适配器 |
| **full** | 所有默认运行时示例 |

### 快速工作流

```bash
# 初始化
python3 harness/cli/harnessctl.py init

# 创建工作单元
python3 harness/cli/harnessctl.py new --id WU-001 --title "修复登录重定向" --type bugfix --risk medium

# 检查状态
python3 harness/cli/harnessctl.py status --id WU-001

# 实现后
python3 harness/cli/harnessctl.py evidence --id WU-001 --claim EV1 --type test --result pass --command "pytest tests/test_login.py" --command-log-ref ".harness/work-units/active/WU-001/evidence/artifacts/pytest-login.log"
python3 harness/cli/harnessctl.py validate --id WU-001 --strict
python3 harness/cli/harnessctl.py check --id WU-001 --gate verification
```

## 核心循环

```
澄清 -> 工作单元合约 -> 上下文路由 -> 计划评审（如需）-> 实现 -> 证据 -> 验证 -> 关闭评审 -> CI 关卡 -> 交接或归档
```

## 采用配置

| 目标配置 | 优先复制 | 按需添加 |
|---|---|---|
| 轻量本地 Harness | `AGENTS.md`、`CLAUDE.md`、`docs/harness/README.md`、`harness/cli/harnessctl.py`、选定技能 | hooks、评审 agents |
| 受控仓库 Harness | 轻量 + `.harness` 生命周期、证据收据、范围检查、关闭评审工作流 | CI 关卡、路径策略 |
| 风险感知 Harness | 受控 + 豁免模型、人工关卡、deny/ask 权限、边界 hooks | 策略即代码、安全评审 |
| 规模化多 Agent Harness | 风险感知 + issue/PR 纪律、最小 worker/reviewer 子 agents、worktrees、HEB 评估 | 调度器/编排器 |

## 文档

- [Harness 标准 (v0.6.2)](docs/coding_agent_project_harness_standard_v0.6.2.md) — 核心标准、能力模型和参考配置
- [Harness 工程教程 (v0.6.0)](docs/harness_engineering_tutorial_v0.6.0.md) — 为什么、如何评估、如何采用、如何避免过度工程
- [Harness 实现指南](harness-implementation-project-module3A/docs/harness/README.md) — 详细生命周期文档

## 核心技能

| 技能 | 用途 |
|------|------|
| `harness-clarify` | 实现前澄清模糊工作 |
| `harness-spec` | 创建/锁定/修正工作单元合约 |
| `harness-ground` | 建立仓库真相和上下文 |
| `harness-tdd` | 行为优先的测试驱动开发 |
| `harness-evidence` | 捕获声明相对的证据收据 |
| `harness-review` | 计划、关闭、风险、安全或架构评审 |
| `harness-github` | GitHub issues、分支、提交、PR 集成 |
| `harness-handoff` | 生成可恢复的交接 |
| `harness-compound` | 将失败转化为持久资产或修剪决策 |
| `harness-waiver` | 创建范围化人工批准的豁免 |

## 这个项目不是什么

它不是通用 Agent 平台、强制性目录标准或项目特定工程判断的替代品。它提供了一组可执行的不变量和适配器示例，可以根据真实失败痕迹进行复制、移除或加厚。

## 参与贡献

请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[MIT](LICENSE)
