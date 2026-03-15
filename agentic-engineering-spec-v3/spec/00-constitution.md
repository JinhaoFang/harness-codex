# 上位规范（Constitution）

> 本文件是系统宪法，不是理念说明书。

## 1. 目标

本规范约束基于 coding agents 的软件开发系统，使其在长程、多轮、多 agent、跨会话场景下仍保持：

- 可复现
- 可验证
- 可回滚
- 可断点重续
- 可持续演进
- 上下文不腐烂

## 2. 术语

- **Goal truth**：目标、非目标、边界、关键决策、完成约束。
- **Process truth**：当前位置、合法推进、当前 gate、恢复入口。
- **World truth**：项目代码、tests、已有结构、已有可复用途径。
- **Process evidence**：运行与审查过程中形成的结构化事实记录；可支持裁决、恢复与再生，但不构成 World truth。
- **Derived digest**：从 Goal truth、Process truth、World truth 与必要 Process evidence 再生出的轻量入口材料；不构成真相层。

## 3. 不变量

### 3.1 真相所有权

MUST:
- `plan.md` 只承载 Goal truth。
- `workflow.md` 只承载 Process truth。
- code / tests / 项目已有结构承载 World truth。
- `reviews/*.json` 只承载 review judgment。
- `evidence/*.json` 只承载 Process evidence。

MUST NOT:
- 用 summary、handoff、pack、brief 改写真相层。
- 用 review judgment 冒充 evidence。
- 用 evidence 冒充项目本体现实。

### 3.2 职责分治

MUST:
- 状态推进合法性由 deterministic control plane 检查。
- schema、引用约束、完整性校验由 deterministic control plane 检查。
- LLM 只承担局部探索、局部判断、代码生成、审查分析。

MUST NOT:
- 让 LLM 拥有制度主权。
- 让 prompt discipline 代替 control plane。

### 3.3 上下文装配

MUST:
- 当前执行单元只接收最小必要信息。
- review 使用 fresh context。
- Derived digest 按需再生，不默认厚持久化。

MUST NOT:
- 依赖长会话自然累积记忆。
- 让旧摘要直接替代对代码世界的重新核对。

### 3.4 证据裁决

MUST:
- plan 经独立审查通过后才能进入实现。
- 实现经独立审查通过后才能关闭。
- reviewer 以 World truth 审 Goal truth 与实现结果。

MUST NOT:
- 用格式正确代替审查通过。
- 用“做了很多”代替“证明成立”。

### 3.5 可逆与反熵

MUST:
- 每个可委派单元具有清晰撤销边界。
- 系统可从 Goal truth、Process truth、World truth 重新进入。
- 高层工作表示按需再生。

MUST NOT:
- 依赖 summary of summary of summary。
- 让恢复工件升格为真相层。
- 让持久化摘要无限膨胀。

## 4. 最小长期对象

长期一等对象仅保留：

1. `AGENTS.md`
2. `plan.md`
3. `workflow.md`
4. `reviews/*.json`
5. `evidence/*.json`
6. code / tests

其余对象应尽量降为：
- derived digest
- 临时 wrapper
- 会话内中间态

## 5. 红线

1. 文档不得覆盖代码世界。
2. 恢复工件不得成为新真相源。
3. reviewer 不得共享 builder 的长上下文。
4. skills / rules / hooks 不得拥有制度主权。
5. controller 不得代替 reviewer 做主观裁决。

## 6. 最小 gate

系统至少包含以下四个 gate：

1. **Understand**：明确目标、范围、非目标、验收。
2. **Ground in World**：核对代码、tests、已有结构、已有可复用途径。
3. **Freeze Goal Truth**：冻结目标、边界、关键决策、验证要求、回滚策略、执行单元拆解。
4. **Independent Review**：以 fresh context 审 plan 或实现结果。

本规范不要求固定采用某条长状态链，但上述 gate 不得缺失。
