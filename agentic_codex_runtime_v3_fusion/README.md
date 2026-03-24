# Agentic Codex Runtime v3 Fusion

以 `agentic_codex_runtime_v3` 为地基，吸收 `coding-agent-flow` 中少量高价值、低耦合的工程设计，形成一个 **runtime core + optional skills/modules** 的融合包。

## 核心原则

- `plan.md` 仍然只承载 Goal truth
- `workflow.md` 仍然只承载 Process truth
- review / evidence 仍然分离
- `agentctl.py` 仍然是确定性控制面，而不是 GitHub orchestration layer
- TDD、工程方案挑战、外部协作、worktree、hooks、长期合同文档都作为 **可拔插增强层** 存在

## 包内组成

### Runtime core
- `AGENTS.global.md`（`~/.codex/AGENTS.md` 全局模板）
- `AGENTS.md`
- `.codex/config.toml`
- `.codex/agents/*`
- `.codex/tools/agentctl.py`
- `.codex/templates/*`
- `.agents/skills/*`（含 core stage skills，以及可叠加的方法 / 评审 skills）
- `.agentdocs/*`
- `docs/agentic/*`

### Optional method / review skills
- `.agents/skills/subagent-bootstrap`
- `.agents/skills/tdd`
- `.agents/skills/plan-eng-review`

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
2. 若希望把 fusion 默认流程作为全局协议，先将 `AGENTS.global.md` 拷贝到 `~/.codex/AGENTS.md`。
3. 重写项目级 `AGENTS.md`，填入目标仓库的真实命令、技术栈、架构分层和测试约定。
4. 初始化 runtime:

   ```bash
   python .codex/tools/agentctl.py init-agentdocs
   ```

5. 创建任务骨架：

   ```bash
   python .codex/tools/agentctl.py create-task --slug sample-task --title "示例任务"
   ```

   `fusion` 默认推荐使用 `--slug`。controller 会自动生成 `YYYYMMDD-HHMM[-NN]-<slug>` 格式的 task id，并在命令输出中显示；`--task-id` 仅用于迁移或显式 override。

6. 只有在需要 repo guardrails 时，再启用 git hooks：

   ```bash
   bash .githooks/install.sh
   ```

7. 需要了解哪些模块是 core、哪些是 optional，先读：
   - `docs/agentic/spec/08-fusion-decision-checklist.md`
   - `docs/agentic/reference/optional-modules.md`

## 推荐工作循环

1. `Discuss`
2. `world-grounding`
3. `freeze-plan`
4. `refresh-subtask-pack`
5. optional `plan-eng-review`
6. `plan-review`
7. `execute-subtask`
8. `tdd` for any code-bearing development subtask
9. `evidence-capture`
10. `close-review`
11. `archive`

说明：
- `plan-eng-review` 是 owner-side 的工程方案挑战，不替代 formal `plan-review`。
- `plan-review` / `close-review` 都应通过 controller 的 `request-review -> reviewer submit-review` 流程完成，避免主会话直接补写 verdict。
- subagent 默认先走 `subagent-bootstrap`：父 agent 只传 task id / subtask id / request id / objective / extra focus，角色自己从 `.agentdocs/*` 与当前代码世界重建上下文。
- `worker` 适合承接已经 grounded、写入边界清晰、且不再是极小修补的实现子任务；这类实现默认优先交给 `worker`，而不是继续挤在主会话里。
- 所有 rereview 都应重新做 full-scope review；上轮 findings 只作为回归检查清单。
- `tdd` 是实现方法 skill，不是 runtime gate，也不与 `execute-subtask` 深度绑定；但凡属于 code-bearing development task，实施时都必须叠加 `tdd`。
- `close-review` 仍然按 subtask 产生 review artifact，但归档前必须由 controller 聚合得到 task 级 `Task close-ready = YES`。

只有当任务确实需要时，再注入：
- `subagent-bootstrap`
- `tdd`
- `plan-eng-review`
- `worktree-isolation`
- `session-recovery`
- `github-collaboration`
- `contract-artifacts`
