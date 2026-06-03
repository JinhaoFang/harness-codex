# Codex Harness 用户指南

这是一套给 AI 编码 Agent（Claude Code / Codex 等）做长程任务执行使用的工程纪律框架。它不改变你的代码逻辑，而是让 Agent 的工作变得**可追溯、可验证、可恢复**。

## 为什么需要它

AI Agent 写代码时常见的问题：改着改着偏离了原始意图、说"完成了"但没有证据、跨会话丢失上下文、静默扩大改动范围。Harness 通过一个核心机制解决这些问题——**把工作变成有明确契约的 Work Unit**，然后通过 CLI 控制器、hooks 自动防护、skills 引导、和 CI gate 共同强制执行。

---

## 1. 核心概念

### Work Unit（工作单元）

每一个非平凡任务都是一个 Work Unit。它的契约（Contract）包含：

- **意图和范围**——做什么、不做什么
- **写边界**——只能改哪些文件
- **需要的证据**——怎么证明做完了
- **停止条件**——什么时候算成功、什么时候算卡住

### 证据（Evidence）

口头说"已完成"不算完成。每项声明都需要对应一条**新鲜证据**：测试通过、lint 通过、手动验证等。证据记录在 `evidence/receipts.jsonl` 中，包含命令、结果、新鲜度基准等。

**跳过的检查必须记录为 `skipped`，绝不能记为 `pass`。** 如果确实需要跳过，走 waiver 流程。

### 评审（Review）

评审由独立角色执行，判断实现是否满足 Contract。评审和证据是**两种不同的真值来源**——"看起来没问题"和"测试确实通过了"不能互相替代。实现者不能给自己的工作写 PASS 评审。

### 风险分级

| 风险 | 典型场景 | 需要什么 |
|---|---|---|
| trivial | 注释、小文档 | 自查即可 |
| low | 本地 bugfix | Work Unit 备注 + 新鲜证据 |
| medium | 多文件改动、用户可见行为 | 完整 Contract + 证据收据 + close 评审 + handoff |
| high | 认证、权限、迁移、安全 | 回滚路径 + 证据收据 + 独立评审或人工审批 |
| critical | 生产数据、外部客户影响、合规 | 锁定 Contract + 爆炸半径 + 回滚证明 + 强制人工审批 + 审计记录 |

高风险触发器：生产数据库操作、租户隔离/RLS/认证/权限逻辑、密钥/凭证轮换、计费/支付、迁移/部署/回滚路径、大规模删除、影响客户的行为、隐私/法律/合规/审计面。

**原理**：风险越高，需要的不变量越多。这不是官僚主义，而是确保 Agent 改权限逻辑时有人类兜底。

---

## 2. 安装与配置

### 安装

```bash
# Claude Code 用户
python3 scripts/adopt.py install /path/to/your-project --profile claude

# Codex 用户
python3 scripts/adopt.py install /path/to/your-project --profile codex

```

安装是**增量**的：已有文件不会被覆盖，只补充缺失的部分。

### 安装后的目录结构

```
your-project/
├── CLAUDE.md              # (claude profile) Agent 项目入口指南
├── AGENTS.md              # (codex profile)  Agent 项目入口指南
├── .claude/               # (claude profile)
│   ├── settings.json      #   权限配置 + hooks 接线
│   ├── agents/            #   worker.md / reviewer.md 子 agent 定义
│   └── skills/            #   Claude 原生 skill（从 skills/ 同步而来）
├── .codex/                # (codex profile)
│   ├── config.toml        #   Codex 配置
│   ├── hooks.json         #   hooks 接线
│   ├── agents/            #   worker.toml / reviewer.toml 子 agent 定义
│   └── skills/            #   Codex 原生 skill（从 skills/ 同步而来）
├── .harness/              # 运行时状态
│   ├── config.json        #   全局配置
│   ├── current            #   当前活跃 Work Unit ID
│   └── work-units/
│       ├── active/        #   活跃的 Work Unit 目录
│       └── archive/       #   已归档的 Work Unit
├── harness/               # Harness 核心
│   ├── cli/harnessctl.py  #   生命周期控制器 CLI
│   ├── hooks/             #   自动防护脚本
│   ├── schemas/           #   artifact JSON schemas
│   ├── templates/         #   Contract / handoff / review 模板
│   └── tests/             #   控制器测试
├── skills/                # 平台无关的 skill 目录（可编辑的源头）
├── docs/harness/          # 详细生命周期文档
└── .github/workflows/     # CI 检查
```

### 全局配置：.harness/config.json

安装时自动生成，通常不需要手动编辑：

```json
{
  "schema_version": "harness.config.v1",
  "profile": "claude",
  "work_units_dir": ".harness/work-units",
  "default_required_gates": ["spec", "verification"],
  "high_risk_requires": ["independent_review_or_human_gate", "rollback_or_reopen_path"]
}
```

可配置项说明：

| 字段 | 说明 |
|---|---|
| `default_required_gates` | 所有 Work Unit 默认需要通过的 gate。默认是 `spec`（Contract 完整性）和 `verification`（证据充分性） |
| `high_risk_requires` | 高风险任务额外要求。默认要求独立评审或人工 gate、以及回滚/重开路径 |

### 权限配置（Claude Code）

`.claude/settings.json` 中预设了三级权限控制：

| 级别 | 示例 | 效果 |
|---|---|---|
| **deny** | `rm -rf /`、`git push --force`、直接 push 到 main | 直接拒绝，不可执行 |
| **ask** | `git push`、`terraform apply`、`npm publish` | 需要用户明确确认 |
| **allow** | `harnessctl` 命令、`git status`、`Read`/`Grep`/`Glob` | 自动放行 |

你可以根据项目需要调整这些规则。合并到已有项目的 settings.json 时注意保留原有配置。

### 权限配置（Codex）

Codex 通过 `.codex/hooks.json` 和 `sandbox_mode` 控制类似的安全策略。PreToolUse hook 只做 deny 或静默，不返回 ask 类决策——ask 行为由 Codex 原生的 PermissionRequest 流程处理。

---

## 3. 工作流程

一个典型 Work Unit 的完整生命周期：

```
澄清 → 创建 Contract → 锁定 → 实现(TDD) → 收集证据 → 评审 → 交接或归档
                                        ↑                    |
                                        └──── 失败时 compound ┘
```

### 第 1 步：澄清需求

Agent 不会在你意图不明时就开始写代码。`harness-clarify` skill 引导 Agent：

1. 重述当前理解（交付物、可观测效果、完成定义）
2. 检查项目上下文（代码、测试、配置、运行时）
3. 识别决策缺口（范围、约束、写边界、证据、审批条件）
4. 每次只问一个高价值问题，给出 2-3 个具体选项
5. 产出确认摘要，交给 `harness-spec`

核心原则：**能通过检查仓库回答的问题，不要问用户。** 只问人类意图、产品权衡、风险接受、范围决策。

### 第 2 步：创建 Work Unit Contract

```bash
# 创建新 Work Unit
python3 harness/cli/harnessctl.py new \
  --id WU-001 \
  --title "修复登录过期后的重定向" \
  --type bugfix \
  --risk medium
```

`--type` 可选值：`feature` / `bugfix` / `refactor` / `migration` / `docs` / `test` / `release` / `security` / `research` / `other`

这会在 `.harness/work-units/active/WU-001/` 下生成完整的目录结构：

```
WU-001/
├── contract.md           # 契约（Agent 填写）
├── state.json            # 生命周期状态
├── handoff.md            # 交接文档（初始为空）
├── amendments.jsonl      # 契约变更记录
├── evidence/
│   └── receipts.jsonl    # 证据收据
├── reviews/              # 评审记录
└── waivers/              # 豁免记录
```

Agent 会用 `harness-spec` skill 填写 contract.md 的各个部分：意图、预期结果、非目标、范围（可能改动的区域、写边界、禁止触碰的区域）、所需证据、停止条件、澄清记录、开放问题、上下文指针、风险备注。

### 第 3 步：锁定 Contract

```bash
# 先检查 spec gate（确保 Contract 完整）
python3 harness/cli/harnessctl.py check --id WU-001 --gate spec --strict

# 通过后锁定
python3 harness/cli/harnessctl.py lock --id WU-001 --status ready
```

spec gate 会检查：必填标题是否完整、有没有 TBD/TODO 占位符、风险级别是否有效、澄清记录是否完整、高风险是否有风险备注等。

锁定后 Contract 的意图、范围、风险、证据要求、成功标准、停止条件不可静默漂移。

#### 变更已锁定的 Contract

如果需要修改，必须通过 `amend` 记录变更并分类影响：

```bash
python3 harness/cli/harnessctl.py amend \
  --id WU-001 \
  --field scope \
  --impact scope_or_risk \
  --reason "新增一个需要改动的模块" \
  --summary "写边界从 auth/ 扩展到 auth/ + middleware/"
```

`--field` 可选值：`intent` / `scope` / `required_evidence` / `risk` / `success` / `stop_conditions` / `context` / `other`

`--impact` 分类决定了后续需要做什么：

| 影响类型 | 需要重新 plan review? | 影响实现? | 影响验收? | 推荐后续 review |
|---|---|---|---|---|
| `context_only` | 否 | 否 | 否 | 无 |
| `collaboration_only` | 否 | 否 | 是 | publication |
| `evidence_only` | 否 | 否 | 是 | close-addendum |
| `success_criteria` | 是 | 否 | 是 | close-addendum 或 close |
| `scope_or_risk` | 是 | 是 | 是 | close |
| `implementation` | 是 | 是 | 是 | close |

**原理**：不是所有变更都需要重来。如果只是补充了上下文（`context_only`），不需要重跑评审。但如果范围变了（`scope_or_risk`），实现和验收都会受影响，必须重新完整评审。

### 第 4 步：建立上下文

`harness-ground` skill 引导 Agent 按固定顺序读取上下文：

1. 当前 Work Unit Contract 或 issue 规范
2. 项目入口指南（`CLAUDE.md` / `AGENTS.md`）
3. 可能改动路径附近的局部规则
4. 代码、测试、配置、运行时日志、生成的 artifact
5. Contract 或涉及区域引用的 ADR/文档
6. 平台/API 行为的官方外部文档

产出格式：

```
已确认的事实:
检查的文件/符号:
相关已有测试:
文档/代码冲突:
风险和未知:
推荐的上下文指针:
下一步合法操作:
```

### 第 5 步：实现（TDD）

`harness-tdd` skill 引导行为驱动开发：

1. **RED**：为单个可观测行为写一个测试
2. 运行，确认测试因预期原因失败
3. **GREEN**：实现最小垂直切片
4. 重新运行，确认通过
5. **REFACTOR**：只在绿灯状态下重构；重构后重新验证
6. 记录证据

测试选择指南：

| 场景 | 测试类型 |
|---|---|
| Bug 修复 | 先复现 bug |
| 公共行为 | 行为/集成测试 |
| API/CLI/Schema | 契约测试 |
| 错误/权限 | 负面/错误路径测试 |
| 状态机/生命周期 | 状态转换测试 |
| 多组件流程 | 端到端/运行时检查 |

TDD 不适用于：纯文档、机械重命名、生成的快照、探索性 spike。这些情况写明确的证据计划或 waiver。

### 第 6 步：收集证据

```bash
# 通过的证据
python3 harness/cli/harnessctl.py evidence \
  --id WU-001 \
  --claim EV1 \
  --type test \
  --result pass \
  --command "pytest tests/test_login.py -v" \
  --command-log-ref ".harness/work-units/active/WU-001/evidence/artifacts/login-test.txt"

# 跳过的证据（必须附带说明）
python3 harness/cli/harnessctl.py evidence \
  --id WU-001 \
  --claim EV2 \
  --type test \
  --result skipped \
  --note "E2E 测试需要浏览器环境，本地无法运行；由 CI 覆盖"
```

`evidence` 命令的完整参数：

| 参数 | 说明 |
|---|---|
| `--claim` | 对应 Contract 中的证据 ID（如 EV1） |
| `--type` | 证据类型，默认 `test` |
| `--result` | `pass` / `fail` / `skipped`（必填） |
| `--command` | 产生证据的命令 |
| `--command-log-ref` | 命令输出日志引用 |
| `--artifact-uri` | 产物链接 |
| `--artifact-hash` | 产物哈希 |
| `--manual-artifact-ref` | 手动验证产物的引用 |
| `--environment-ref` | 测试环境标识 |
| `--actor` | 谁产生的：`agent` / `controller` / `ci` / `human` / `reviewer` |
| `--exit-code` | 进程退出码 |
| `--covers` | 覆盖范围（可多次指定） |
| `--verification-scope` | 验证范围，默认 `files` |
| `--freshness-basis` | 新鲜度基准，默认 `diff_hash` |
| `--note` | 附加说明（`--result skipped` 时必填） |

#### 证据新鲜度

证据绑定了 git 状态（diff_hash、changed_files）。当实现代码变化后，之前的证据可能不再"新鲜"。但以下变化**不会**导致证据失效：

- evidence receipt ID 变化
- commit 创建/squash/rebase（实现 diff 不变时）
- CI 重新运行
- handoff/archive/state 文件更新
- GitHub issue/PR 元数据变化

**原理**：评审有效性基于**实现 diff 这个面**，而不是 artifact ID。只要改的代码没变，证据刷新、提交重整、CI 重跑都不应该强制重新评审。

#### 验证 gate

收集完证据后运行：

```bash
python3 harness/cli/harnessctl.py validate --id WU-001 --strict
python3 harness/cli/harnessctl.py check --id WU-001 --gate verification --strict
```

### 第 7 步：评审

Harness 支持 8 种评审模式：

| 模式 | 何时用 | 检查什么 |
|---|---|---|
| `plan` | 实现前 | Contract 是否 grounded，执行计划是否合理 |
| `close` | 实现后，归档前 | diff、证据、范围、风险、可维护性 |
| `close-addendum` | 验收判断发生轻量变更时 | 仅变更的判断点，不重跑完整 close review |
| `publication` | 发 GitHub issue/PR 时 | 协作面就绪性，不替代实现 close review |
| `risk` | 风险聚焦 | 风险缓解措施 |
| `security` | 安全聚焦 | 安全面审查 |
| `architecture` | 架构聚焦 | 架构决策审查 |
| `evaluator` | 评估 | HEB 评估 |

**对 medium 及以上风险**：实现前需要 plan review，实现后需要 close review。
**对 high/critical 风险**：需要独立评审（`independence_level` 为 `separate_role`、`fresh_context` 或 `human_gate`）。

#### 评审流程

```bash
# 1. 请求评审
python3 harness/cli/harnessctl.py request-review --id WU-001 --mode close

# 2. Agent（作为 reviewer 角色）执行评审后提交
python3 harness/cli/harnessctl.py submit-review \
  --id WU-001 \
  --mode close \
  --decision PASS \
  --reviewer-role reviewer-agent \
  --independence-level fresh_context \
  --evidence-ref receipt-20260603-EV1 \
  --finding "范围符合 contract，证据充分"

# 3. 检查评审 gate
python3 harness/cli/harnessctl.py check --id WU-001 --gate review --strict
```

`submit-review` 的决策选项：

| 决策 | 含义 |
|---|---|
| `PASS` | 通过 |
| `PASS_WITH_RISK_ACCEPTED` | 通过，但附带已接受的风险 |
| `CHANGES_REQUESTED` | 需要修改 |
| `REJECTED` | 拒绝 |
| `BLOCKED` | 阻塞 |
| `NEEDS_HUMAN_GATE` | 需要人类审批 |

评审独立性级别：

| 级别 | 说明 |
|---|---|
| `self_check` | 自查（仅 trivial/low 使用） |
| `separate_role` | 不同角色评审（worker 实现，reviewer 评审） |
| `fresh_context` | 新上下文评审 |
| `human_gate` | 人类审批 |

### 第 8 步：交接或归档

#### 归档前检查

```bash
# finalize-check 一次性收集所有 gate 状态和操作指引
python3 harness/cli/harnessctl.py finalize-check --id WU-001 --strict
```

`finalize-check` 输出包含：
- 实现面状态（unchanged/changed/unknown）
- 证据面状态（accepted_by_implementation_equivalence/fresh_pass/rerun_required）
- 评审面状态（review_required/valid_or_not_required）
- 发布面状态（required/not_required_or_satisfied）
- 推荐的下一步操作和禁止的操作

**原理**：`finalize-check` 是归档前的统一出口，避免你手动解读多个 gate 的结果来决定能不能归档。Agent 应该遵循它的 action 字段，而不是自行从 HEAD 变化推断出新工作。

#### 归档

```bash
# 直接归档（本地工作完成）
python3 harness/cli/harnessctl.py archive --id WU-001 --no-next-step-reason "本地实现和评审完成"

# 强制归档（跳过 gate 检查，慎用）
python3 harness/cli/harnessctl.py archive --id WU-001 --force
```

#### 交接（跨会话继续工作）

```bash
python3 harness/cli/harnessctl.py handoff --id WU-001 --next-safe-action "运行验证 gate，然后请求 close review"
```

交接文档（`handoff.md`）包含：当前目标、状态、分支/HEAD/diff hash、已改动文件、最新证据、已知失败、阻塞项、开放问题、下一步安全操作、回滚/重开路径。

**原理**：交接文档由 controller 从权威 artifact（Contract、state、evidence、review）生成，而不是从聊天摘要生成。这保证了跨会话恢复时信息不会因为上下文压缩而丢失。

---

## 4. CLI 控制器完整参考

`harnessctl` 是 Harness 的唯一生命周期管理入口。所有命令通过 `python3 harness/cli/harnessctl.py <command>` 调用。

### Work Unit 管理

| 命令 | 说明 | 关键参数 |
|---|---|---|
| `init` | 初始化 harness 运行时 | `--profile codex/claude` |
| `new` | 创建新 Work Unit | `--id`（必填）、`--title`（必填）、`--type`、`--risk` |
| `list` | 列出所有 Work Unit | 无 |
| `status` | 查看完整状态 JSON | `--id` |
| `brief` | 简洁摘要（Contract + 证据 + 评审） | `--id` |
| `lock` | 锁定 Contract | `--id`、`--status specified/ready` |
| `amend` | 记录 Contract 变更 | `--id`、`--field`、`--impact`、`--reason`、`--summary`、`--allow-draft` |
| `set-state` | 手动设置状态（低级别） | `--id`、`--status`、`--next-safe-action` |

### 证据与验证

| 命令 | 说明 | 关键参数 |
|---|---|---|
| `evidence` | 记录证据收据 | `--claim`、`--result`、`--command`、`--command-log-ref`、`--artifact-uri`、`--note` 等 |
| `validate` | 验证 artifact 格式完整性 | `--id`、`--all`（验证所有 WU）、`--strict` |
| `check` | 运行指定 gate | `--id`、`--gate spec/scope/verification/plan-review/review/archive/skills`、`--strict` |

### 评审

| 命令 | 说明 | 关键参数 |
|---|---|---|
| `request-review` | 请求评审 | `--id`、`--mode plan/close/close-addendum/publication/risk/security/architecture/evaluator`、`--reviewer-role` |
| `submit-review` | 提交评审结论 | `--id`、`--mode`、`--decision`、`--reviewer-role`、`--independence-level`、`--evidence-ref`、`--finding`、`--required-rework` |

### 生命周期

| 命令 | 说明 | 关键参数 |
|---|---|---|
| `handoff` | 生成交接文档 | `--id`、`--next-safe-action`（必填） |
| `archive` | 归档 Work Unit | `--id`、`--force`、`--no-next-step-reason` |
| `finalize-check` | 归档前汇总所有 gate | `--id`、`--strict` |
| `ci` | CI 级别验证所有活跃 WU | `--strict`、`--require-active` |

### 维护

| 命令 | 说明 | 关键参数 |
|---|---|---|
| `doctor` | 健康检查 | 无 |
| `waiver` | 创建豁免 | `--id`、`--waiver-type evidence/risk/scope/deadline`、`--approved-by`（必须 `human:xxx`）、`--requirement`、`--reason`、`--risk-accepted`、`--expires-at` |

### 通用参数

| 参数 | 说明 |
|---|---|
| `--root` | 指定仓库根目录（默认当前目录） |
| `--id` | 指定 Work Unit ID（不指定则使用 `.harness/current` 中的当前 WU） |
| `--strict` | 阻塞时返回退出码 2（CI 场景使用） |

### Work Unit 状态流转

```
draft → specified → ready → running → verifying → reviewing → handoff → archived
                                            ↕              ↕
                                         blocked        integrating
```

| 状态 | 含义 |
|---|---|
| `draft` | Contract 正在编写 |
| `specified` | Contract 完成，已锁定 |
| `ready` | Plan review 通过，准备实现 |
| `running` | 实现中 |
| `verifying` | 收集证据中 |
| `reviewing` | 评审中 |
| `integrating` | 集成/合并中 |
| `handoff` | 准备交接 |
| `archived` | 已归档 |
| `blocked` | 被外部依赖阻塞 |

---

## 5. Skills

Harness 提供 10 个平台无关的 skill，每个对应生命周期的一个环节。它们位于 `skills/` 目录，安装时同步到 `.claude/skills/` 或 `.codex/skills/`。

**Skill 引导工作流并调用 controller，但不拥有生命周期状态。** 状态始终由 `.harness/` 目录和 `harnessctl` 管理。

### harness-clarify — 澄清需求

在动手前澄清模糊或非平凡的编码工作。

- 通过仓库探索回答事实性问题，只向用户问人类意图类问题
- 每次只问一个高价值问题，附带 2-3 个具体选项
- 立即暴露冲突（用户意图 vs 仓库行为、术语冲突、不可能的证据、范围越界）
- 最终产出确认摘要（交付物、可观测效果、完成定义、非目标、写边界、所需证据、审批条件、已解决决策、剩余假设）

### harness-spec — 创建/锁定/修改 Contract

将澄清结果转化为 Work Unit Contract。

- 从 `harnessctl new` 创建 WU，填写 contract.md
- 运行 spec gate 后锁定
- 如果需要修改已锁定的 Contract，通过 `harnessctl amend` 记录变更及影响分类

### harness-ground — 建立仓库上下文

在规划、实现或评审前，从仓库事实建立任务上下文。

- 按固定优先级顺序读取：Contract → 项目指南 → 局部规则 → 代码/测试 → ADR/文档 → 外部文档
- 如果文档与代码/运行时冲突，以上当前代码事实为准并暴露冲突

### harness-tdd — 行为驱动的 TDD

对有代码的开发工作应用行为驱动开发。

- RED → GREEN → REFACTOR 循环
- 每次只写一个测试切片
- 不在 RED 状态下重构，不在写边界外做 GREEN 改动
- 不适用于纯文档、机械重命名、生成快照、探索性 spike

### harness-evidence — 记录证据收据

捕获每项声明对应的证据。

- 记录通过或跳过的证据
- 跳过必须附带说明（跳过原因、替代证据、风险影响）
- 运行验证 gate 确认证据充分

### harness-review — 执行评审

从新鲜输入执行 plan/close/等评审。

- 输入是 Contract、diff、代码、测试、证据收据等——**不是** builder 的叙述或聊天记录
- plan review：实现前检查 Contract 是否 grounded
- close review：实现后检查 diff、证据、范围、风险
- close-addendum：仅在验收判断发生轻量变更时使用
- 评审有效性基于实现 diff 面，不基于 artifact ID

### harness-handoff — 生成交接文档

为跨会话、阻塞、评审转移、归档场景生成可恢复的交接。

- 从 controller 的权威 artifact 生成，不从聊天摘要生成
- 包含：目标、状态、分支/HEAD、改动文件、证据、失败、阻塞、下一步、回滚路径

### harness-waiver — 创建豁免

为缺失证据、跳过检查、风险接受或截止日期例外创建有人类审批的豁免。

```bash
python3 harness/cli/harnessctl.py waiver \
  --id WU-001 \
  --waiver-type evidence \
  --approved-by "human:alice" \
  --requirement EV3 \
  --reason "E2E 测试需要浏览器环境" \
  --replacement-evidence "CI 中对应测试通过" \
  --risk-accepted "发布前 CI 必须通过" \
  --expires-at "2026-07-01"
```

使用前确认：已将跳过记录为 `skipped` 而非 `pass`、豁免的 requirement 匹配缺失的证据 ID、审批者是人类、有到期/重审条件。

### harness-github — Issue / PR 协作

将 GitHub 作为协作面使用。

- 在 Work Unit 锁定和 plan review 通过后再创建 issue/PR
- 按风险级别决定是否需要 issue 和 PR

| 任务类别 | GitHub issue | PR/CI |
|---|---|---|
| trivial | 不需要 | 可选 |
| low | 可选 | PR 证据备注即可 |
| medium | 推荐 | PR 引用证据和 CI artifact |
| high | 必须 | 受保护 PR + 人工 gate |
| critical | 必须 | 受保护 PR + 审计 artifact |

分支命名：`wu/<WU-ID>-short-topic` 或 `issue-<number>-short-topic`

本地实现+评审+PR 完成后即可归档，不需要等远程 merge。

### harness-compound — 复合与裁剪

将重复失败、评审发现、失败交接、错误完成等转化为持久资产或裁剪决策。

可选决策：`none` / `docs` / `adr` / `test` / `lint` / `ci` / `permission` / `hook` / `skill` / `controller-check` / `workflow` / `evaluator-rubric` / `deletion`

添加或保留机制前必须回答：机制名称、目的、防护的不变量、失败模式、验证方法、已知代价、移除条件。

---

## 6. Hooks（自动防护）
> 目前 stop hooks 还不成熟，可以关闭使用。具体是在使用的过程中如果有激活的任务就会触发，即使你想要和 Agent 进行多轮交互也会触发，解决办法是触发后手动打断，或者不启动 stop hooks

Hooks 是在 Agent 生命周期特定节点自动运行的守卫脚本。你不需要手动调用它们。安装时已通过 `.claude/settings.json` 或 `.codex/hooks.json` 完成接线。

### Claude Code Hooks

| 事件 | Hook 脚本 | 做什么 |
|---|---|---|
| `SessionStart` | `context_router.py` | 恢复会话时自动注入当前活跃 Work Unit 的上下文摘要 |
| `UserPromptSubmit` | `context_router.py` | 每次提交 prompt 时检查是否有活跃 WU，提醒 Agent 按正确生命周期操作 |
| `PreToolUse` | `pre_tool_use_policy.py` | 在执行 Bash/Edit/Write 前拦截危险命令（`rm -rf /`、`git push --force`、直接 push 到 main 等） |
| `PostToolBatch` | `context_router.py` | 工具执行批处理后轻量上下文提醒 |
| `TaskCompleted` | `stop_without_evidence.py` | 阻止 Agent 在活跃 WU 有改动但缺少证据时标记任务完成 |
| `SubagentStart` | `context_router.py` | 注入 worker/reviewer 角色的输出协议 |
| `PreCompact` | `pre_compact_handoff_check.py` | 压缩上下文前检查：如果有活跃 WU 且有未提交改动但没有 handoff，阻止压缩 |
| `PostCompact` | `context_router.py` | 压缩后注入恢复上下文 |
| `Stop` | `stop_without_evidence.py` | 会话结束时检查活跃 WU 的 gate 是否通过 |

### Codex Hooks

| 事件 | Hook 脚本 | 做什么 |
|---|---|---|
| `SubagentStart` | `context_router.py` | 注入 worker/reviewer 角色上下文 |
| `PreCompact` | `pre_compact_handoff_check.py` | 压缩前确保 handoff 存在 |
| `PostCompact` | `context_router.py` | 压缩后注入恢复上下文 |
| `Stop` | `stop_without_evidence.py` | 阻止无证据完成 |
| `PermissionRequest` | `permission_request_policy.py` | Codex 专用的权限请求策略评估 |

可选扩展事件（Codex 默认不启用）：`SessionStart`、`UserPromptSubmit`、`PreToolUse`。

### Hook 脚本详解

#### context_router.py

多个事件共用。核心行为：
- 找到 harness 根目录（通过 `.harness/config.json` 定位）
- 读取 `.harness/current` 获取当前活跃 WU ID
- 加载 WU 状态，输出上下文信息：WU 状态、下一步安全操作、最近文件变更

#### stop_without_evidence.py

最关键的防护 hook：
1. 查找当前 WU 和 harness 根目录
2. 检查是否有非 harness 生命周期文件的 git 变更
3. 调用 `harnessctl finalize-check` 运行所有 gate
4. 根据结果决定放行还是阻塞，阻塞时给出具体的下一步操作命令

阻塞场景：
- 证据需要重跑（stale evidence）
- 需要评审（缺少 close review verdict）
- 需要发布面（缺少 GitHub 证据）
- 验证不通过（缺少证据）
- 评审不通过（缺少 close review）

#### pre_tool_use_policy.py / policy_common.py

命令安全策略评估。两级决策：

**直接拒绝（deny）**：
- `rm -rf /`、`rm -rf ~`
- `git reset --hard`
- `git push --force`
- 直接 push 到 `main`/`master`
- `drop database`、`truncate table`
- 涉及密钥/凭证的操作

**需要确认（ask）**：
- `npm/pnpm/yarn publish`
- `terraform/pulumi apply`
- `kubectl/helm apply/delete/upgrade`

#### pre_compact_handoff_check.py

防止上下文压缩导致工作丢失：
- 检查活跃 WU 是否有 git 变更
- 如果有变更但 `handoff.md` 不存在或未生成，阻止压缩
- 返回阻止原因和系统提示

#### session_end_handoff_check.py

会话结束时检查 handoff 是否存在。**仅警告，不阻止**。

#### hook_sound.py

macOS 上的音频反馈。`SubagentStart` 播放 Pop/Tink/Ping 声音，完成时播放 Hero/Glass/Ping 声音。

- 仅 macOS 有效，其他平台和 CI 环境自动静音
- 设置 `HARNESS_HOOK_SOUND=0` 可禁用

---

## 7. 子 Agent

Harness 预设了两个最小化的子 Agent 角色：

| 角色 | 沙箱 | 用途 |
|---|---|---|
| `harness_worker` | workspace-write | 在写边界内实现一个有界的 Work Unit |
| `harness_reviewer` | read-only | 从新鲜输入执行独立的 plan/close 评审 |

**不预设** planner、monitor、verifier、explorer 等角色——这些职责由 skills、controller gate、hooks 或普通任务路由覆盖，除非有真实的失败记录证明需要独立的隔离角色。

子 Agent 应接收精简的输入包：Work Unit Contract、当前 diff/路径列表、所需证据 ID、已知风险边界、明确的输出契约。不要把整个 `.harness` 历史发给子 Agent。

Claude Code 中定义在 `.claude/agents/`（Markdown 格式），Codex 中定义在 `.codex/agents/`（TOML 格式）。

---

## 8. CI 集成

`.github/workflows/harness-checks.yml` 提供以下 CI 检查：

- 运行 harness 测试
- 运行 `harnessctl doctor`
- 验证 harness artifact
- 运行生命周期 CI gate
- 运行 skill 目录 gate

CI gate 命令：

```bash
# 验证所有活跃 Work Unit
python3 harness/cli/harnessctl.py ci --strict

# 如果要求必须有活跃 WU 才能通过
python3 harness/cli/harnessctl.py ci --strict --require-active
```

---

## 9. 关键约束

1. **不能静默扩大范围**——如果需要改 Contract 之外的代码，必须先 amend
2. **不能给自己写 PASS 评审**——实现者和评审者必须是不同角色
3. **跳过不是通过**——skipped evidence 永远不是 pass
4. **没有证据不能完成**——除非有人工审批的 waiver
5. **危险操作需要审批**——force push、删库、部署等需要人类确认
6. **评审有效性基于实现 diff**——不是基于 artifact ID，证据刷新不等于需要重新评审
7. **GitHub 不是完成权威**——issue/PR 状态不替代 Contract、证据、评审 gate

这些约束不是靠 Agent 自觉遵守的，而是靠 hooks 自动拦截、权限配置强制确认、和 CI gate 共同执行。
