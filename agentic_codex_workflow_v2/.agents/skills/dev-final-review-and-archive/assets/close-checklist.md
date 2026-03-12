# Close Checklist

## 1) Independent Review
- [ ] close reviewer 与主实现者独立
- [ ] close reviewer 仅写 task-scoped review 产物与 controller sidecar
- [ ] 若存在独立性例外，workflow 中已明确记录原因

## 2) Spec Alignment
- [ ] 实现结果与已通过的 plan 一致
- [ ] 没有在实现阶段偷偷扩大 scope 或更改 contract
- [ ] 关键文件 / 模块改动与 Phase Board 一致

## 3) Verification & Evidence
- [ ] 所有 `DONE` phase 都有 `Verify Run + Evidence Ref`
- [ ] `Evidence Ref` 指向真实 bundle 路径
- [ ] 至少抽样复核一条 evidence bundle
- [ ] 关键 Gate 已复跑，或已记录降级原因与后续补跑要求

## 4) Runtime Governance
- [ ] `PLAN_REVIEW = PASS` 后才进入过 `BUILD`
- [ ] 当前 workflow 没有非法状态转移
- [ ] 若发生异常，已通过 `EXCEPTION_RECOVERY` 收口
- [ ] 当前状态允许下一步进入 `ARCHIVE`

## 5) Documentation & Memory
- [ ] workflow / issue / plan 已同步到最终状态
- [ ] memory lookup 在 Align 阶段被实际使用
- [ ] Memory Candidates 只包含本次任务验证过的稳定规则
- [ ] scratch 已 promote 或明确关闭

## 6) Final Output Format
- Final Status: PASS / NEEDS_FIX / BLOCKED
- Key Findings:
- Required Follow-ups:
- Evidence Summary:
- Archive Actions:
