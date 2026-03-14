# Git / GitHub / Worktree Contract

> 目标：把 Git、GitHub、worktree 与多 agent 写入边界变成显式契约，避免 review、build、归档互相污染。

## 1. 基本定义

- **Plan Doc**：规格真源
- **Workflow Doc**：执行状态、证据、review 结论真源
- **Issue**：外部摘要与追踪镜像
- **Phase**：可独立验证、独立回填证据的阶段
- **Checkpoint Commit**：阶段边界冻结点

## 2. 执行型会话开始前的 Git 检查

任何执行型会话开始时，先做：

1. `git status --short --branch`
2. `git diff --stat`
3. `git diff --name-only`
4. 如有目标分支约定，再看 `git branch --show-current`

若当前不是 Git 仓库，在 workflow 中写 `git = N/A`。

## 3. Phase 与提交粒度

- 一个可独立验证的 phase，至少对应一个 checkpoint 或“可提交状态”
- phase 完成但未形成 checkpoint 时，workflow 必须写明原因
- 不允许把多个无关 phase 长时间混在一个脏工作区里

## 4. Worktree 强制场景

以下情况必须使用独立 worktree：

- 并行写入两个独立 phase
- reviewer 需要从干净状态复核 build 结果
- 需要保留当前脏工作区，同时启动新的写入型会话

## 5. Sub-agent 写入边界

- reviewer 只允许写 task-scoped review 产物与 controller 生成的 structured artifact；monitor 一律只读
- worker 只能写当前 phase 授权的文件边界
- explorer 只允许写 task-scoped findings / scratch / evidence / task-pack 工件
- 同一 worktree 中禁止两个写入型 sub-agent 并发运行
- close review 期间，主 worktree 进入只读收尾状态

## 6. Issue 使用规则

同时满足以下条件时，必须创建或复用 issue：

1. 当前目录是 Git 仓库
2. 仓库存在 GitHub remote
3. 团队日常通过 issue 跟踪开发
4. 任务不是纯本地探索

Issue 只保留：

- Summary
- Scope
- Acceptance Checklist
- Links
- Phase Checklist

Issue 不复制完整 plan 与执行流水账。

## 7. GitHub 命令权限边界

### 可直接运行

- `git status`
- `git diff`
- `git diff --stat`
- `git log --oneline --decorate -n N`
- `git show`
- `git branch --show-current`
- `gh issue view/list`
- `gh pr view/list`

### 需要确认

- `git add`
- `git commit`
- `git reset`
- `git rebase`
- `git push`
- `git worktree add/remove`
- `gh issue create/edit/comment`
- `gh pr create/edit/merge`
