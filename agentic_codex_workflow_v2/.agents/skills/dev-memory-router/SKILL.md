---
name: dev-memory-router
description: |
  把已验证结论路由到长期记忆的 routing skill。
  Use near task close when Codex must decide whether stable findings belong in `.agentdocs/architecture/`
  or `.agentdocs/insights.md`, while keeping one-off execution notes out of long-term memory.
---

# Dev Memory Router

只路由已验证、可复用的结论，不把执行流水账提升为长期记忆。

## Use Bundled Resources
- 阅读 `references/memory-routing-rules.md`，再判断目标应是 `architecture/` 还是 `insights.md`。
- 按统一 schema 组织 `Rule / Why / Trigger / Example / Source Workflow / Last Verified / Verification Source`。

## Boundary
- 只提升本次任务重新验证过、对未来高频复用有价值的结论。
- 优先合并近义旧条目，不制造重复长期记忆。

## Escalate
- 在结论尚未验证、被 close review 判为不稳定或需要先合并历史条目时，延后写回。
- 不要绕过 close review 的稳定性判断。
