# 验证门禁与证据规范（Python / Node）

## 1) 通用规则
- Gate = 必须通过的最小验证集合；未满足 Gate 不得宣布完成
- Gate 命令应来自项目约定（scripts / Makefile / CI 入口），不要临时猜命令
- Evidence Ref 必须指向 `.agentdocs/tasks/<task-id>/evidence/` 下的真实 bundle
- 仅写“pytest -q”或“reviewer PASS”不再算有效证据

## 2) Evidence Bundle 最低字段
每条 evidence 至少包含：
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

## 3) 降级协议（DEGRADED）
无法执行标准 Gate 时，必须额外记录：
- `why`
- `instead`
- `to_run_later`

## 4) Python 建议 Gate
- Format：`uv run ruff format .`
- Lint：`uv run ruff check .`
- Test：`uv run pytest -q`

## 5) Node 建议 Gate
按 lockfile 决定包管理器；以 root scripts 为唯一真相：
- lint
- typecheck（如有）
- test
- build（如改动影响构建时）

## 6) 行为类 / 文档类任务
当任务不适合自动化测试时，至少提供：
- checklist
- 独立 reviewer 结论
- 产物路径
- 复核命令或复核步骤
- evidence bundle

## 7) Preflight（流程一致性硬信号）

除了项目的测试/构建 gate（pytest、lint、build 等），还建议在进入 BUILD / ARCHIVE 前跑一次 `.agentdocs` 的一致性检查：

```bash
python .agents/skills/dev-agentdocs-check/scripts/agentdocs_check.py \
  --workflow <workflow> --mode all --intent build
```

这个 preflight 的作用是：
- 把“build-before-review / evidence ref 不可追溯 / index DEFAULT 多重冲突 / plan 路径缺失”等硬问题提前暴露
- 让 reviewer 把精力放在语义质量（scope/contract/risk/验证设计）上
