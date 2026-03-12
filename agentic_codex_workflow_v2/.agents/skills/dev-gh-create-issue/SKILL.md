---
name: dev-gh-create-issue
description: |
  用于 ISSUE_SYNC 阶段的 GitHub issue 同步 skill。
  Use when a plan is stable enough to mirror summary, scope, acceptance checklist, links, and phase checklist into an issue,
  while keeping the issue as a concise mirror rather than a second plan source of truth.
---

# Dev GitHub Create Issue

把稳定的 plan 子结构同步到 issue，同时保持 issue 只是镜像层。

## Use Bundled Resources
- 先阅读 `references/issue-writing-guidelines.md`，收敛 summary、scope、acceptance 与 links 的写法。
- 再使用 `assets/issue-template.md` 起草或更新 issue。

## Boundary
- 只同步摘要、范围、acceptance checklist、links 与 phase checklist。
- 不要把完整 plan、完整契约或执行流水账复制到 issue。

## Escalate
- 在 scope、acceptance、phase breakdown 未冻结时，停止 ISSUE_SYNC。
- 在 GitHub 变更权限或目标 issue 信息不明确时，先升级。
