---
name: dev-structured-writeback
description: |
  用于结构化写回 review、evidence 与 workflow event 的 tooling skill。
  Use when semantic content is already decided and Codex needs a deterministic way to persist
  review bundles, evidence bundles, or workflow events through repo-local controller entrypoints.
---

# Dev Structured Writeback

在语义内容已经冻结时，再调用 deterministic writeback。

## Use Bundled Resources
- 运行 `scripts/write_review.sh` 写 review bundle。
- 运行 `scripts/write_evidence.sh` 写 evidence bundle。
- 运行 `scripts/write_workflow_event.sh` 写 workflow event。

## Boundary
- 只传入已经准备好的结构化字段，不在写回阶段发明新语义。
- 把写入限制在 task-scoped review / evidence / workflow event 产物。

## Escalate
- 在 controller 失败时，只报告失败与恢复动作。
- 不要手工补丁伪造“已写回”结果。
