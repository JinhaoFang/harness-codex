# subtask-pack-refresh

## Purpose

从 Goal truth、Process truth、World truth 和必要的 process evidence 重新生成 subtask 的最小入口 digest。

## When to use

- 进入某个 subtask 前
- session 中断后恢复前
- review 或 implementation 前需要 fresh entrypoint 时

## Principles

- pack 是派生视图，不是真相层。
- pack 只放当前 subtask 所需的最小必要信息。
- 能引用的不复制，能再生的不长期持久化。

## Output

输出精简的 `subtask-pack.md`。
