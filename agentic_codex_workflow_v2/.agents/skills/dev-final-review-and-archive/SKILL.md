---
name: dev-final-review-and-archive
description: |
  兼容旧入口的 close-review / archive compatibility skill。
  Use only when a legacy session, note, or prompt still refers to this old entry,
  and Codex must translate it back to the current `dev-review-router` + `dev-close-review` flow without losing auditability.
---

# Dev Final Review & Archive

把遗留入口翻译回当前 close-review / archive 流程，不要把这个兼容层当成新主入口。

## Use Bundled Resources
- 优先把调用迁移到 `dev-review-router` 与 `dev-close-review`。
- 仅在解释遗留说明时阅读 `assets/close-checklist.md` 与 `assets/close-summary-template.md`。
- 仅在遗留手工写回兼容场景下使用 `scripts/apply_close_record.py`；默认仍优先 controller。

## Boundary
- 保持当前状态机、独立 `close_reviewer` 与 task-scoped archive 流程不变。
- 不要借兼容层绕过 review gate 或 controller。

## Escalate
- 在遗留说明与现行契约冲突时，先迁移入口再继续。
- 不要把本 skill 当作新流程的 close-review 手册。
