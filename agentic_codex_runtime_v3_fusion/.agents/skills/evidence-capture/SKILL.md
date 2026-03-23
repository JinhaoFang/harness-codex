---
name: evidence-capture
description: use when codex has run commands, tests, builds, runtime checks, or behavior checks and needs to record process evidence in a structured way without mixing in review verdicts.
---

# evidence-capture

Capture process evidence so later reviews can trace what actually happened.

## What evidence is for
Evidence records facts such as:
- which command ran
- which directory it ran in
- whether it passed or failed
- which artifacts were produced
- short notes that help a reviewer interpret the result

Evidence does not decide whether the task is approved.

## Good evidence
- use the real command, not a paraphrase
- keep notes short and factual
- attach artifact paths when files, screenshots, logs, or reports exist
- create separate evidence entries when checks serve different purposes
- for TDD-driven development work, prefer separate evidence entries for the red proof and the green proof

## Structured writeback

```bash
python .codex/tools/agentctl.py write-evidence   --task-id <task-id>   --subtask <subtask-id>   --kind command|test|build|behavior|screenshot|other   --result PASS|FAIL|INFO   --purpose "what this check proved"   --command "<real command>"   --cwd "<working directory>"   --artifact-path <path>
```

## Do not
- do not put PASS / REJECT review judgments in evidence
- do not invent artifacts that do not exist
- do not treat a skipped check as PASS
