# Agentic Codex Runtime v3 (SSOT)

> 让 AI 编程 Agent 的开发过程变得**可复现、可验证、可回滚、可断点重续、可持续演进、上下文不腐烂**。

## 仓库结构

- `agentic_codex_runtime_v3/`：**SSOT**。可直接复制到目标仓库根目录使用的 v3 runtime（含 `AGENTS.md`、`.codex/`、`.agents/skills/`、controller、`docs/agentic/`）。
- `agentic_codex_workflow_v2/`：legacy workflow 与历史材料（保留用于对照与迁移参考；不再作为主入口）。
- v2 汇总规范来源：`agentic_codex_workflow_v2/docs/references/design_structure_V2.md`
- v3 现行规范（拆分版）：`agentic_codex_runtime_v3/docs/agentic/spec/`

## v3 核心设计（摘要）

- **Goal truth**：`.agentdocs/tasks/<task-id>/plan.md`
- **Process truth**：`.agentdocs/tasks/<task-id>/workflow.md`
- **World truth**：代码 / tests / 运行时行为
- **Process evidence**：`.agentdocs/tasks/<task-id>/evidence/*.json`
- **Review judgment**：`.agentdocs/tasks/<task-id>/reviews/*.json`
- **Derived digest**：`.agentdocs/tasks/<task-id>/subtask-packs/*.md`（可再生，不是新真相层）

## Quick start（在目标仓库使用）

1. 将 `agentic_codex_runtime_v3/` 内的内容复制到目标仓库根目录（使 `AGENTS.md`、`.codex/`、`.agents/skills/` 位于仓库根）。
2. 按目标仓库实际命令更新 `AGENTS.md` 的 **Local project commands**。
3. 初始化 runtime 存储：

   ```bash
   python .codex/tools/agentctl.py init-agentdocs
   ```

4. 创建任务骨架：

   ```bash
   python .codex/tools/agentctl.py create-task --task-id T001 --title "Example task"
   ```

## Skills（v3）

- `world-grounding`
- `freeze-plan`
- `refresh-subtask-pack`
- `plan-review`
- `execute-subtask`
- `evidence-capture`
- `close-review`
- `reopen-fix`

## License

MIT
