# Task Pack

## Identity
- Task ID: 260312-realtime-livekit-closeout
- Title: 快速开发版收尾：Realtime + LiveKit
- Phase: BUILD
- Current State: BUILD
- Allowed Next State: CLOSE_REVIEW
- Owner: main

## Understanding Proof
- Goal Restatement: Execute the bounded realtime closeout: fix explicit openai dependency risk, unify README/legacy workflow status with code facts, and add E4 acceptance/regression artifacts without reopening completed feature work.
- Explicit Non-Goals:
  - Do not implement WS realtime TTS, new UX features, or deeper performance tuning.
  - Do not reopen false interruption resume, 5xx retry, interrupt semantics, or voice-mode implementation.
- 95% Understanding Check: YES
- Missing Pieces:
  - <none>

## Source Pointers
- Spec Source:
  - .agentdocs/archive/260312-realtime-livekit-closeout/plan.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/workflow.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/findings/realtime-closeout-sync-snapshot-2026-03-12.md
- Review Inputs:
  - .agentdocs/archive/260312-realtime-livekit-closeout/reviews/plan-review-r1.json
  - .agentdocs/archive/260312-realtime-livekit-closeout/plan.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/findings/realtime-closeout-sync-snapshot-2026-03-12.md

## Frozen Context
- Frozen Decisions:
  - BUILD scope stays within explicit dependency, doc-state cleanup, and E4 acceptance/regression artifacts.
  - false interruption resume, 5xx retry, and voice-mode thinking stay treated as already implemented.
- Known Non-Reopen Decisions:
  - <none>
- Open Risks / Escalations:
  - Lockfile refresh may be needed to keep livekit-agent dependency metadata consistent.
  - Some E4 evidence depends on external runtime environment and may need to remain as documented UAT.
- Previous Findings:
  - <none>

## Read Boundary
- Must Read:
  - AGENTS.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/plan.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/workflow.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/reviews/plan-review-r1.json
  - .agentdocs/archive/260312-realtime-livekit-closeout/findings/realtime-closeout-sync-snapshot-2026-03-12.md
  - .agentdocs/workflow/2602102130-realtime-livekit-agent-task.md
  - .agentdocs/workflow/2602131031-realtime-livekit-fix-execution-task.md
  - .agentdocs/workflow/2602131414-realtime-e3-enhancements-voice-mode-e4-task.md
  - .agentdocs/workflow/2602131555-livekit-agent-false-interruption-resume-task.md
- Verified Adjacent Context:
  - .agentdocs/workflow/2602121821-livekit-agent-e3-hardening-tracing-task.md
- Unread But Potentially Relevant:
  - <none>
- Coverage Decision: SUFFICIENT

## Current Truth Anchors
- Code Paths:
  - services/livekit_agent/pyproject.toml
  - services/livekit_agent/uv.lock
  - services/livekit_agent/README.md
  - .agentdocs/workflow/2602102130-realtime-livekit-agent-task.md
  - .agentdocs/workflow/2602131031-realtime-livekit-fix-execution-task.md
  - .agentdocs/workflow/2602131414-realtime-e3-enhancements-voice-mode-e4-task.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/**
- Key Symbols / Entry Points:
  - services/livekit_agent/adapters/dashscope_asr.py
  - services/livekit_agent/app/worker_entrypoint.py
  - services/livekit_agent/core/interruption_gate.py
  - services/livekit_agent/adapters/fastapi_internal_client.py
- Tests / Checks:
  - tests/services/livekit_agent/adapters/test_fastapi_internal_client.py
  - tests/services/livekit_agent/adapters/test_livekit_text_stream.py
  - tests/services/livekit_agent/core/test_interruption_gate.py
  - tests/services/livekit_agent/pipelines/test_realtime_text_to_speech.py
  - tests/services/agentscope_runtime/test_voice_mode_prompt.py
  - tests/api/v1/test_rtc_token.py
- Config / Runtime:
  - docker-compose.yml
  - services/livekit_agent/README.md
  - services/livekit_agent/pyproject.toml
  - services/livekit_agent/uv.lock

## Action Boundary
- Write Boundary:
  - services/livekit_agent/pyproject.toml
  - services/livekit_agent/uv.lock
  - services/livekit_agent/README.md
  - .agentdocs/workflow/2602102130-realtime-livekit-agent-task.md
  - .agentdocs/workflow/2602131031-realtime-livekit-fix-execution-task.md
  - .agentdocs/workflow/2602131414-realtime-e3-enhancements-voice-mode-e4-task.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/*
- Forbidden Writes:
  - FastAPI/runtime business logic or public API contracts.
  - WS TTS, performance tuning, or unrelated workflow/docs.
- Build Scope: APPROVED_SCOPE
- Escalation Rule: If implementation requires new realtime features, public contract changes, or non-realtime module edits beyond the frozen boundary, stop and return to PLAN_DRAFT.

## Invariants
  - Inference and interrupt routing stay through FastAPI internal endpoints only.
  - Closeout must not change realtime contract or semantics.

## Verification
- Must-Haves:
  - Explicit dependency risk is either fixed or downgraded with evidence and rationale.
  - README and key workflow docs no longer contradict code facts.
  - E4 checklist and minimal regression scope are written as executable artifacts.
- Verification Obligations:
  - Run targeted ruff and pytest for realtime-related files.
  - Update task-scoped evidence and workflow runtime pointers.
  - Leave a bounded CLOSE_REVIEW recheck scope.
- Reviewer Recheck Plan:
  - Reject if build introduces scope creep or reopens completed implementation work.
- UAT:
  - Use the E4 checklist with App or Playground plus Jaeger when environment is available.
