# plan-review

## Purpose

用 fresh context 检查 Goal truth 是否与代码世界一致。

## When to use

- `plan.md` 初稿完成后
- goal / boundary / technical choice 有显著变化后

## Checklist

1. plan 是否和现有项目结构冲突。
2. 是否忽略已有模块、已有方法、已有 tests。
3. 技术选型是否与项目演化方向冲突。
4. verification 是否真的能证明完成。
5. rollback 是否可执行。

## Output

输出结构化 review judgment：pass / revise / reject，并给出 grounded reasons。

## Must not

- 不得只查格式。
- 不得共享 builder 的长上下文。
