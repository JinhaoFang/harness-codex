# Agentic Engineering Spec v3

本包包含：

- `spec/`：上位规范、对象最小化、运行与平台映射
- `templates/`：可直接落仓的最小模板
- `skills/`：方法注入技能
- `controller/`：deterministic control plane 设计与最小命令面（含参考实现 `controller/agentctl.py`）

## v3 精修重点

- 继续压薄 `plan.md` / `workflow.md` / `subtask-pack.md`
- 将 `AGENTS.md` 调整为更像真实仓库入口的薄协议
- 将 `delegation-brief` 明确降为 session wrapper
- 为 controller 增加可独立实现的最小命令面
