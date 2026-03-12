---
name: dev-agentdocs-check
description: |
  对 agentdocs、task pack、workflow gate 与 skill 结构执行确定性体检的 tooling skill。
  Use when Codex needs to run repo-local preflight checks before BUILD / REVIEW / ARCHIVE,
  or when workflow references, pack structure, evidence paths, or skill scaffolding may be inconsistent.
---

# Dev Agentdocs Check

在进入下一道 gate 前，先运行确定性 preflight，而不是依赖自由文本判断。

## Use Bundled Resources
- 运行 `scripts/agentdocs_check.py`，并显式选择 `--mode flowcheck|lint|coverage|all` 与正确的 `--intent`。
- 运行 `scripts/evidence_run.py`，把验证命令封装成可复核的 evidence bundle。
- 阅读 `assets/output-schema.md`，确认下游消费的 JSON 字段与状态含义。

## Write Boundary
- 只写脚本生成的 task-scoped evidence bundle。
- 把 workflow 状态推进、review 结论与结构修复留给 controller 或上层路由动作。

## Escalate
- 在结果为 `BLOCK`、路径缺失、pack 不完整或 evidence 不可追溯时，停止当前 gate。
- 不要用本 skill 代替 plan review、close review 或业务实现判断。
