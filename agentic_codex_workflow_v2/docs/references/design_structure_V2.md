# Agentic engineering for coding

> **可复现、可验证、可回滚、可断点重续、可持续演进、上下文不腐烂。**

- **局部操作与局部判断，下放给 agent**
- **全局制度、不可违背的不变量、验证与演进机制，上提到系统设计**

# 一、目录

1. **总判断**
2. **六项总纲**：每一项都按“定义/本质、为什么第一性、违反时怎么坏、它禁止什么、允许哪些实现路线”来写
3. **架构分层与模块分层**：这一部分更偏系统设计骨架，不拘泥于固定模板，但保持清晰可审查

---

# 二、真相层级

在 agentic engineering 里，必须先区分**什么是真相，什么只是访问真相的手段、恢复真相的路径、或解释真相的辅助工件**。

如果这一点不先立住，系统运行一段时间后，文档、summary、continue notes、rules/skills 都可能被 agent 误当成“最终权威”，从而逐步漂移。

这里采用三层真相，而**不额外引入“恢复工件”作为独立真相层**。
原因很简单：恢复本身不应拥有新的真相地位；恢复所需内容，应当能够从已有真相中重新构造出来。否则就是为了修补一个问题，再引入新的维护对象，最终导致系统更难维护、长尾更长。

---

## 第一层：目标真相

它回答的是：

- 到底要做什么
- 不做什么
- 哪些灰区已经被决策锁定
- 完成必须满足哪些目标约束

典型承载物包括：

- `context.md`
- decision records
- task contracts
- must-haves
- gray-area decisions

它的本质是：**目标与约束的权威来源**。

如果这一层不稳，后面的规划、执行、验证都会在错误方向上越跑越远。

---

## 第二层：过程真相

它回答的是：

- 当前处于哪个 milestone / slice / task
- 下一步合法状态迁移是什么
- 哪些单元已完成、哪些未完成
- 当前恢复点应从哪里进入

典型承载物包括：

- state machine
- task / slice / milestone registry
- legal transitions
- checkpoint metadata
- workflow state

它的本质是：**系统位置与推进规则的权威来源**。

过程真相不能依赖会话历史推断，更不能靠 agent “大概记得现在做到哪里”。

---

## 第三层：世界真相

它回答的是：

- 代码实际上是什么状态
- 仓库和文件系统当前是什么状态
- 测试、构建、行为检查、UI、日志、指标实际显示了什么
- 世界是否真的已经满足任务承诺

典型承载物包括：

- source code
- filesystem
- git history
- tests / build results
- screenshots
- logs / metrics / traces
- behavior checks

它的本质是：**外部世界与执行结果的权威来源**。

如果目标真相规定“应该怎样”，过程真相规定“做到哪了”，那么世界真相回答的是：
**现实到底是不是已经如此。**

---

## 三层之间的关系

三层真相不是并列孤岛，而是有清晰分工：

- **目标真相**决定方向与约束
- **过程真相**决定当前位置与合法推进
- **世界真相**决定现实是否满足前两者的要求

因此，系统不能让低权威对象倒灌成高权威对象：

- summary 不能替代目标真相
- 会话历史不能替代过程真相
- “agent 说已经完成”不能替代世界真相

恢复、continue、summary、review notes 都可以存在，
但它们只能作为**从三层真相重新进入系统的辅助工件**，不能成为第四层真相，更不能覆盖原有真相。

只有先把真相层级立住，后面的职责分治、状态外部化、上下文装配、验证裁决、可逆化和反熵化才不会互相打架。

---

# 三、六项总纲

**不可妥协原则：**

- 职责分治
- 状态外部化
- 上下文装配化
- 证据裁决化

**面向长程自治的附加不可妥协原则：**

- 变更可逆化
- 系统反熵化

---

## 第一项：职责分治

### 1. 定义 / 本质

它约束的是：**哪些职责可以交给 LLM，哪些职责必须收回到 deterministic layer。**
GSD 的原话几乎可以当成系统宪法：如果某件事可以被 if-else 稳定正确处理，那它就不应该交给 LLM。deterministic code 负责 git、状态迁移、文件解析、上下文装配、静态验证；LLM 负责 scope/slice/task 分解、must-haves、gray areas、research judgment、failure diagnosis、summary 和代码生成。

### 2. 为什么它是第一性的

它解决的不是“效率偏好”，而是**概率系统不适合承担制度职责**这个根问题。
只要把机械正确性寄托在 LLM 上，系统就会同时失去三样东西：可靠性、可解释性、可恢复性。GSD 之所以强调 token-efficiency and reliability，本质上不是省 token，而是把“流程正确性”从概率空间拿出来，放回确定性空间。OpenAI 那篇也一样：他们早期进展慢，原因不是 Codex 不会写，而是环境和内在结构 underspecified，缺少让 agent 可执行、可审计的制度壳。

### 3. 违反它时，系统会怎么坏

最典型的失效模式是：

- agent 自己拼 git/bash 命令，导致状态推进和代码状态不同步
- agent 需要自己解析 markdown 才知道“当前在哪个 task”，于是状态 truth 不再可信
- agent 需要自己猜该加载哪些上下文，导致上下文注入变成“发现式探索”，token 大量浪费
- 验证逻辑也由 agent 临时解释，结果同样的完成条件在不同会话里被不同理解

这类系统表面上“很自由”，实际上会越来越脆：你无法知道错是出在业务判断，还是出在流程控制本身。GSD 之所以把 `gsd_manage` / `gsd_verify` 做成工具，就是为了切断这条失效链。

### 4. 它禁止什么

它禁止的反模式包括：

- 让 agent 自己决定状态迁移是否合法
- 让 agent 通过聊天历史推断当前任务位置
- 让 agent 自己“记住”该读哪些规则/上下文
- 让 agent 在没有系统原语的情况下手工 orchestrate 全流程

一句话：**禁止把 control plane 伪装成 prompt discipline。**

### 5. 它允许哪些不同实现路线

这条原则只要求“分治”，**不限定具体实现技术**：

- 可以像 GSD 一样用专门工具封装 deterministic layer
- 也可以用 shell scripts / internal CLI / daemon / workflow engine
- 也可以在更轻量的系统里，只先把 state transitions、rollback、context assembly 抽出来

---

## 第二项：状态外部化

### 1. 定义 / 本质

它约束的是：**系统进度、决策、位置、恢复点，必须存在于会话之外，并能被重建；不仅要外部化，还必须可重建、可失效化。**

GSD 的 hierarchy、task/slice/milestone artifacts、checkpoint、continue 相关设计，本质上都在回答同一个问题：系统现在处于什么状态，如何从磁盘和 git 中重新推导回来；以及当上游目标、边界、代码现实发生变化时，哪些状态表述必须被显式判定为失效，而不是被默认继续沿用。

### 2. 为什么它是第一性的

因为**会话不是状态容器，会话只是计算过程**。

一旦状态主要存放在对话上下文里，所有关键能力都会同时断掉：

- session 一结束，状态就蒸发
- 换一个 agent / 新上下文，无法接力
- 很难知道“究竟做到哪了”
- 决策是隐式的，不可审计
- resume 只能靠人重新解释

但“写出状态”本身还不够。
如果状态不能从工件和 git 中重新推导，或者在上游变化后仍被系统继续当成有效状态使用，那么它仍然只是脆弱快照，而不是真正的状态外部化。

所以这条原则真正要求的是：

## **状态必须外部化、可重建、可失效化。**

### 3. 违反它时，系统会怎么坏

具体失效模式会非常明显：

- 任务做到一半被 compaction 或 session timeout，下一轮 agent 重新探索一遍
- 以前做过的决策被重新争论，导致策略漂移
- 人必须通过滚聊天记录才能知道当前进展
- agent 说“我已经完成了”，但系统没有任何可独立验证的状态表示
- 上游 contract 已改变，但旧状态仍被当成有效进度继续推进
- 某个 summary / note 明明已经过时，却没有任何失效机制，后续 agent 仍按它工作

### 4. 它禁止什么

它禁止的反模式包括：

- 把“continue”建立在“让模型自己写个简短 recap”上
- 把“当前任务”仅放在 system prompt 或口头约定里
- 让关键决策只存在于某次讨论会话中
- 没有 checkpoint / resume artifact 就声称支持长任务
- 让外部化状态成为一次性快照，而不能从更低层真相重新构造
- 在目标真相、过程真相、世界真相变化后，不显式判定原状态是否已失效

### 5. 它允许哪些不同实现路线

状态外部化可以很轻，也可以很重：

- 轻量路线：markdown artifacts + git + 可重建的 continue / state 描述
- 中等路线：加一个明确的 state machine 文件 / task registry
- 更重路线：再配数据库、event log、workflow engine

GSD 证明了，即使只靠“文件 + git”，也能把状态做得很强。原则要求的是：

## **状态在会话外存在、能从系统真相重建，并且能在上游变化时被判定失效。**

---

## 第三项：上下文装配化

### 1. 定义 / 本质

它约束的是：**当前任务该看到什么，不该看到什么，以及这些信息如何被系统注入。**
GSD 的 anchor pruning、pre-assembled context、hierarchical summaries；systematicls 的“只给代理精确所需的信息”“研究与实现分离”“每个 contract 一个新会话”，讲的是同一件事：上下文不是自然堆积，而是按任务装配。

### 2. 为什么它是第一性的

它解决的是 agent 系统最普遍、也最隐蔽的根问题：**context rot / context inflation**。
GSD 直接把 context rot 描述成“multi-task reliability 的 silent killer”；systematicls 则说得更通俗：你给代理太多不相关的信息，它就会开始被 26 个会话前、71 个会话前的噪音污染。

这不是“提示词写得不够好”，而是信息流设计错误：
你把会话历史当记忆库，就等于把“相关信息”和“过时噪音”混在一起交给模型。

### 3. 违反它时，系统会怎么坏

失效模式非常具体：

- 第 3、4 个任务开始，模型持续引用早已过时的代码结构
- 重复读项目结构、查状态、找历史决策，token 被“定位自己”消耗掉
- 早期失败路径、过时调试输出、旧接口名污染当前判断
- 长会话看似“连续”，实际 reasoning quality 逐步下降

GSD 甚至明确指出：很多 agent 系统之所以在第 3、4 个任务后撞墙，不是模型变笨，而是上下文被毒化了。

### 4. 它禁止什么

它禁止的反模式包括：

- 依赖长会话自然累积记忆
- 默认“上下文越多越安全”
- 把研究、规划、实现、调试全部塞进同一上下文窗口
- 让 agent 自己通过 discovery calls 去搞清楚“我在哪、之前做了什么、当前应该依赖什么”

GSD 甚至说得很重：如果 agent 还需要 `grep` 项目结构、`read` 状态文件、查 prior slices，那么 **context assembly 是 broken，是 bug，不是 workflow**。

### 5. 它允许哪些不同实现路线

这条原则允许很多路线：

- Anchor pruning + curated summaries
- Research / implementation split
- Contract-per-session
- Retrieval + routing + task-local memory
- 文档目录型 CLAUDE.md / AGENTS.md + 条件路由

重点不在“必须用哪一种技巧”，而在是否满足两个条件：

1. 当前任务拿到的是**最小必要信息**
2. 这些信息是**系统装配进去的，不是靠 agent 临时发现的**

---

## 第四项：证据裁决化

### 1. 定义 / 本质

它约束的是：**系统推进不能依据“步骤做完了”，只能依据“证据成立了”；而且证据不只是附属说明，而是推进、返工、回滚、完成裁决的授权来源。**

GSD 的 must-haves 把完成条件定义为 truths、artifacts、key links，再配上 static / command / behavioral / human 四层验证；systematicls 则把 tests、screenshots、contract 当成任务结束的硬约束。
这不是流程打卡，而是**由证据裁决系统是否可以推进**。

### 2. 为什么它是第一性的

它解决的根问题是：**LLM 很会开始任务，但不天然知道任务何时真正结束。**

systematicls 直接指出，“代理不知道如何结束任务”是当前智能的一大核心问题；如果没有明确终点，agent 很容易交付一个 stub 或半成品并宣布完成。GSD 的 must-haves 与 verification ladder，本质上就是在把“结束”从主观判断改成证据裁决。

所以这条原则要求的不是“结果最好有证据”，而是：

**没有证据裁决，就没有推进合法性。**

### 3. 违反它时，系统会怎么坏

最典型的失效模式包括：

- 文件都存在，但没有真实实现
- 每个文件单独看都像做了事，但彼此没 wiring
- 测试看起来绿了，但 UI/行为不符合用户承诺
- agent 按步骤做完就停止，但任务承诺没有被真正证明
- 人类 review 时无法知道哪些行为是“有意设计”，哪些是 accidental output
- 执行完成感凌驾于真实完成裁决之上，导致系统过早推进

### 4. 它禁止什么

它禁止的反模式包括：

- 用 TODO checklist 替代完成定义
- 用“代码写了很多”替代“结果已成立”
- 把验证等同于“测试跑了”
- 允许 agent 修改测试来让任务“结束”
- 只看文件存在，不看 wiring 和 substance
- 让状态推进由执行者主观宣告，而不是由证据裁决授权

### 5. 它允许哪些不同实现路线

这条原则允许多条验证路线并存：

- TDD / unit tests
- Integration / end-to-end tests
- Screenshot + UI verification
- Curl / browser / API behavior checks
- Artifacts + links + static analysis
- UAT scripts 供人类抽检

所以这里的范式不是狭义 TDD，而更接近：

**Verification-First / Contract-Driven Development**

TDD 只是其中一条强有力的局部实现路线，不是全部。
更准确地说，系统不是“因为跑了测试所以能推进”，而是：

**因为证据裁决成立，所以系统才被授权推进。**

---

## 第五项：变更可逆化

### 1. 定义 / 本质

它约束的是：**每一步都要能以清晰粒度撤销，而不是只能“继续改”。**
GSD 的做法很具体：每个 slice 一条 branch、每个 task 一个 checkpoint、slice 完成后 squash merge、坏 task 回 checkpoint、坏 slice 直接 revert、UAT 失败走 `-fix` branch。

### 2. 为什么它是第一性的

它解决的是 agent delegation 的根条件：**只有可逆，才敢放权。**
如果你让 agent 高速地产生修改，但没有清晰的撤销粒度，那么系统表面上“更自动化”，本质上只是把风险累积得更快。GSD 特别强调 clean, revertable git history，不是为了代码整洁，而是为了让 autonomy 可以被安全承受。

### 3. 违反它时，系统会怎么坏

失效模式通常是：

- agent 生成一大团跨任务变更，无法定位坏点
- UAT 发现问题时，只能整片返工
- main 上历史不可读，回滚代价巨大
- 错误不是不能修，而是“修的代价大到不敢放权”

这种系统一开始可能跑得很快，但很快就会进入“每次都要人盯着合并”的保守状态，自治能力自然退化。

### 4. 它禁止什么

它禁止的反模式包括：

- 所有修改都堆在一条长期分支里
- 没有 checkpoint 就开始大任务
- 没有 slice 粒度的 merge / revert 边界
- 把“可回滚”理解成“git 反正总能 reset”

真正的要求不是 git 命令存在，而是**回滚粒度被系统设计出来了**。

### 5. 它允许哪些不同实现路线

可逆化可以这样实现：

- branch + checkpoint + squash merge
- stacked PRs
- change sets / patches
- snapshot + rollback journal
- workflow engine + step-level compensation

原则不要求你必须复刻 GSD 的 git 结构，但要求每个 delegable 单位都拥有清晰的撤销边界。

---

## 第六项：系统反熵化

### 1. 定义 / 本质

它约束的是：**系统必须具备持续恢复、持续压缩、持续清理、持续纠偏、持续再生的能力，而不是一次性产出后任其腐烂。**

GSD 的 continue、hierarchical summaries、UAT→fix flow，本质上都在解决长期运行中的连续性与信息衰减问题；systematicls 则直接指出 rules/skills 会膨胀、冲突、再次让性能恶化，因此必须周期性清理。

这里最关键的修正是：
反熵不只是“压缩旧信息”，更是**从更低层真相重新生成高层工作记忆**。
否则系统会滑向“summary of summary of summary”的逐级失真。

### 2. 为什么它是第一性的

它解决的是 agent 系统与传统脚本系统最大的不同：

**agent 系统不是一次求解，而是持续运行。**

只要系统长期运行，就一定会出现：

- 上下文老化
- 规则漂移
- 技能冲突
- summary 失真
- 会话中断
- 交付后返工

所以“反熵”不是运维优化，而是 agent 系统能否长期有效的生死线。
而反熵真正可靠的方式，不是不断压缩已有摘要，而是必要时回到目标真相、过程真相、世界真相重新再生高层表示。

### 3. 违反它时，系统会怎么坏

具体失效模式包括：

- 规则和技能越来越多，最后彼此冲突
- summary 一层压一层，信息逐级失真
- 每次恢复都靠人重新解释，resume 失去意义
- UAT 发现问题后没有制度化 fix flow，只能临时插入返工
- 系统前几周很好用，之后越来越“有魔法感但不稳定”
- 高层记忆长期脱离底层真相，最后形成文档漂移和制度漂移

### 4. 它禁止什么

它禁止的反模式包括：

- 把 memory 当越多越好
- 无限累加规则/skills 而不做合并与清理
- 用“summary of summary of summary”压缩长期记忆
- 把中断恢复建立在临时人工 recap 上
- 把 fix 当成例外，而不是流程内建能力
- 把压缩误当成反熵，却不提供从底层真相重新再生高层表示的能力

### 5. 它允许哪些不同实现路线

反熵化允许很多不同实现路线：

- continue / resume hooks
- hierarchical summaries，但高层摘要应能从下层真相重生成
- rule/skill refactor day
- UAT → fix branch → re-verify
- 周期性知识库 freshness checks
- 基于目标真相、过程真相、世界真相的 summary regeneration

GSD 的做法是“层级摘要 + continue + fix flow”，systematicls 的做法是“rules/skills 清理 + contract-per-session”。它们路线不同，但都在做同一件事：

## **主动清除系统熵增，并在必要时从底层真相重新再生高层工作表示。**

---

# 四、架构分层

这一部分不按“五段式”写，因为它更适合看作系统拓扑。

---

## 第一层：意图层

这一层回答的是：

- 到底要做什么
- 不做什么
- 哪些地方存在 gray areas
- 哪些灰区已经被决策锁定

GSD 的 discussion phase 就是典型实现：在 planning 之前先识别 gray areas、提出具体选项、挑战模糊、把决策沉淀成 `context.md`，并注入后续 planning / execution / verification。Harrison 的 “long live PRDs” 也是同一个方向：死掉的是传统 PRD 流程，不是 intent artifact 本身。

如果这一层薄弱，系统不会立刻报错，而是会在更后面以更贵的方式坏掉：

- task 分解偏向错误方向
- 验证通过但结果不对
- review 极慢，因为 reviewer 无法分辨“故意的”和“偶然的”
- fix flow 变成无限循环

所以意图层不是“文档层”，而是**方向锁定层**。

---

## 第二层：上下文层

这一层回答的是：

- 当前任务需要知道什么
- 上游哪些决策和摘要应该被注入
- 哪些历史必须被裁掉
- rules/skills 在当前场景下该如何路由

GSD 的 anchor pruning、pre-assembled context、hierarchical summaries；systematicls 的 CLAUDE.md 作为逻辑目录、research/implementation split、每 contract 一个新会话，都属于这一层。

这一层的目标不是“记住一切”，而是：
**让 agent 以最低的信息熵获得当前任务的最大有效上下文。**

---

## 第三层：执行层

这一层回答的是：

- agent 在什么工作区执行
- 它通过什么原语改变世界
- 它如何受到任务粒度、状态机、控制面约束

OpenAI 的 harness engineering 里，关键变化就是让 agent 不只是输出文本，而是真正在受控环境里工作：使用标准开发工具、读仓库知识库、看 UI、看 logs、看 metrics、在 feedback loop 里持续修正。

所以执行层不是“让 agent 能 run bash”这么简单，而是：
**让 agent 的执行发生在被系统包裹的受控环境中。**

---

## 第四层：反馈层

这一层回答的是：

- 什么算完成
- 证据从哪里来
- 谁来判断推进 / 返工 / 回滚
- 人类在什么层级介入

GSD 的 verification ladder 和 UAT，systematicls 的 tests + screenshots + contract，Harrison 的 review bottleneck，全部汇聚在这里。

所以反馈层不是“测试层”，而是**系统真相裁决层**。

---

# 五、模块分层

- **一级模块**
- **横切控制底座**
- **横切方法注入子系统**

---

## A. 八个一级模块

### 模块 1：意图 / 决策工件模块

负责沉淀目标、边界、gray areas、deferred items、决策理由。
它的代表工件不是“传统 PRD”，而是更广义的 **intent artifact**，例如 `context.md`、structured prompt、review companion doc。

### 模块 2：规划 / 边界契约模块

负责 milestone / slice / task 分解，以及 boundary maps、produce/consume contracts。
它不是 TODO 列表，而是**最小可完成单元 + 依赖边界 + demo sentence + contract**。

### 模块 3：状态机 / 工作流模块

负责当前位置、合法迁移、完成条件、下一步、resume 入口。
GSD 明确把 next task、complete task、complete slice、advance 收进 deterministic layer，说明这不是隐式逻辑，而是一级系统对象。

### 模块 4：上下文 / 记忆模块

负责任务级上下文装配、摘要注入、记忆压缩、恢复注入、token budget 管理。
它的目标不是“多记”，而是“精准装配 + 防腐烂”。

### 模块 5：执行工作区模块

负责 agent 的实际工作环境、工具接入、任务工作区隔离、运行时反馈回路。
它要保证 agent 不是在“空聊天框”里工作，而是在**可操作、可观察、可重复的工作区**里工作

### 模块 6：验证 / 证据模块

负责 must-haves、tests、screenshots、behavior checks、UAT scripts、证据采集与裁决。
它是系统的推进闸门，而不是辅助测试。

### 模块 7：版本 / 可逆模块

负责 branch、checkpoint、merge、revert、fix-forward。
这里关注的是**可逆性边界**，不是 git 命令本身。

### 模块 8：恢复 / 演进模块

该模块的职责是帮助系统**从既有真相重新进入运行状态并持续演进**，而不是生产新的真相层。负责 interruption handling、continue、fix flow、summary regeneration、rule/skill cleanup。
它保证系统不是一次性成功，而是长期可维护。

---

## B. 一个横切底座：Deterministic Control Plane

这是这版最重要的修正之一。

**它不是一级模块。**
它是横切基础设施，服务于状态、上下文、执行、验证、版本、恢复这些模块。

它承载的职责包括：

- state transitions
- git operations
- scaffolding
- context assembly
- static verification
- deterministic checks

GSD 的 `gsd_manage` / `gsd_verify` 正是这种 control plane 的体现。

正式表述是：

## **机械化操作不是一级模块，而是横切的确定性控制面。**

---

## C. 一个横切子系统：Rules / Skills Injection

**skills 不是一级模块。**
它们更适合放在“上下文路由 + 方法学外部化”的位置理解。

systematicls 的区分很清晰：

- **rules**：编码偏好、禁忌、条件路由
- **skills**：编码配方、方法、套路、解决路径

CLAUDE.md/目录型文件的作用，是在特定场景下把这些方法路由给 agent。

所以正式定位应该是：

## **skills/rules 是方法注入子系统，不是状态 truth，也不是控制 truth。**

它们可以包含 shell/script 配方，但**不能替代 control plane**。
凡是涉及状态推进正确性、上下文装配正确性、回滚正确性、验证正确性的职责，都不能只靠“某个 skill 里写了怎么做”。

---

# 六、最终收束版

把这一整轮压成最短、最硬的一版，就是：

## 六项总纲

1. 职责分治
2. 状态外部化
3. 上下文装配化
4. 证据裁决化
5. 变更可逆化
6. 系统反熵化

## 四层架构

1. 意图层
2. 上下文层
3. 执行层
4. 反馈层

## 八个一级模块

1. 意图 / 决策工件
2. 规划 / 边界契约
3. 状态机 / 工作流
4. 上下文 / 记忆
5. 执行工作区
6. 验证 / 证据
7. 版本 / 可逆
8. 恢复 / 演进

## 两个横切系统

- deterministic control plane
- rules / skills injection

---

# 七、把它压成一个最实用的判断格式

以后分析任何系统，可以直接用这套问法：

**先问原则**

- 它怎么做职责分
- 它怎么做状态外部化
- 它怎么做上下文装配
- 它怎么做结果证据
- 它是否设计了可逆边界
- 它是否有反熵机制

**再问模块**

- 意图工件在哪里
- 契约/规划单位是什么
- 状态核在哪里
- 上下文怎么装配
- 执行工作区是什么
- 验证闸门是什么
- 回滚边界在哪里
- 恢复/演进怎么做

这样就不会再把“原则”和“手段”混在一起。

---

# 八、依赖关系图

```text
意图/决策工件
↓
规划/边界契约
↓
状态机/工作流 ←—— 验证/证据
↓ ↑
上下文/记忆 ——→ 执行工作区 ——→ 证据采集
↓
恢复/演进

版本/可逆 —— 横切于 状态机 / 执行 / 验证 / 恢复
Deterministic Control Plane —— 横切于 状态机 / 上下文 / 版本 / 验证 / 恢复
Rules/Skills Injection —— 通过 上下文 路由到 规划 / 执行 / 验证
```

这个图里有几个关键点。

---

## 关键点 1：意图必须先于规划

这很好理解：
没有明确意图与已锁定决策，就没有稳定的分解。

GSD 的 discussion phase 先产出 `context.md`，再进入 planning；而且这个文件不是 planning 的附录，而是 planning / execution / verification 的输入。

所以依赖关系必须是：

**意图 → 规划**
而不是
**规划时顺便自己想意图**

---

## 关键点 2：规划必须先于状态

因为状态机不可能在“没有单元边界”的前提下存在。
状态机需要知道：

- 现在处于哪个 milestone/slice/task
- 下一个合法单元是什么
- 哪个单元完成后可推进

这些都依赖规划模块定义出来的 hierarchy 和 boundary maps。

所以是：

**规划 → 状态**

而不是：

**先有状态，再临时定义工作对象**

---

## 关键点 3：验证不是附属品，而是状态推进的授权源

这点特别重要。
状态机记录“位置”，但验证决定“可否推进”。
所以依赖关系不是简单的线性：

**状态 → 执行 → 验证 → 状态**

而是：

- 状态发起任务
- 执行产生候选结果
- 验证裁决完成与否
- 状态依据验证结果迁移

所以状态和验证之间本质上是一个闭环，而不是单向关系。GSD 的 must-haves / verification ladder 和 task completion / slice completion 正好说明了这一点。

---

## 关键点 4：上下文依赖状态与规划，不能反过来定义它们

上下文模块需要知道：

- 当前是哪个 task
- 要注入哪些依赖 slice 的 summary
- 优先级如何裁剪
- resume 时继续哪一步

这些都说明上下文模块依赖于：

- 规划给出的依赖图
- 状态给出的当前位置

GSD 甚至说得更狠：如果 agent 还需要 `grep` 项目结构、`read` 状态文件、自己找 prior slices，那说明 context assembly broken。

所以正确关系是：

**规划/状态 → 上下文**

而绝不能反过来变成：

**agent 在上下文里慢慢摸索当前状态和依赖**

---

## 关键点 5：skills 只能经由上下文进入，不应直接写进状态真相

这是这轮最重要的“禁止反向依赖”之一。

正确关系是：

**skills/rules → 上下文路由 → planning/execution/verification**

而错误关系是：

**skills → 直接定义 state transition / completion truth / rollback truth**

因为只要 skills 能直接决定这些系统真相，整个控制系统就退化成“靠 agent 记得读哪份技能文档来维持正确性”。

这是最危险的一类反模式。

---

# 六、哪些模块不能反向依赖谁

这一节最适合作为你后面做系统设计时的“红线规则”。

---

## 红线 1：状态机不能反向依赖上下文模块来认定当前位置

状态真相必须外部可重建。
不能变成“看当前 session 里出现了哪些消息，所以推测现在在 task 4”。

也就是说：

- 上下文可以**承载**状态信息
- 但状态不能**由上下文推断生成**

这是根红线。

---

## 红线 2：验证真相不能反向依赖 skills / rules

验证标准必须是 contract / must-haves / tests / behavior / UAT 等证据性对象。
不能变成“这个 skill 里说差不多这样就行，所以判定完成”。

skills 可以提供验证方法，但不能拥有完成裁决权。
这也是为什么 systematicls 要把 `{TASK}_CONTRACT.md` 当成 stop-hook 的依据，而不是靠 agent 的自由理解。

---

## 红线 3：规划不能反向依赖执行过程来定义边界

也就是不能先让 agent 大概写起来，再根据它写出来的东西反向定义 slice / task / contract。
那样会导致 contract 变成事后描述，而不是前置约束。

GSD 的 boundary maps 强调的是：**先显式声明 produce / consume，再去写实现。**

---

## 红线 4：意图不能在执行中被静默改写

GSD 的 discussion 之所以重要，是因为它把 gray-area decisions 锁进 `context.md` 并注入全流程，避免 agent 在 task 4 静默做出和前面不同的选择。

所以执行模块可以发现问题、提出返工建议，但不能静默改写目标真相。
任何目标层修正，都应该显式回到意图/决策模块。

---

## 红线 5：恢复模块不能成为新的真相源

continue file、summary、fix notes 都很重要，但它们本质上是**恢复工件**，不是根真相。
它们应该帮助系统重新进入已有状态，而不是生成一个新的“我猜你现在大概做到这”的状态。

也就是说：

- 恢复模块依赖主模块
- 主模块不能依赖恢复模块来重新定义自己

---

## 红线 6：summary 不能绕过 freshness check 直接成为 planning 依据

summary、continue notes、阶段性 recap 都可以帮助系统加速进入状态，
但它们不能在没有 freshness check 的前提下，直接成为下一轮 planning 的依据。

任何高层摘要在被用于后续规划前，都应有机会被更低层真相校验，例如：

- 当前代码是否仍与摘要一致
- 上游目标真相是否已经修改
- 相关 contract / must-haves 是否已变化
- 相关 slice / task 是否已被 fix、revert 或重开
- 世界真相中的测试、行为、日志是否仍支持该摘要结论

否则 summary 会逐步从“辅助理解”滑向“伪真相”，最终让系统围绕过期概括继续运行。

---

## 红线 7：人工 override 不能只存在于口头层

人类当然拥有目标层主权，可以推翻旧决策、修改 gray areas、调整边界、改变优先级。
但这些 override 不能只存在于一次聊天、一段口头说明、一次临时评论中。

只要人工 override 不被显式写回系统真相，它就会在下一轮被旧真相覆盖，导致系统再次回到旧轨道。

因此，任何影响系统方向、约束、完成标准或合法推进路径的人工 override，都必须显式回写到相应真相层：

- 目标层变更，写回目标真相
- 过程层变更，写回过程真相
- 对世界真相的重新裁定，写回验证与证据记录

也就是说：

**人工主权可以越权，但不能悬空。**
