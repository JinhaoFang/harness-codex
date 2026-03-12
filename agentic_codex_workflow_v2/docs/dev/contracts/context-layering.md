# Runtime Context Layering Contract

> 这份契约回答一个现实问题：为什么同一套规则写在不同位置，对 coding agent 的运行效果完全不同？因为有些入口会在启动时自动被发现，有些不会。V2 的目标是把高频规则放在自动入口，把深规则变成 task pack 的显式依赖。

## 1. 自动入口层
### AGENTS / global instructions
- 会话启动时最容易进入上下文
- 适合放：高频硬规则、总路由、角色协议、controller 入口
- 不适合放：冗长配方、低频细则、完整背景资料

### Skills metadata
- 启动时通常只加载 metadata
- 适合放：何时使用、输入输出、触发条件
- 不适合放：大量深文档正文

## 2. 运行时入口层
### Task Pack
- 由 controller 在当前 phase 生成
- 是 sub-agent 的第一入口
- 适合放：当前 phase 的最小必要上下文

## 3. 深层参考层
### docs/contracts / architecture / insights
- 只有在 task pack 显式引用时才展开
- 适合放：长期规则、例外情况、深度背景、模板规范

## 4. 设计原则
1. 高概率必用的规则放 AGENTS
2. 触发逻辑放 skills metadata
3. 当前 phase 的最小上下文放 task pack
4. 低频或深层细则留在 contracts / architecture
5. 不要再依赖“agent 应该自己会去搜到这份文档”
