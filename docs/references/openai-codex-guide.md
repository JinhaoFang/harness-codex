# OpenAI Codex 官方文档指南

> 来源：
> - https://developers.openai.com/codex/rules
> - https://developers.openai.com/codex/guides/agents-md
> - https://developers.openai.com/codex/skills
> - https://developers.openai.com/codex/subagents

---

## 目录

1. [Rules - 命令执行规则控制](#1-rules---命令执行规则控制)
2. [AGENTS.md - 自定义指令](#2-agentsmd---自定义指令)
3. [Agent Skills - 技能扩展](#3-agent-skills---技能扩展)
4. [Subagents - 子代理协作](#4-subagents---子代理协作)

---

## 1. Rules - 命令执行规则控制

> **注意**：Rules 是实验性功能，可能会发生变化。

使用 Rules 控制 Codex 在沙箱外可以运行哪些命令。

### 创建规则文件

1. 在 `./codex/rules/` 下创建 `.rules` 文件（例如 `~/.codex/rules/default.rules`）
2. 添加规则。以下示例在允许 `gh pr view` 在沙箱外运行前会提示确认：

```
# Prompt before running commands with the prefix `gh pr view` outside the sandbox.
prefix_rule(
    # The prefix to match.
    pattern = ["gh", "pr", "view"],

    # The action to take when Codex requests to run a matching command.
    decision = "prompt",

    # Optional rationale for why this rule exists.
    justification = "Viewing PRs is allowed with approval",

    # `match` and `not_match` are optional "inline unit tests" where you can
    # provide examples of commands that should (or should not) match this rule.
    match = [
        "gh pr view 7888",
        "gh pr view --repo openai/codex",
        "gh pr view 7888 --json title,body,comments",
    ],
    not_match = [
        # Does not match because the `pattern` must be an exact prefix.
        "gh pr --repo openai/codex view 7888",
    ],
)
```

3. 重启 Codex

### 规则加载机制

Codex 在启动时扫描每个 Team Config 位置下的 `rules/` 目录。当你在 TUI 中将命令添加到允许列表时，Codex 会写入用户层的 `~/.codex/rules/default.rules`，以便后续运行可以跳过提示。

当启用 Smart approvals（默认）时，Codex 可能在升级请求期间为你提议一个 `prefix_rule`。在接受之前请仔细审查建议的前缀。

管理员也可以从 `requirements.toml` 中强制执行限制性的 `prefix_rule` 条目。

### prefix_rule 字段说明

| 字段 | 必需 | 说明 |
|------|------|------|
| `pattern` | 是 | 定义要匹配的命令前缀的非空列表。每个元素可以是字面字符串（如 `"pr"`）或字面量的联合（如 `["view", "list"]`）来匹配该参数位置的替代选项 |
| `decision` | 否（默认 `"allow"`） | 规则匹配时的操作。当多个规则匹配时，Codex 应用最严格的决策（`forbidden` > `prompt` > `allow`） |
| `justification` | 否 | 规则的人类可读原因。Codex 可能在批准提示或拒绝消息中显示它 |
| `match` / `not_match` | 否（默认 `[]`） | Codex 加载规则时验证的示例。用于在规则生效前捕获错误 |

**decision 选项：**
- `allow`：在沙箱外运行命令，无需提示
- `prompt`：每次匹配调用前提示
- `forbidden`：阻止请求，不提示

### Shell 脚本的安全处理

某些工具将多个 shell 命令包装在单个调用中，例如：

```
["bash", "-lc", "git add . && rm -rf /"]
```

因为这类命令可以在一个字符串中隐藏多个操作，Codex 会特殊处理 `bash -lc`、`bash -c` 及其 `zsh` / `sh` 等效命令。

#### 当 Codex 可以安全拆分脚本时

如果 shell 脚本是由以下组成的线性命令链：
- 纯单词（无变量扩展、无 `VAR=...`、`$FOO`、`*` 等）
- 由安全操作符连接（`&&`、`||`、`;` 或 `|`）

那么 Codex 会解析它（使用 tree-sitter）并将其拆分为单独的命令，然后应用你的规则。

上面的脚本被视为两个单独的命令：
- `["git", "add", "."]`
- `["rm", "-rf", "/"]`

Codex 会针对你的规则评估每个命令，最严格的结果获胜。即使你允许 `pattern=["git", "add"]`，Codex 也不会自动允许 `git add . && rm -rf /`，因为 `rm -rf /` 部分会单独评估并阻止整个调用被自动允许。

#### 当 Codex 不拆分脚本时

如果脚本使用更高级的 shell 功能，如：
- 重定向（`>`、`>>`、`<`）
- 替换（`$(...)`、`...`）
- 环境变量（`FOO=bar`）
- 通配符模式（`*`、`?`）
- 控制流（`if`、`for`、带赋值的 `&&` 等）

那么 Codex 不会尝试解释或拆分它。在这种情况下，整个调用被视为：

```
["bash", "-lc", "<full script>"]
```

你的规则会应用于这**单个**调用。

### 测试规则

使用 `codex execpolicy check` 测试规则如何应用于命令：

```bash
codex execpolicy check --pretty \
  --rules ~/.codex/rules/default.rules \
  -- gh pr view 7888 --json title,body,comments
```

命令会输出 JSON，显示最严格的决策和任何匹配的规则，包括匹配规则中的任何 `justification` 值。使用多个 `--rules` 标志来组合文件，添加 `--pretty` 来格式化输出。

`.rules` 文件格式使用 **Starlark**（参见语言规范）。其语法类似 Python，但设计为可安全运行：规则引擎可以在没有副作用的情况下运行它（例如，不触及文件系统）。

---

## 2. AGENTS.md - 自定义指令

Codex 在执行任何工作之前会读取 `AGENTS.md` 文件。通过将全局指导与项目特定的覆盖层结合，无论打开哪个仓库，你都可以以一致的期望开始每个任务。

### 指令链发现顺序

Codex 在启动时构建指令链（每次运行一次；在 TUI 中通常意味着每个启动的会话一次）。发现遵循以下优先级顺序：

1. **全局作用域**：在 Codex 主目录中（默认为 `~/.codex`，除非设置了 `CODEX_HOME`），Codex 读取 `AGENTS.override.md`（如果存在）。否则，Codex 读取 `AGENTS.md`。Codex 仅使用此级别的第一个非空文件。

2. **项目作用域**：从项目根目录（通常是 Git 根目录）开始，Codex 向下遍历到当前工作目录。如果 Codex 找不到项目根目录，它只检查当前目录。在路径中的每个目录中，它检查 `AGENTS.override.md`，然后是 `AGENTS.md`，然后是 `project_doc_fallback_filenames` 中的任何回退名称。Codex 每个目录最多包含一个文件。

3. **合并顺序**：Codex 从根目录向下连接文件，用空行连接它们。更接近当前目录的文件会覆盖早期指导，因为它们出现在组合提示的后面。

Codex 跳过空文件，并在组合大小达到 `project_doc_max_bytes` 定义的限制（默认 32 KiB）后停止添加文件。

### 创建全局默认值

在 Codex 主目录中创建持久默认值，以便每个仓库继承你的工作协议。

1. 确保目录存在：
   ```bash
   mkdir -p ~/.codex
   ```

2. 创建 `~/.codex/AGENTS.md` 包含可重用的偏好：
   ```markdown
   # ~/.codex/AGENTS.md

   ## Working agreements

   - Always run `npm test` after modifying JavaScript files.
   - Prefer `pnpm` when installing dependencies.
   - Ask for confirmation before adding new production dependencies.
   ```

3. 在任何地方运行 Codex 确认它加载了文件：
   ```bash
   codex --ask-for-approval never "Summarize the current instructions."
   ```

使用 `~/.codex/AGENTS.override.md` 当你需要临时的全局覆盖而不删除基础文件时。删除覆盖以恢复共享指导。

### 项目级文件

仓库级文件让 Codex 了解项目规范，同时仍然继承你的全局默认值。

1. 在仓库根目录添加 `AGENTS.md`：
   ```markdown
   # AGENTS.md

   ## Repository expectations

   - Run `npm run lint` before opening a pull request.
   - Document public utilities in `docs/` when you change behavior.
   ```

2. 当特定团队需要不同规则时，在嵌套目录中添加覆盖。例如，在 `services/payments/` 内创建 `AGENTS.override.md`：
   ```markdown
   # services/payments/AGENTS.override.md

   ## Payments service rules

   - Use `make test-payments` instead of `npm test`.
   - Never rotate API keys without notifying the security channel.
   ```

3. 从 payments 目录启动 Codex：
   ```bash
   codex --cd services/payments --ask-for-approval never "List the instruction sources you loaded."
   ```

### 目录结构示例

```
- AGENTS.md                    # Repository expectations
- services/
  - payments/
    - AGENTS.md                # Ignored because an override exists
    - AGENTS.override.md       # Payments service rules
    - README.md
  - search/
    - AGENTS.md
    - ...
```

### 配置回退文件名

如果你的仓库已经使用不同的文件名（例如 `TEAM_GUIDE.md`），将其添加到回退列表，以便 Codex 将其视为指令文件：

```toml
# ~/.codex/config.toml
project_doc_fallback_filenames = ["TEAM_GUIDE.md", ".agents.md"]
project_doc_max_bytes = 65536
```

现在 Codex 按此顺序检查每个目录：`AGENTS.override.md`、`AGENTS.md`、`TEAM_GUIDE.md`、`.agents.md`。

### 自定义 CODEX_HOME

设置 `CODEX_HOME` 环境变量当你想要不同的配置文件时：

```bash
CODEX_HOME=$(pwd)/.codex codex exec "List active instruction sources"
```

### 故障排除

| 问题 | 解决方案 |
|------|----------|
| **没有加载任何内容** | 验证你在预期的仓库中，确保指令文件包含内容；Codex 忽略空文件 |
| **错误的指导出现** | 查找目录树中更高位置或 Codex 主目录下的 `AGENTS.override.md` |
| **Codex 忽略回退名称** | 确认在 `project_doc_fallback_filenames` 中列出的名称没有拼写错误，然后重启 Codex |
| **指令被截断** | 提高 `project_doc_max_bytes` 或将大文件拆分到嵌套目录中 |
| **配置文件混淆** | 在启动 Codex 前运行 `echo $CODEX_HOME` |

---

## 3. Agent Skills - 技能扩展

使用 agent skills 为 Codex 扩展任务特定的能力。技能打包了指令、资源和可选脚本，以便 Codex 可以可靠地遵循工作流程。你可以在团队之间或与社区共享技能。

### 渐进式披露

技能使用**渐进式披露**来高效管理上下文：Codex 从每个技能的元数据（`name`、`description`、文件路径和来自 `agents/openai.yaml` 的可选元数据）开始。只有当 Codex 决定使用技能时，才会加载完整的 `SKILL.md` 指令。

### 技能目录结构

```
- my-skill/
  - SKILL.md          # Required: instructions + metadata
  - scripts/          # Optional: executable code
  - references/       # Optional: documentation
  - assets/           # Optional: templates, resources
  - agents/
    - openai.yaml     # Optional: appearance and dependencies
```

`SKILL.md` 文件必须包含 `name` 和 `description`。

### 技能激活方式

1. **显式调用**：在提示中直接包含技能。在 CLI/IDE 中，运行 `/skills` 或输入 `$` 来提及技能。
2. **隐式调用**：当你的任务匹配技能 `description` 时，Codex 可以选择一个技能。

因为隐式匹配取决于 `description`，所以要编写具有清晰范围和边界的描述。

### 创建技能

首先使用内置的创建器：

```bash
$skill-creator
```

创建器会询问技能做什么、何时触发，以及是保持纯指令还是包含脚本。

你也可以手动创建一个包含 `SKILL.md` 文件的文件夹：

```markdown
---
name: skill-name
description: Explain exactly when this skill should and should not trigger.
---

Skill instructions for Codex to follow.
```

### 技能发现位置

| 技能作用域 | 位置 | 建议用途 |
|-----------|------|----------|
| `REPO` | `$CWD/.agents/skills` | 与工作文件夹相关的技能 |
| `REPO` | `$CWD/../.agents/skills` | 与共享区域相关的技能 |
| `REPO` | `$REPO_ROOT/.agents/skills` | 仓库中任何人都可用的根技能 |
| `USER` | `$HOME/.agents/skills` | 适用于用户可能工作的任何仓库的技能 |
| `ADMIN` | `/etc/codex/skills` | SDK 脚本、自动化、默认管理技能 |
| `SYSTEM` | Codex 内置 | 广泛受众的有用技能（如 skill-creator） |

### 安装技能

使用 `$skill-installer` 安装内置之外的技能：

```bash
$skill-installer linear
```

### 禁用技能

在 `~/.codex/config.toml` 中使用 `[[skills.config]]` 条目禁用技能而不删除它：

```toml
[[skills.config]]
path = "/path/to/skill/SKILL.md"
enabled = false
```

### 高级配置 (agents/openai.yaml)

添加 `agents/openai.yaml` 来配置 UI 元数据、设置调用策略和声明工具依赖：

```yaml
interface:
  display_name: "Optional user-facing name"
  short_description: "Optional user-facing description"
  icon_small: "./assets/small-logo.svg"
  icon_large: "./assets/large-logo.png"
  brand_color: "#3B82F6"
  default_prompt: "Optional surrounding prompt to use the skill with"

policy:
  allow_implicit_invocation: false

dependencies:
  tools:
    - type: "mcp"
      value: "openaiDeveloperDocs"
      description: "OpenAI Docs MCP server"
      transport: "streamable_http"
      url: "https://developers.openai.com/mcp"
```

**`allow_implicit_invocation`**（默认 `true`）：当为 `false` 时，Codex 不会根据用户提示隐式调用技能；显式 `$skill` 调用仍然有效。

### 最佳实践

- 保持每个技能专注于一个任务
- 除非需要确定性行为或外部工具，否则优先使用指令而非脚本
- 编写具有明确输入和输出的命令式步骤
- 针对技能描述测试提示以确认正确的触发行为

---

## 4. Subagents - 子代理协作

Codex 可以通过并行生成专门的子代理（subagents）来运行子代理工作流，然后在一个响应中收集它们的结果。这对于高度并行的复杂任务特别有帮助，例如代码库探索或实现多步骤功能计划。

通过子代理工作流，你还可以定义自己的**自定义代理（custom agents）**，根据任务配置不同的模型和指令。

> **注意**：当前 Codex 版本**默认启用**子代理工作流，无需额外配置。

### 核心概念

- **显式触发**：Codex 只在你明确要求时才生成子代理
- **Token 消耗**：每个子代理独立执行模型和工具工作，因此子代理工作流比单代理运行消耗更多 token
- **编排自动化**：Codex 处理代理间的编排，包括生成新子代理、路由后续指令、等待结果和关闭代理线程
- **结果合并**：当多个代理运行时，Codex 等待所有结果可用后返回合并响应

### 内置代理

Codex 内置以下代理：

| 代理名称 | 用途 |
|---------|------|
| `default` | 通用回退代理 |
| `worker` | 专注于执行的代理，用于实现和修复 |
| `explorer` | 重读取的代码库探索代理 |

### 基本用法示例

```
I would like to review the following points on the current PR (this branch vs main).
Spawn one agent per point, wait for all of them, and summarize the result for each point.
1. Security issue
2. Code quality
3. Bugs
4. Race
5. Test flakiness
6. Maintainability of the code
```

### 交互命令

- 使用 `/agent` 在 CLI 中切换活动代理线程并检查正在进行的线程
- 直接要求 Codex 引导正在运行的子代理、停止它或关闭已完成的代理线程

### 全局设置

在配置文件的 `[agents]` 部分配置全局子代理设置：

| 字段 | 类型 | 必需 | 用途 |
|------|------|------|------|
| `agents.max_threads` | number | No | 同时打开的代理线程最大数量（默认 `6`） |
| `agents.max_depth` | number | No | 生成的代理嵌套深度（根会话从 0 开始，默认 `1`） |
| `agents.job_max_runtime_seconds` | number | No | `spawn_agents_on_csv` 作业的每个工作器默认超时（默认 1800 秒） |

---

## 自定义代理（Custom Agents）

要定义自己的自定义代理，在以下位置添加独立的 TOML 文件：
- `~/.codex/agents/` - 个人代理
- `.codex/agents/` - 项目范围代理

每个文件定义一个自定义代理。Codex 通过 `name` 字段识别代理。

### 自定义代理文件 Schema

| 字段 | 类型 | 必需 | 用途 |
|------|------|------|------|
| `name` | string | **是** | Codex 在生成或引用此代理时使用的代理名称 |
| `description` | string | **是** | 人类面向的指导，说明何时使用此代理 |
| `developer_instructions` | string | **是** | 定义代理行为的核心指令 |
| `nickname_candidates` | string[] | No | 生成的代理的可选显示昵称池 |

可选字段（省略时从父会话继承）：
- `model`：使用的模型
- `model_reasoning_effort`：推理努力程度
- `sandbox_mode`：沙箱模式
- `mcp_servers`：MCP 服务器配置
- `skills.config`：技能配置

> **注意**：如果自定义代理名称匹配内置代理（如 `explorer`），你的自定义代理优先。

### 显示昵称（nickname_candidates）

使用 `nickname_candidates` 为生成的代理分配更易读的显示名称。这在运行多个相同自定义代理实例时特别有用，可以让 UI 显示不同的标签。

```toml
name = "reviewer"
description = "PR reviewer focused on correctness, security, and missing tests."
developer_instructions = """
Review code like an owner.
Prioritize correctness, security, behavior regressions, and missing test coverage.
"""
nickname_candidates = ["Atlas", "Delta", "Echo"]
```

昵称仅用于显示，Codex 仍通过 `name` 识别和生成代理。

---

## spawn_agents_on_csv 批量任务

当你有许多类似任务可以表示为每个工作项一行时，使用 `spawn_agents_on_csv`。Codex 读取 CSV，每行生成一个工作子代理，等待整批完成，并将合并结果导出到 CSV。

**适用于：**
- 每行审查一个文件、包或服务
- 检查事件、PR 或迁移目标列表
- 为许多类似输入生成结构化摘要

**工具参数：**
- `csv_path`：源 CSV
- `instruction`：工作提示模板，使用 `{column_name}` 占位符
- `id_column`：当你想从特定列获取稳定的项目 ID 时
- `output_schema`：当每个工作器应返回具有固定形状的 JSON 对象时
- `output_csv_path`、`max_concurrency`、`max_runtime_seconds`：作业控制

每个工作器必须调用 `report_agent_job_result` 一次。如果工作器退出时未报告结果，Codex 在导出的 CSV 中将该行标记为错误。

**示例提示：**

```
Create /tmp/components.csv with columns path,owner and one row per frontend component.

Then call spawn_agents_on_csv with:
- csv_path: /tmp/components.csv
- id_column: path
- instruction: "Review {path} owned by {owner}. Return JSON with keys path, risk, summary, and follow_up via report_agent_job_result."
- output_csv_path: /tmp/components-review.csv
- output_schema: an object with required string fields path, risk, summary, and follow_up
```

---

## 示例：PR 审查团队

此模式将审查分为三个专注的自定义代理：
- `pr_explorer`：映射代码库并收集证据
- `reviewer`：查找正确性、安全性和测试风险
- `docs_researcher`：通过专用 MCP 服务器检查框架或 API 文档

**项目配置 (`.codex/config.toml`)：**

```toml
[agents]
max_threads = 6
max_depth = 1
```

**`.codex/agents/pr-explorer.toml`：**

```toml
name = "pr_explorer"
description = "Read-only codebase explorer for gathering evidence before changes are proposed."
model = "gpt-5.3-codex-spark"
model_reasoning_effort = "medium"
sandbox_mode = "read-only"
developer_instructions = """
Stay in exploration mode.
Trace the real execution path, cite files and symbols, and avoid proposing fixes unless the parent agent asks for them.
Prefer fast search and targeted file reads over broad scans.
"""
```

**`.codex/agents/reviewer.toml`：**

```toml
name = "reviewer"
description = "PR reviewer focused on correctness, security, and missing tests."
model = "gpt-5.4"
model_reasoning_effort = "high"
sandbox_mode = "read-only"
developer_instructions = """
Review code like an owner.
Prioritize correctness, security, behavior regressions, and missing test coverage.
Lead with concrete findings, include reproduction steps when possible, and avoid style-only comments unless they hide a real bug.
"""
```

**`.codex/agents/docs-researcher.toml`：**

```toml
name = "docs_researcher"
description = "Documentation specialist that uses the docs MCP server to verify APIs and framework behavior."
model = "gpt-5.3-codex-spark"
model_reasoning_effort = "medium"
sandbox_mode = "read-only"
developer_instructions = """
Use the docs MCP server to confirm APIs, options, and version-specific behavior.
Return concise answers with links or exact references when available.
Do not make code changes.
"""

[mcp_servers.openaiDeveloperDocs]
url = "https://developers.openai.com/mcp"
```

**使用提示：**

```
Review this branch against main. Have pr_explorer map the affected code paths,
reviewer find real risks, and docs_researcher verify the framework APIs that the patch relies on.
```

---

## 示例：前端集成调试

此模式对于 UI 回归、不稳定的浏览器流程或跨越应用程序代码和运行产品的集成错误很有用。

**`.codex/agents/code-mapper.toml`：**

```toml
name = "code_mapper"
description = "Read-only codebase explorer for locating the relevant frontend and backend code paths."
model = "gpt-5.3-codex-spark"
model_reasoning_effort = "medium"
sandbox_mode = "read-only"
developer_instructions = """
Map the code that owns the failing UI flow.
Identify entry points, state transitions, and likely files before the worker starts editing.
"""
```

**`.codex/agents/browser-debugger.toml`：**

```toml
name = "browser_debugger"
description = "UI debugger that uses browser tooling to reproduce issues and capture evidence."
model = "gpt-5.4"
model_reasoning_effort = "high"
sandbox_mode = "workspace-write"
developer_instructions = """
Reproduce the issue in the browser, capture exact steps, and report what the UI actually does.
Use browser tooling for screenshots, console output, and network evidence.
Do not edit application code.
"""

[mcp_servers.chrome_devtools]
url = "http://localhost:3000/mcp"
startup_timeout_sec = 20
```

**`.codex/agents/ui-fixer.toml`：**

```toml
name = "ui_fixer"
description = "Implementation-focused agent for small, targeted fixes after the issue is understood."
model = "gpt-5.3-codex-spark"
model_reasoning_effort = "medium"
developer_instructions = """
Own the fix once the issue is reproduced.
Make the smallest defensible change, keep unrelated files untouched, and validate only the behavior you changed.
"""

[[skills.config]]
path = "/Users/me/.agents/skills/docs-editor/SKILL.md"
enabled = false
```

**使用提示：**

```
Investigate why the settings modal fails to save. Have browser_debugger reproduce it,
code_mapper trace the responsible code path, and ui_fixer implement the smallest fix once the failure mode is clear.
```

---

## 安全与沙箱

- **沙箱继承**：子代理继承你当前的沙箱策略
- **批准请求**：在交互式 CLI 会话中，批准请求可以从非活动代理线程浮出水面。批准覆盖层显示来源线程标签，你可以按 `o` 在批准/拒绝/回答请求前打开该线程
- **非交互流程**：在非交互流程中，需要新批准的操作会失败，错误会返回到父工作流
- **运行时覆盖**：Codex 在生成子代理时重新应用父轮次的实时运行时覆盖，包括你在会话期间交互设置的沙箱和批准选择（如 `/approvals` 更改或 `--yolo`），即使选定的自定义代理文件设置了不同的默认值
- **代理级覆盖**：你也可以为单个自定义代理覆盖沙箱配置，例如显式标记一个代理为只读模式

---

## 总结

| 功能 | 用途 | 关键文件 |
|------|------|----------|
| **Rules** | 控制命令执行权限 | `~/.codex/rules/default.rules` |
| **AGENTS.md** | 项目和全局指令 | `AGENTS.md`、`AGENTS.override.md` |
| **Skills** | 扩展 Codex 能力 | `.agents/skills/*/SKILL.md` |
| **Subagents** | 并行子代理协作 | `~/.codex/agents/*.toml`、`.codex/agents/*.toml` |
