# Current Truth Anchors Contract (V3)

> 这份契约解决一个常见偏差：agent 在进入实现后仍然过度依赖 plan / docs，导致“以文档代替代码现实”。V3 要求把“当前事实真源”显式写出来，并在 BUILD / REVIEW 阶段优先回到这些锚点。

## 1. 定义
**Current Truth Anchors** 是用于证明“系统当前实际上是什么”的最小证据集合，通常来自：
- 代码路径
- 关键符号 / 组件 / 命令
- 测试
- 配置
- 运行输出 / 日志 / 页面行为

## 2. 何时必须存在
以下阶段必须显式列出 truth anchors：
- `ALIGN_PROOF`
- `PLAN_DRAFT`
- `BUILD`
- `CLOSE_REVIEW`

## 3. 最低字段
- `Code Paths`
- `Key Symbols / Entry Points`
- `Tests / Checks`
- `Config / Env Anchors`
- `Runtime Evidence`
- `Doc Notes (辅助，仅解释，不覆盖事实)`

## 4. 使用规则
1. 要判断“当前行为”，先读 truth anchors，再读文档
2. 文档与代码冲突时，以代码 / 测试 / 运行结果为准
3. 若代码不可直接说明，需要补充运行时 evidence
4. reviewer 至少抽样复核 1 个 truth anchor
