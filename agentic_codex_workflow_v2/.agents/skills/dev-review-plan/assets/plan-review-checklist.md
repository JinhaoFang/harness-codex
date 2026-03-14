# Plan Review Checklist

## 1) Scope & State Machine

- [ ] Plan 是否清楚写明 Goal / In Scope / Out of Scope / Success Criteria
- [ ] workflow 当前状态是否为 `PLAN_REVIEW`
- [ ] 当前任务是否具备唯一下一状态：`BUILD` 或回退 `PLAN_DRAFT`
- [ ] workflow / issue 是否没有复制完整规格

## 2) Memory / Coverage / Scratch

- [ ] workflow 是否记录 `Memory Lookup Used = YES`
- [ ] Plan 是否写明复用规则与需重新验证的规则
- [ ] Context Coverage 是否包含 `Must Read / Adjacent Scan / Unread But Potentially Relevant / Coverage Decision`
- [ ] Scratch 是否只作为临时研究层，且写明 promotion 规则

## 3) Architecture & Contract

- [ ] reviewer 是否已按需抽样代码 / 接口 / 架构事实，而不是只依据文档表面判断
- [ ] 架构边界、生命周期、依赖方向是否与项目规范一致
- [ ] 契约、边界、错误策略、兼容策略是否明确且可检查
- [ ] 边界场景是否覆盖关键失败路径

## 4) Verification & Evidence

- [ ] Gate Pack 是否合理
- [ ] 每个 phase 是否都有可执行 Verify 与 Evidence Bundle
- [ ] reviewer 是否能在独立会话里复核关键验证
- [ ] Evidence Ref 是否计划指向 `.agentdocs/tasks/<task-id>/evidence/`

## 5) Governance & Risk

- [ ] 新依赖 / 新基础设施 / public API / 数据迁移 / 安全例外 是否明确标出
- [ ] 需用户拍板项是否清楚列出
- [ ] Top Risks 是否真实而不是模板化占位
- [ ] breaking change 的迁移与回滚是否完整

## 6) Review Output Format

请固定输出：

1. Decision: PASS / NEEDS_CHANGES
2. Summary: 3~8 行
3. Required Changes:
   - [ ] item（带路径/章节 + 修改要点 + 验证方式；必须是 blocking delta，不重写整份 plan）
4. Evidence:
5. Open Questions（<= 3，仅在信息不足时使用）
