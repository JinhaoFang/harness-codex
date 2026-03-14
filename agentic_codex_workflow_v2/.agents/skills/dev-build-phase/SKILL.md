---
name: dev-build-phase
description: |
  面向 worker 的 BUILD specialist skill。
  Use when the current task already passed PLAN_REVIEW, a BUILD task pack exists,
  and Codex needs to execute exactly one implementation phase with minimal change and traceable evidence.
---

# Dev Build Phase

先读取当前 BUILD task pack，再执行一个实现 phase。

## Procedure

- 重新读取 task pack、workflow / plan 中被当前 phase 引用的段落。
- 回到 code / tests / config / runtime truth anchors，确认当前事实再编辑。
- 只在当前 phase 的 write boundary 内做可辩护修改。
- 产出 traceable evidence，并返回自描述结果包。

## Write Boundary

- 只写当前 phase 授权的实现文件与 task-scoped 工件。
- 不要承担 review、archive 或 governance 决策。

## Escalate

- 在 plan 不足、scope / acceptance / contract 变化、truth anchor 冲突或 write boundary 需要扩大时，回退到 `PLAN_DRAFT`。
- 在 task pack、truth anchors 或验证命令缺失时，停止当前 phase。
