# High-Entropy 闭环

唯一正常路径：
1. `dev-workflow-bootstrap`
   - 初始化或恢复 `.agentdocs`
   - 建立 / 注册 workflow SSOT
   - 创建 `.agentdocs/tasks/<task-id>/` 及其 task-scoped 子目录
2. `dev-gh-create-issue`
   - 创建 / 复用 issue
   - 只同步摘要、scope、acceptance、links、phase checklist
3. `dev-write-plan`
   - 生成 / 更新 Plan Doc
   - 固化规格、边界、契约、phase、evidence plan、scratch promotion rule
4. `dev-review-plan`
   - 必须使用独立 `plan_reviewer`
   - `PASS` 前禁止进入 Build
   - reviewer 输出由主 agent 原样回填 workflow
5. Build
   - 每个阶段使用独立 `worker`
   - 每个已完成 phase 必须回填 `Verify Run + Evidence Ref`
   - `Evidence Ref` 必须指向 `.agentdocs/tasks/<task-id>/evidence/`
6. `dev-close-review`
   - 必须使用独立 `close_reviewer`
   - 抽样 evidence bundle
   - PASS 后调用 `dev-memory-router`
   - 通过状态校验脚本后再归档

异常只允许进入 `EXCEPTION_RECOVERY`，不得伪装成正常路径。
