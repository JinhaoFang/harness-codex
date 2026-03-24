# AGENTS.md

## 角色定位

- 这是 `agentic_codex_runtime_v3_fusion` 目录自己的项目级 AGENTS，不是全局默认协议。
- 全局工作方式、开发流程、TDD / review / subagent 默认原则应放在 `~/.codex/AGENTS.md`。
- 本仓库提供了 `AGENTS.global.md` 作为全局模板。
- 若把本运行时复制到其他仓库，请重写本文件中的“命令 / 技术事实 / 架构映射 / 测试约定”，不要原样沿用。

## 使命

- 确保本仓库中的 runtime 设计、controller、skills、templates 与文档保持一致，可复现、可验证、可恢复。
- 这个文件只陈述当前仓库事实；完整 fusion 流程协议见全局模板与 `docs/agentic/*`。

## 仓库布局

- `AGENTS.md` = 当前仓库的项目级工作协议。
- `AGENTS.global.md` = `~/.codex/AGENTS.md` 的全局模板。
- `.codex/config.toml` = 项目 Codex 默认配置和角色注册表。
- `.codex/agents/*.toml` = Subagents 角色配置。
- `.agents/skills/*` = 阶段 / 方法 / 评审 skills。
- `.codex/tools/agentctl.py` = 确定性控制平面。
- `.codex/templates/*` = 生成 `plan/workflow/review/evidence/subtask-pack` 的模板。
- `.agentdocs/insight.md` = 跨任务可复用经验。
- `.agentdocs/architecture/` = 架构专题 SoT。
- `.agentdocs/tasks/<task-id>/...` = runtime artifacts 示例。
- `docs/agentic/spec/*` = 设计真相来源。
- `docs/agentic/reference/*` = 操作参考。
- `tests/test_agentctl_runtime.py` = controller regression tests。
- `.githooks/*` / `.github/workflows/*` = optional engineering guardrails。

## 仓库概览

- 该目录是一个可移植的 fusion runtime 包，不是业务应用。
- 主要内容是：stdlib Python controller、Markdown skills、TOML agent 配置、Markdown 规范文档、模板和回归测试。

```text
agentic_codex_runtime_v3_fusion/
|-- .codex/tools/agentctl.py        # stdlib-only controller
|-- .codex/templates/*              # generated artifact templates
|-- .codex/agents/*.toml            # subagent role definitions
|-- .agents/skills/*                # stage / method / review skills
|-- docs/agentic/spec/*             # design source of truth
|-- docs/agentic/reference/*        # operational reference
|-- tests/test_agentctl_runtime.py  # controller regression tests
|-- .githooks/*                     # optional repo guardrails
`-- .github/workflows/*             # optional CI guardrails
```

## 技术事实

- `.codex/tools/agentctl.py` 目前只使用 Python 标准库；不要轻易引入新的 Python 依赖。
- `.agents/skills/*` 主要承载阶段 / 方法 / 评审 guidance；`.codex/agents/*.toml` 承载 subagent 角色定义。
- `docs/agentic/spec/*` 是设计与边界的深层真相来源；`docs/agentic/reference/*` 是运行与操作参考。
- `.agentdocs/tasks/<task-id>/plan.md` / `workflow.md` / `reviews/*.json` / `evidence/*.json` / `subtask-packs/*.md` 体现了本 runtime 的 truth split。
- `.githooks/*` 和 `.github/workflows/security-checks.yml` 是 optional guardrails，不属于 runtime truth。

## 真实命令

- 安装：当前无单独安装步骤；controller 为 stdlib Python 脚本。
- 测试：`PYTHONDONTWRITEBYTECODE=1 python -m unittest tests.test_agentctl_runtime`
- 定向测试：`PYTHONDONTWRITEBYTECODE=1 python -m unittest tests.test_agentctl_runtime.AgentctlRuntimeTests`
- diff 健康检查：`git diff --check`
- 安装 repo hooks：`bash .githooks/install.sh`
- 当前无单独 `build` 或 `lint` 入口；若只改文档 / 配置，至少运行相关测试或 `git diff --check`。

## 项目特定测试约定

- `tests/test_agentctl_runtime.py` 会把整个 runtime 目录复制到临时目录，再在副本中运行 controller 命令。
- 这组测试验证的是生成物和状态迁移，不是直接 monkeypatch controller 内部实现。
- 修改 controller、template、pack freshness、review writeback、metadata sync 时，应优先补这类 artifact-driven regression tests。
- 测试里的 world-grounded anchors 应继续指向仓库真实文件，而不是 `.agentdocs/*`。

## 联动修改规则

- 修改 `.codex/tools/agentctl.py` 或 `.codex/templates/*` 时，通常要同时检查：
  - `tests/test_agentctl_runtime.py`
  - `docs/agentic/reference/controller-commands.md`
  - `docs/agentic/reference/controller-readme.md`
- 修改 `.agents/skills/*` 的流程语义时，通常要同时检查：
  - 对应的 `.codex/agents/*.toml`
  - `README.md`
  - 必要时更新相关 spec / reference 文档
- 修改 subagent 路由、rereview 规则、TDD 规则时，优先同步：
  - `.agents/skills/*`
  - `.codex/agents/*.toml`
  - `README.md`
- 修改 `.githooks/*` 时，保持 `.githooks/README.md` 与 `.github/workflows/security-checks.yml` 一致，避免本地和 CI 规则漂移。

## 项目级 Runtime 摘要

- 本文件只保留短摘要；完整 runtime 规则不要继续堆在这里。
- 本 runtime 的核心不变量仍然是：
  - `plan.md` = Goal truth
  - `workflow.md` = Process truth
  - `reviews/*.json` = review judgment
  - `evidence/*.json` = process evidence
  - `subtask-pack` = derived view
  - 代码 / 测试 / 运行时行为 = world truth
- `plan-review` / `close-review` verdict 必须通过 `request-review -> submit-review` 落盘，主 agent 不得代替 reviewer 提交 verdict。
- `Task close-ready = YES` 之前不得归档；单个 subtask close review PASS 不等于整个 task 可归档。
- 日常入口先看：
  - `docs/agentic/reference/runtime-overview.md`
  - `docs/agentic/reference/controller-commands.md`
- 需要理解深层设计边界时看：
  - `docs/agentic/spec/00-constitution.md`
  - `docs/agentic/spec/01-truth-model.md`
  - `docs/agentic/spec/03-runtime-and-review.md`
  - `docs/agentic/spec/07-discuss-and-plan-contract.md`
- 需要理解具体阶段 / 方法 / 评审行为时，看：
  - `.agents/skills/*`
  - `.codex/agents/*.toml`

## 本仓库的额外约束

- 不要把新的长期状态层塞进本仓库；优先强化现有 controller、templates、skills、spec/reference docs 和 tests。
- 不要把 `README.md` 或聊天摘要当成设计真相；设计判断回到 `docs/agentic/spec/*`，运行判断回到 controller / tests / artifacts。
- 不要声称完成，除非已经运行与改动匹配的真实命令，并让文档与测试保持一致。
