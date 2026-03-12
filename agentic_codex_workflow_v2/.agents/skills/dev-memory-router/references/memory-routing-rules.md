# Memory 路由规则

## 1) 长期记忆的边界
只写未来高频可复用知识，不写执行流水账。

### architecture/
写入：
- 系统架构、模块边界、依赖方向、生命周期、关键不变量
- 会反复影响后续设计与实现的契约口径
- 本次任务明确复核过的架构规则

### insights.md
写入：
- 踩坑记录（症状 -> 原因 -> 修复 -> 验证）
- 高价值入口
- 常用命令 / 常见验证路径
- 经过本次任务再次验证的经验规则

### 不写入长期记忆
- 执行流水账
- 临时验证状态
- 一次性讨论痕迹
- 只在 scratch 中出现、尚未 promote 的结论

## 2) 写回前提
写回必须同时满足：
- 当前任务在 workflow 中记录了 `Memory Lookup Used: YES`
- 该规则被本次任务验证过
- `Verification Source` 可追溯
- close reviewer 未指出该规则不稳定

## 3) 统一 schema
每条必须包含：
- Rule
- Why
- Trigger
- Example
- Source Workflow
- Last Verified
- Verification Source

## 4) 合并与失效
- 同类项优先合并，不新增近义重复条目
- 失效或被替代的规则要更新或删除
- 仍不稳定的知识继续留在 workflow，不写入长期记忆
