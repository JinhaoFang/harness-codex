# 融合决策清单（以 v3 runtime 为地基）

> 本清单回答的不是“第一套有什么好设计”，而是“哪些设计在吸收后仍然不破坏 v3 runtime 的 truth model、controller boundary 与 object minimization”。

## 核心原则

1. **不新增重复真相层**：不能为了协作便利再长出新的长期账本。
2. **controller 只做 deterministic operations**：不把 `agentctl.py` 变成厚流程编排器或 GitHub orchestrator。
3. **平台能力做成可拔插模块**：GitHub / worktree / hooks 都不是 runtime 宪法。
4. **优先保留未来不容易过时的东西**：truth model、review discipline、evidence traceability、reversible workflow。

## 决策表

| 模块 | 结论 | 归宿 | 原因 |
|---|---|---|---|
| `plan.md` / `workflow.md` / review / evidence / subtask-pack | 保留 | runtime core | 第二套内核，不接受第一套反向塑形 |
| `.githooks/*` | 吸收 | repo guardrails | 高价值、低耦合、不污染 truth model |
| `.github/workflows/security-checks.yml` | 吸收 | repo guardrails | 与 runtime 正交，长期有价值 |
| `worktree` | 重写吸收 | optional skill | 重要，但只属于执行工作区，不属于真相层 |
| GitHub-first 协作 | 重写吸收 | optional skill + minimal external refs | 保留 traceability，不把 GitHub 变成 SoT |
| `harness` session / recovery 思想 | 重写吸收 | optional skill | 吸收恢复与并发原语，不引入独立状态文件 |
| `harness-tasks.json` / `harness-progress.txt` | 放弃 | 不引入 | 与 `workflow.md` / review / evidence 重复记账 |
| `docs/prd|api|ui` 习惯 | 重写吸收 | `docs/contracts/*` 可选长期合同 | 避免与 `plan.md` 重叠，但保留长期合同价值 |
| `tests/*-test-cases.md` 固定流程 | 降级 | strategy only | 保留验证思想，不设为硬性对象 |
| TDD | 降级 | strategy only | 是方法，不是 runtime 真相 |
| GitHub CLI 具体操作 | 降级 | optional adapter | 未来最可能被上游替代 |
| controller 直接管理 issue / PR | 放弃 | 不引入 | 会让 deterministic control plane 变厚 |

## 直接红线

以下内容不得进入 runtime core：

- GitHub issue / PR 作为唯一任务真相
- worktree 作为状态推进对象
- session history / progress log 作为 process truth
- 每个 task 默认必须生成 PRD/API/UI 文档
- 每个 task 默认必须生成测试用例文档
- 每个 task 默认必须走 issue + PR 才算合法

## 本次融合实际落地

### 已落地
- repo guardrails：`.githooks/*`、`.github/workflows/security-checks.yml`
- optional skills：`contract-artifacts`、`github-collaboration`、`session-recovery`、`worktree-isolation`
- minimal controller extension：`workflow.md` 增加 `External refs`，供外部协作适配器记录 traceable mirrors
- optional contracts：`docs/contracts/*`

### 明确未落地
- 不迁移 Harness 状态文件体系
- 不迁移 GitHub-first 宪法化约束
- 不把 PRD/API/UI 变成所有任务默认前置工件
- 不让 controller 直接创建 / 评论 / 合并 issue/PR

## 使用顺序建议

1. 继续按 v3 core 执行：`Discuss -> Ground -> Freeze Goal Truth -> Review -> Execute -> Evidence -> Close Review -> Archive`
2. 只有在确有需要时，再按需注入 optional modules：
   - 需要 repo 工程护栏：启用 hooks / workflows
   - 需要并行工作区：用 `worktree-isolation`
   - 需要外部协作镜像：用 `github-collaboration`
   - 需要恢复中断工作：用 `session-recovery`
   - 需要长期业务/API/UI 合同：用 `contract-artifacts`
