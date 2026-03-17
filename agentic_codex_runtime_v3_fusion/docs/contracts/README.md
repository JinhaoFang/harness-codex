# docs/contracts/

这里存放 **可选的长期合同文档**，用于补充而不是替代 task-local `plan.md`。

## 定位

- `plan.md` = 当前 task 的 Goal truth
- `workflow.md` = 当前 task 的 Process truth
- `docs/contracts/*` = 跨 task、跨 reviewer、可长期复用的业务 / API / UI 合同文档

## 何时创建

只在以下情况创建：

- 该信息会在多个 task 中复用
- 该信息需要独立 review / 版本化 / 对外对齐
- 该信息不能只作为当前 task 的 Goal truth 存在

## 何时不要创建

- 只是当前 task 的一次性计划细节
- 只是执行步骤、review 节奏、恢复说明
- 只是为了“补一份文档”而复制 `plan.md`

## 子目录

- `prd/`：长期产品 / 业务合同
- `api/`：稳定接口 / schema / compatibility 合同
- `ui/`：稳定交互 / 状态 / 页面行为合同
- `templates/`：最小模板
