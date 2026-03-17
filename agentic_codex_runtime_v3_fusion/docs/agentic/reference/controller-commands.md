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

## 2. write-review

用途：写入结构化 review judgment。

输入：
- task id
- review type: plan | close
- decision: PASS | CHANGES_REQUIRED | REJECT
- checked refs（task requirements / plan / world anchors / evidence refs）
- coverage（task requirements / goal truth / world truth）
- sampling scope / basis / residual risk（仅 world truth 抽样时）
- materials accessed[]
- findings[] / required_changes[]（可选）

输出：
- review ref（唯一文件名；同类 review 并行写入不得互相覆盖）

规则：
- review judgment 不得写入 evidence 目录。
- close review 的 evidence refs 应指向已存在的 `evidence/*.json` 或可复核的 code/test 指针。
- task requirements 与 Goal truth 核心约束不得标记为 sampled。
- 若 World truth 使用抽样，必须显式写明 scope / basis / residual risk。
- review 必须写明实际访问过的 materials。

## 3. write-evidence

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

## 4. refresh-pack

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
- pack 只在 grounded plan 存在后生成；初始 create-task 不自动生成空 pack。
- pack 不是新的真相层。

## 5. archive

用途：在 close review 通过后归档。

前置条件：
- Close review = PASS
- workflow 中 `Recovery needed = NO`

输出：
- archive ref
- workflow update

## 6. reopen

用途：从归档或关闭状态重新打开。

输入：
- task id
- trigger
- reason

输出：
- workflow update
- required next gate

## 7. validate-refs

用途：校验 plan / workflow / review / evidence / pack 之间的引用有效性。

输入：
- task id

输出：
- pass / fail
- broken refs[]

## 8. init-agentdocs

用途：初始化或补齐 `.agentdocs/` 的派生索引骨架。

输出：
- ensured `.agentdocs/index.md`
- ensured `.agentdocs/archive/index.md`

## 9. create-task

用途：创建 `.agentdocs/tasks/TASK_ID/` 任务骨架。

输入：
- task id
- title
- optional default subtask id（默认 S1）

输出：
- plan.md / workflow.md / reviews/ / evidence/ / subtask-packs/

## 10. sync-index

用途：从磁盘状态再生派生索引（active / archived）。

输出：
- updated `.agentdocs/index.md`
- updated `.agentdocs/archive/index.md`


## update-current optional external refs

```bash
python .codex/tools/agentctl.py update-current --task-id <task-id> --external-ref "gh:issue#123" --external-ref "gh:pr#456"
```

Use this only to record external collaboration mirrors. The repo runtime remains the source of truth.
