# Evidence Bundle Contract

> Evidence 的目标不是“证明自己说过跑了测试”，而是让独立 reviewer 能复核你到底跑了什么、在哪里跑的、当时结果是什么。额外强调：**evidence 是 task-scoped 工件**，应随任务一起归档，而不是长期漂在热路径。

## 1. 目录

### 推荐路径

每个新任务使用：`.agentdocs/tasks/<task-id>/evidence/`

建议命名：

- `E01-<phase>-<label>.txt`
- `E01-<phase>-<label>.json`

### 兼容 legacy

旧路径 `.agentdocs/evidence/<task-id>/` 继续可读；迁移时，不强制重写旧 evidence。

workflow / plan / task pack 中的 `Evidence Ref` 必须指向真实路径。

`Evidence Ref` 与 `Review Ref` 是两种不同类型的引用：

- `Evidence Ref` 只指向事实证据
- `Review Ref` 只指向评审结论
- `reviews/*.json` 不得充当 `Evidence Ref`

## 2. 最低字段

每个 evidence bundle 至少包含：

- `evidence_id`
- `phase`
- `purpose`
- `command`
- `cwd`
- `ran_at`
- `exit_code`
- `result`（`PASS / FAIL / DEGRADED`）
- `output_path` 或 `output_excerpt`
- `related_artifacts`
- `notes`
- `reviewer_recheck`（若已被 reviewer 抽样）

## 3. workflow / plan 引用规则

`Evidence Ref` 不允许只写：

- `见上文`
- `pytest -q`
- `reviewer PASS`
- `reviews/plan-review-r1.json`
- `reviews/close-review-r1.json`

`Evidence Ref` 必须写成：

- workflow / plan 中的 evidence section 标识
- `.agentdocs/.../evidence/<id>.json` 真实路径

## 4. DEGRADED 规则

当标准 gate 无法执行时，bundle 里必须额外包含：

- `why`
- `instead`
- `to_run_later`

没有这三项，`DEGRADED` 无效。

## 5. reviewer 复核

- `PLAN_REVIEW` 检查 evidence 设计是否可复核
- `CLOSE_REVIEW` 抽样复跑或抽样读取 bundle
- `Final Status = PASS` 时，至少有一条 evidence 被 close reviewer 复核

## 6. sub-agent 自描述要求

如果 sub-agent 产出了 evidence，它在回复中必须至少汇报：

- `Evidence Produced`
- `Verification Run`
- `Next Legal Action`

这让 main agent 不需要再手动打开 evidence 目录才能知道结果。

## 7. 推荐工具：evidence_run（自动生成 bundle）

```bash
python .agents/skills/dev-agentdocs-check/scripts/evidence_run.py   --workflow .agentdocs/tasks/<task-id>/workflow.md   --phase P1   --cwd .   -- pytest -q
```

你仍然需要在 workflow / plan 中引用这些 `.json` 路径（并补齐 purpose / notes / related_artifacts 等语义字段）。

若使用 controller 直接写 evidence：

```bash
python .codex/workflow/taskctl.py record-evidence \
  --task-root .agentdocs/tasks/<task-id> \
  --workflow .agentdocs/tasks/<task-id>/workflow.md \
  --evidence-id E01-P1-smoke \
  --phase P1 \
  --purpose "..." \
  --command "pytest -q" \
  --result DEGRADED \
  --why "..." \
  --instead "..." \
  --to-run-later "..."
```
