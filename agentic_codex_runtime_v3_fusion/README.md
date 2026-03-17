# Agentic Codex Runtime v3 Fusion

以 `agentic_codex_runtime_v3` 为地基，吸收 `coding-agent-flow` 中少量高价值、低耦合的工程设计，形成一个 **runtime core + optional modules** 的融合包。

## 核心原则

- `plan.md` 仍然只承载 Goal truth
- `workflow.md` 仍然只承载 Process truth
- review / evidence 仍然分离
- `agentctl.py` 仍然是确定性控制面，而不是 GitHub orchestration layer
- 外部协作、worktree、hooks、长期合同文档都作为 **可拔插模块** 存在

## 包内组成

### Runtime core
- `AGENTS.md`
- `.codex/config.toml`
- `.codex/agents/*`
- `.codex/tools/agentctl.py`
- `.codex/templates/*`
- `.agents/skills/*`（含 core skills）
- `.agentdocs/*`
- `docs/agentic/*`

### Optional modules
- `.githooks/*`
- `.github/workflows/security-checks.yml`
- `.agents/skills/contract-artifacts`
- `.agents/skills/github-collaboration`
- `.agents/skills/session-recovery`
- `.agents/skills/worktree-isolation`
- `docs/contracts/*`

## 这次融合没有做的事

- 没有迁移 `harness-tasks.json` / `harness-progress.txt`
- 没有把 GitHub issue/PR 设为 runtime source of truth
- 没有把 `docs/prd|api|ui` 设为每个 task 的默认前置文档
- 没有把 `agentctl.py` 扩张成厚流程编排器

## 快速开始

1. 将此包复制到目标仓库根目录。
2. 编辑 `AGENTS.md` 的本地项目命令。
3. 初始化 runtime:

   ```bash
   python .codex/tools/agentctl.py init-agentdocs
   ```

4. 创建任务骨架：

   ```bash
   python .codex/tools/agentctl.py create-task --task-id T001 --title "示例任务"
   ```

5. 只有在需要 repo guardrails 时，再启用 git hooks：

   ```bash
   bash .githooks/install.sh
   ```

6. 需要了解哪些模块是 core、哪些是 optional，先读：
   - `docs/agentic/spec/08-fusion-decision-checklist.md`
   - `docs/agentic/reference/optional-modules.md`

## 推荐工作循环

1. `Discuss`
2. `world-grounding`
3. `freeze-plan`
4. `refresh-subtask-pack`
5. `plan-review`
6. `execute-subtask`
7. `evidence-capture`
8. `close-review`
9. `archive`

只有当任务确实需要时，再注入：
- `worktree-isolation`
- `session-recovery`
- `github-collaboration`
- `contract-artifacts`
