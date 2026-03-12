#!/usr/bin/env bash
set -euo pipefail
python .codex/workflow/taskctl.py record-workflow-event "$@"
