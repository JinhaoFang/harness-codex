# Controller 最小命令面

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

## 2. write-review

用途：写入结构化 review judgment。

输入：
- task id
- review type: plan | close
- verdict: pass | revise | reject
- reasons[]
- evidence_refs[]

输出：
- review ref

规则：
- review judgment 不得写入 evidence 目录。
- evidence_refs 必须指向已存在 evidence 或代码指针。

## 3. write-evidence

用途：写入结构化 process evidence。

输入：
- task id
- evidence type: command | test | runtime | screenshot | note
- summary
- refs[]

输出：
- evidence ref

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
- pack 不是新的真相层。

## 5. archive

用途：在 close review 通过后归档。

前置条件：
- close review = pass
- workflow 无未退出异常

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
