# Controller 设计定位

controller 是 **deterministic control plane**，应当单独设计与实现，不应被塞进 skills。

本目录提供：

- `docs/agentic/reference/controller-commands.md`：Fusion controller 最小命令面（规范）
- `.codex/tools/agentctl.py`：参考实现（可在目标仓库中运行），用于一键初始化 `.agentdocs/`、创建 task 骨架、写入 review/evidence、再生 subtask pack、校验引用与归档

## 职责边界

controller MUST:
- 检查 gate 合法性
- 检查 schema / completeness / 引用约束
- 结构化写入 workflow / reviews / evidence
- 刷新 subtask pack
- 维护 archive / reopen 一致性
- 在不新增长期工件的前提下，把 Discuss gate、review coverage 与 sampling discipline 变成可检查约束

controller MUST NOT:
- 代替 reviewer 做主观裁决
- 代替 plan 写 Goal truth
- 代替代码世界回答架构是否正确

skills MAY:
- 指导 world grounding
- 指导 plan review
- 指导 reuse check
- 指导 close review
- 触发 controller 命令

skills MUST NOT:
- 直接定义状态推进真相
- 直接定义完成真相
- 直接定义回滚真相

---

## 参考实现：`agentctl.py`

> 说明：本仓库主要提供模板与规范；`.agentdocs/` 会在“实际使用该流程的目标仓库”中由脚本初始化与维护。

### 快速开始

在目标仓库根目录执行（或使用 `--repo-root` 指定）：

```bash
python .codex/tools/agentctl.py init-agentdocs
python .codex/tools/agentctl.py create-task --slug my-task --title "My Task"
```

### 重要约束（Fusion）

- `delegation-brief` 是 session wrapper，默认不作为长期对象落盘。
- `subtask-pack` 是派生 digest，可再生；不允许引用或保留 V2 的 `task-packs/`。
- `fusion` 默认使用 `--slug` 生成 `YYYYMMDD-HHMM[-NN]-<slug>`；`--task-id` 只应作为显式 override。
- `create-task` 只创建 skeleton；`subtask-pack` 应在 grounded plan 存在后再刷新。
- `plan.md` 承载 Goal truth；`workflow.md` 承载 Process truth；review 与 evidence 必须分离写入。
- controller 会在 freeze/review 关键节点同步 `plan.md` frontmatter 状态（`draft -> frozen -> approved`，或在打回时 `needs_revision`）。
- workflow 中的 close-review 既记录“最新 reviewed subtask”，也记录 task 级 `Task close-ready` 聚合结果；archive 只看 task 级聚合，不看单个 subtask 的 PASS。
