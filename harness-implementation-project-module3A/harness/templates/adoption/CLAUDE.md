# 项目指南 

## 0. 项目地图 (Project Map)

- **项目名称**：[在此处用一句话描述采用后的仓库]
- **主要运行时/技术栈**：[采用后更新]
- **主要校验命令**：[采用后更新]
- **高风险区域**：[采用后更新]
- **Harness 仓库级运行状态**：`.harness/config.json` 由 `harnessctl init` 生成；`.harness/current` 由 `harnessctl new` 等命令维护为当前工作单元指针。
- **Harness 工作单元状态**：`.harness/work-units/active/<WU-ID>/`
- `.harness/` 默认由 `harnessctl init` 写入 `.gitignore`；除非项目明确要求审计留存，否则不要把运行时状态当作稳定源码提交。
- **深度生命周期指南**：`docs/harness/`
- **可复用程序**：`skills` 。

## 1. 工作风格 (Working Style)

- **先思后行**：陈述假设，揭示模糊之处；当意图或风险不明时，主动提问。
- **严禁臆断**：不要掩盖困惑，应展示权衡方案（Tradeoffs）。
- **优先遵循 DRY 和 KISS 原则**：在添加抽象层之前优先复用现有路径；保持能解决当前“工作单元”的最简设计。
- **优先进行精准修改**：仅触动与“工作单元”直接相关的方案文件；不要进行投机性的重构或大规模的格式调整。
- **避免过度设计**：除非有明确要求，否则不要添加推测性的灵活性、无用的配置或面向未来的抽象。
- **仅删除由你自己改动产生的无用代码/引用**，除非有明确指令。

## 2. 规范制定前的澄清 (Clarify Before Spec)

对于每一个非琐碎（Non-trivial）的“工作单元”，“澄清（Clarify）”是第一道关卡，其权重高于编写规范（Spec）。

在起草或锁定“工作单元契约”之前：

- **立足于仓库现实（harness-ground）**：检查相关的入口点、测试、配置、本地规则和现有行为。
- **澄清用户意图（harness-clarify）**，直到满足以下两个条件：
  - 用户意图置信度达到至少 95%；
  - 对项目现状的了解置信度达到至少 95%。
- **明确界定**：交付目标、预期结果、非目标（Non-goals）、必须保留的约束、证据呈现方式、写入边界、阶段顺序、审批点、迁移/删除条件以及未解决的问题。
- 如果仍存在多种解释，请停止操作并提出针对性问题，严禁私自做出选择。
- 合约草案可用于揭示模糊性，但在“澄清记录”完成且通过规范关卡前，不得将其视为锁定的“目标（Goal）”。

**工作单元契约必须包含一份“澄清记录（Clarification record）”。仅标注“未解决问题：无”不足以证明已执行澄清流程。**

## 3. 任务分类 (Task Classification)

- **琐碎（Trivial）**：注释、简短文档或对生产/运行时无影响的操作。自我检查即可。
- **非琐碎（Non-trivial）**：生产代码、用户可见行为、多文件操作、需审查的产物或跨会话工作。必须创建或阅读“工作单元契约”。
- **中等风险（Medium risk）**：涉及多文件或用户可见行为。需使用证据回执并进行结项审查。
- **高危/关键风险（High/critical risk）**：涉及鉴权、权限、计费、迁移、密钥、生产数据、部署、合规、不可逆更改或大规模删除。需要风险说明、回滚或重新开启路径，以及独立审查或人类批准。

## 4. 上下文路由 (Context Routing)

请按此顺序阅读：

1. 工作单元契约或 Issue 规范。
2. 与当前任务相关的项目地图和生命周期规则。
3. 目标文件附近的本地规则（Local rules）。
4. 当前代码、测试、运行时行为和 CI 配置。
5. 工作单元或变更路径引用的 ADR（架构决策记录）或文档。

**若文档与代码、测试或运行时行为冲突，请指出冲突并以当前代码实际情况（World Truth）为准。**

## 6. 编码标准 (Coding Standards)

- 在项目风格允许时，代码文件应包含简短的模块级说明。
- 实际操作中尽量将文件控制在 1000 行以内；仅出于可读性或权属原因拆分。
- 测试应描述**外部可观察的行为**，而非实现细节。
- 对于代码开发，必须使用**行为优先的 TDD（测试驱动开发）**。
- **追求“工程化适度”**：在简洁与健壮之间寻找平衡点；深思熟虑优先于盲目快改；最小 diff 优于破坏性的无意义重构。
- **架构可视化**：复杂设计、关键数据流、状态转换和非显然测试 setup 倾向使用 mermaid 图表达。

## 7. 子智能体路由 (Subagent Routing)

只有当平台实际启动子智能体时，隔离性才会提升。不要假设写下的路由规则会自动执行。

- 在进行**中等及以上风险**的实施前，运行 `harnessctl request-review --mode plan`，启动 Reviewer 子智能体，等待结论，然后运行 `harnessctl check --gate plan-review --strict`。
- 方案审查通过后，在写入边界清晰的情况下，启动 Worker 子智能体进行实施。仅在极小、低风险的编辑时才保留在主智能体中实施，并记录无需执行者隔离的原因。
- **使用 Worker 时**：仅提供角色、WU-ID、子任务目标、写入边界、所需证据和额外重点。执行者必须从仓库产物中重新构建上下文。
- **使用 Reviewer 时**：Reviewer 必须直接阅读契约、Diff、证据、范围和风险。自述不能作为唯一的审查输入。
- **开发者不得自行提交“结项审查通过（PASS）”的结论。**

**默认策略**：对于非琐碎的代码实施，当契约锁定、方案审查通过且写入边界清晰时，应使用执行者隔离。

## 8. 测试与证据 (Testing And Evidence)

- 使用 `harnessctl evidence` 记录验证过程；**自然语言的声明不代表证据**。
- 中等及以上风险的证据应包含 `command_log_ref`（命令日志引用）、`artifact_uri`（产物路径）或 `manual_artifact_ref`（手动产物引用）。
- 跳过的检查绝不代表通过。需将跳过的证据记录为 `skipped` 或使用特定范围的豁免（Waiver）。
- 在验证/审查前运行产物校验：

```bash
python3 harness/cli/harnessctl.py validate --id <WU-ID> --strict
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate verification --strict
```
## 9. 开发与执行

当 work unit 通过 review 后可以使用 worker 来进行任务的执行

## 10. 审查与验收 (Review And Acceptance)

- **方案审查（Plan Review）**：在实施前检查提议的工作是否立足于现实。
- **结项审查（Close Review）**：在验收前检查 Diff、证据、范围、风险和可维护性。
- 中等及以上风险的工作在“运行”前需要方案审查通过，在“完成”前需要结项审查通过。
- 结项审查必须引用最新的证据回执 ID。
- 高危/关键工作需要独立审查或人工关卡。

## 11. 安全与边界 (Safety And Boundaries)

- 未经明确风险处理，不得处理密钥、生产数据、迁移、部署、计费、鉴权或不可逆操作。
- 破坏性命令、强制推送、直接推送到受保护分支、发布软件包、基础设施变更及集群变更，均需要人类批准或平台权限门禁。
- Prompt 指令不足以作为不可逾越的边界；请使用控制器检查、钩子、权限、CI、分支保护或人工关卡。

## 12. 常用命令 (Commands)

```bash
python3 harness/cli/harnessctl.py init
python3 harness/cli/harnessctl.py list
python3 harness/cli/harnessctl.py status --id <WU-ID>
python3 harness/cli/harnessctl.py check --id <WU-ID> --gate spec --strict
python3 harness/cli/harnessctl.py lock --id <WU-ID> --status ready
python3 harness/cli/harnessctl.py evidence --id <WU-ID> --claim EV1 --type test --result pass --command "<command>" --command-log-ref "<log>"
python3 harness/cli/harnessctl.py validate --all --strict
python3 harness/cli/harnessctl.py ci --strict
```

当目标仓库定义了特定项目的构建/测试命令时，请优先使用。

## 13. 更新规则 (Update Rules)

- 保持此文件简短且结构化。更新相关章节，而非追加随意规则。
- **不要**在此处存储活跃的工作单元状态、聊天摘要或调试历史。
- 将详细的生命周期变更放在 `docs/harness/`，可复用程序放在 `skills/`，确定性检查放在 `harness/cli` 或 CI 中。
- 更改控制器行为时，需在同一次提交中更新测试和相关文档。
