#!/usr/bin/env bash
set -euo pipefail
python .agents/workflow/taskctl.py record-evidence "$@"
