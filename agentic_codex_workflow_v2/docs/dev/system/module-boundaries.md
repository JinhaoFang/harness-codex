# Agentic System Module Boundaries

> 这份文档不是新增治理对象，而是把系统已存在的构件按职责重新分层，避免后续演进时把“规则、角色、技能、状态、脚本”揉成一团。

## 1. Policy Layer
位置：`AGENTS.md`、`docs/dev/contracts/*`

负责：
- 真源优先级
- 状态机
- task pack 最低字段
- 评审与归档门禁
- 结构化写回原则

不负责：
- 不决定当前该调用哪个 sub-agent
- 不规定某个 skill 的内部 checklist 长什么样

## 2. Orchestration Layer
位置：`.codex/config.toml`、`.codex/agents/*.toml`、router skills

负责：
- 角色选择
- phase / review mode / next legal action
- single-agent 与 multi-agent 的切换

演进方向：
- 模型能力上升时，这一层最容易收缩或替换

## 3. Capability Layer
位置：`.agents/skills/*`

负责：
- 把专门能力封装成渐进加载模块
- 让主 agent 先知道能力目录，再由 specialist 深读执行手册

推荐分类：
- Router skills
- Specialist skills
- Tooling skills

## 4. State Layer
位置：`.agentdocs/*`

负责：
- workflow / plan / task pack / review / evidence / archive 的持久化
- 跨会话恢复
- 审计、回放、可视化输入

要求：
- machine-readable canonical artifact 优先
- 文本叙述与结构字段应可相互定位

## 5. Controller Layer
位置：`.codex/workflow/taskctl.py`、templates

负责：
- 模板渲染
- pack 校验
- delegation brief 生成
- 结构化写回
- skill lint
- archive / index sync

要求：
- 优先提供稳定命令接口，而不是让 skill 直接依赖内部脚本路径
- 所有新增结构化输出都应为未来可视化保留机读格式
