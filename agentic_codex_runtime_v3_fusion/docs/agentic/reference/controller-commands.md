# Controller 最小命令面

## 0. update-current

用途：结构化更新 workflow 当前状态，并可追加一条最小事件。

输入：
- task id
- current gate（可选）
- allowed next action（可选）
- active subtask（可选）
- exception status（可选）
- recovery needed / trigger / exit condition（可选）
- generic workflow bullet updates（可选）
- event（可选）

输出：
- workflow update

规则：
- 当 `plan.md` 与 review artifacts 已存在时，controller 会同时重算 task 级 `Task close-ready` / `Pending close-review subtasks` 摘要，避免 workflow 脱离真实 review 进度。
- `update-current` 会先同步 task 级派生 metadata：例如以 `plan.md` 为准回写 `workflow.md` 的 title/heading/status 镜像，并刷新相关 `updated_at`。

## 1. check-gate

用途：检查当前 gate 是否允许进入下一步。

输入：
- task id
- current workflow ref
- requested action

输出：
- pass / fail
- reason
- required refs

规则：
- `plan-review` 前必须满足 Discuss readiness、plan completeness 与 fresh pack。
- `implement` / `close-review` 前必须有 fresh pack。
- `fresh pack` 不是“文件存在即可”；controller 会校验 pack 记录的 task title、plan/workflow status、`plan.md` / `workflow.md` 修订信息以及 latest review/evidence refs 是否仍与当前 truth 一致。
- 已经存在 pending review request 时，不得重复请求同类 review，也不得跳过 pending review 继续推进依赖它的动作。
- `archive` 前必须所有 subtasks 都已获得 PASS close review；不能只因为最近一个 subtask 的 close review 为 PASS 就归档整个 task。

## 2. request-review

用途：在 workflow 中登记一个待完成的 review 请求，并显式生成 request id。

输入：
- task id
- review type: plan | close
- subtask
- optional event

输出：
- workflow update
- request id

规则：
- `request-review` 会先通过 `check-gate` 验证当前 gate 是否允许请求该类 review。
- 同一类 review 已存在 pending request 时，不得重复请求。
- `plan-review` request 会把 `plan.md` frontmatter 状态同步为 `frozen`，避免主会话把旧的 `approved` / `draft` 信号误读成当前 verdict。

## 3. submit-review

用途：对一个已存在的 pending review request 提交结构化 review judgment。

输入：
- task id
- review type: plan | close
- request id
- reviewer role: `plan_reviewer` | `close_reviewer`
- decision: PASS | CHANGES_REQUIRED | REJECT
- checked refs（task requirements / plan / world anchors / evidence refs）
- coverage（task requirements / goal truth / world truth）
- sampling scope / basis / residual risk（仅 world truth 抽样时）
- materials accessed[]
- findings[] / required_changes[]（可选）

输出：
- review ref（唯一文件名；同类 review 并行写入不得互相覆盖）

规则：
- 没有 pending request 时，不得直接提交 review verdict。
- `plan` verdict 只能由 `plan_reviewer` 角色提交；`close` verdict 只能由 `close_reviewer` 角色提交。
- review judgment 不得写入 evidence 目录。
- close review 的 evidence refs 应指向已存在的 `evidence/*.json` 或可复核的 code/test 指针。
- task requirements 与 Goal truth 核心约束不得标记为 sampled。
- 若 World truth 使用抽样，必须显式写明 scope / basis / residual risk。
- review 必须写明实际访问过的 materials。
- plan review writeback 会同步 `plan.md` frontmatter 状态：`PASS -> approved`，`CHANGES_REQUIRED|REJECT -> needs_revision`。
- submit 后 controller 会把对应 review request 从 `PENDING` 标记为 `RESOLVED`。
- workflow 中记录的是“最新 review 决策 + 对应 subtask”，task 级 archive readiness 由 controller 根据全部 subtasks 的 close review 聚合计算。

## 4. write-evidence

用途：写入结构化 process evidence。

输入：
- task id
- kind: command | test | build | behavior | screenshot | other
- result: PASS | FAIL | INFO
- purpose / command / cwd（可选但推荐）
- artifact_paths[] / notes（可选）

输出：
- evidence ref（唯一文件名；同类 evidence 并行写入不得互相覆盖）

规则：
- evidence 不得包含 review verdict。

## 5. refresh-pack

用途：从主真相与必要 evidence 再生 subtask pack。

输入：
- task id
- subtask id
- plan ref
- workflow ref
- optional evidence refs

输出：
- pack ref

规则：
- pack 优先引用，不复制长段内容。
- pack 应保留当前 objective、verification、evidence plan 与 reviewer focus 的最小必要信息。
- pack 应记录生成时所依据的 task title、plan/workflow status、plan/workflow 修订信息，以及 latest review/evidence refs，供后续 gate 做 freshness 判定。
- pack 只在 grounded plan 存在后生成；初始 create-task 不自动生成空 pack。
- pack 不是新的真相层。
- 当 grounded plan 首次通过 `refresh-pack` 进入 reviewable 状态时，controller 会把 `plan.md` frontmatter 状态从 `draft` / `needs_revision` 同步为 `frozen`。

## 6. archive

用途：在 close review 通过后归档。

前置条件：
- workflow `Task close-ready = YES`
- workflow 中 `Recovery needed = NO`

输出：
- archive ref
- workflow update

## 7. reopen

用途：从归档或关闭状态重新打开。

输入：
- task id
- trigger
- reason

输出：
- workflow update
- required next gate

## 8. validate-refs

用途：校验 plan / workflow / review / evidence / pack 之间的引用有效性。

输入：
- task id

输出：
- pass / fail
- broken refs[]

## 9. init-agentdocs

用途：初始化或补齐 `.agentdocs/` 的派生索引骨架。

输出：
- ensured `.agentdocs/index.md`
- ensured `.agentdocs/archive/index.md`

## 10. create-task

用途：创建 `.agentdocs/tasks/TASK_ID/` 任务骨架。

输入：
- stable topic slug（推荐）
- task id override（可选）
- title
- optional default subtask id（默认 S1）

规则：
- 正常使用优先 `--slug`。
- 使用 `--slug` 时，controller 自动生成 `YYYYMMDD-HHMM[-NN]-<slug>`。
- `--task-id` 只用于迁移或显式 override。

输出：
- plan.md / workflow.md / reviews/ / evidence/ / subtask-packs/
- chosen task id

## 11. sync-index

用途：从磁盘状态再生派生索引（active / archived）。

输出：
- updated `.agentdocs/index.md`
- updated `.agentdocs/archive/index.md`


## update-current optional external refs

```bash
python .codex/tools/agentctl.py update-current --task-id <task-id> --external-ref "gh:issue#123" --external-ref "gh:pr#456"
```

Use this only to record external collaboration mirrors. The repo runtime remains the source of truth.
