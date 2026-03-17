# .githooks/

这些 hook 是 **repo-level engineering guardrails**，不是 agent runtime truth。

## 安装

```bash
bash .githooks/install.sh
```

会执行：

```bash
git config core.hooksPath .githooks
```

## 边界

- hook 负责 secrets / dangerous commands / protected branch 等工程护栏。
- hook 不负责 `plan.md` / `workflow.md` / review / evidence 的裁决。
- 若 hook 与 runtime truth 冲突，以代码世界和 runtime review 规则共同裁决；不要为了绕过 hook 新增长期工件。
