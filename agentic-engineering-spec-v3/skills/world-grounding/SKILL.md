# world-grounding

## Purpose

在形成或修订 `plan.md` 之前，先用代码世界核对真实情况。

## When to use

- 准备写 plan 时
- plan 有重大修改时
- reviewer 认为 plan 可能脱离项目现实时

## Steps

1. 识别关键入口文件、关键符号、关键 tests。
2. 识别现有可复用途径与已有实现。
3. 记录会影响 plan 的现实约束。
4. 只输出最小 grounding 结果，不生成厚 recap。

## Output

输出一份简洁的 grounding 摘要，供 `plan.md` 或 review 使用。

## Must not

- 不得直接改写 `plan.md` 中的目标承诺。
- 不得把运行日志混成 World truth。
