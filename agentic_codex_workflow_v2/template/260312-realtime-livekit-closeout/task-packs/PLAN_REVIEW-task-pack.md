# Task Pack

## Identity
- Task ID: 260312-realtime-livekit-closeout
- Title: 快速开发版收尾：Realtime + LiveKit
- Phase: PLAN_REVIEW
- Current State: PLAN_DRAFT
- Allowed Next State: PLAN_REVIEW
- Owner: main

## Understanding Proof
- Goal Restatement: Freeze the realtime/livekit closeout scope to E4 acceptance closure, explicit openai dependency declaration, and README/workflow status unification without reopening completed implementation work.
- Explicit Non-Goals:
  - Implement WS realtime TTS or broader performance tuning.
  - Reopen false interruption resume, 5xx retry, or voice-mode functionality as new feature work.
  - Expand into media, observability Phase 1, or fastapi/agent closeout.
- 95% Understanding Check: YES
- Missing Pieces:
  - <none>

## Source Pointers
- Spec Source:
  - .agentdocs/archive/260312-realtime-livekit-closeout/plan.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/workflow.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/findings/realtime-closeout-sync-snapshot-2026-03-12.md
- Review Inputs:
  - .agentdocs/archive/260312-realtime-livekit-closeout/plan.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/workflow.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/findings/realtime-closeout-sync-snapshot-2026-03-12.md
  - .agentdocs/workflow/2602102130-realtime-livekit-agent-task.md
  - .agentdocs/workflow/2602131031-realtime-livekit-fix-execution-task.md
  - .agentdocs/workflow/2602131414-realtime-e3-enhancements-voice-mode-e4-task.md
  - .agentdocs/workflow/2602131555-livekit-agent-false-interruption-resume-task.md

## Frozen Context
- Frozen Decisions:
  - Closeout scope is limited to E4 acceptance closure, explicit dependency declaration, and doc-state cleanup.
  - false interruption resume is already implemented and must not be reopened as new feature scope.
  - legacy workflow remains reference-only; only the most misleading status lines may be updated.
- Known Non-Reopen Decisions:
  - Do not reopen fastapi+agent closeout or observability/media scope.
- Open Risks / Escalations:
  - Manual acceptance and Jaeger checks depend on local compose/App/Playground environment.
  - openai dependency and uv.lock alignment may require a minimal but careful lock refresh.
  - Long legacy workflow chain can cause duplicate or conflicting status claims.
- Previous Findings:
  - <none>

## Read Boundary
- Must Read:
  - AGENTS.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/plan.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/workflow.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/findings/realtime-closeout-sync-snapshot-2026-03-12.md
  - .agentdocs/workflow/2602102130-realtime-livekit-agent-task.md
  - .agentdocs/workflow/2602131031-realtime-livekit-fix-execution-task.md
  - .agentdocs/workflow/2602131414-realtime-e3-enhancements-voice-mode-e4-task.md
  - .agentdocs/workflow/2602131555-livekit-agent-false-interruption-resume-task.md
- Verified Adjacent Context:
  - .agentdocs/workflow/2602121821-livekit-agent-e3-hardening-tracing-task.md
  - .agentdocs/workflow/2602131329-realtime-optimization-next-steps.md
- Unread But Potentially Relevant:
  - tests/e2e/test_agent_voice_transcript_e2e.py
  - tests/e2e/test_voice_business_domains_e2e.py
- Coverage Decision: SUFFICIENT

## Current Truth Anchors
- Code Paths:
  - services/livekit_agent/**
  - tests/services/livekit_agent/**
  - services/agentscope_runtime/agent/factory.py
  - tests/services/agentscope_runtime/test_voice_mode_prompt.py
  - src/app/api/v1/rtc.py
- Key Symbols / Entry Points:
  - services/livekit_agent/app/worker_entrypoint.py
  - services/livekit_agent/adapters/fastapi_internal_client.py
  - services/livekit_agent/adapters/dashscope_asr.py
  - services/livekit_agent/adapters/livekit_text_stream.py
  - services/livekit_agent/core/interruption_gate.py
  - services/agentscope_runtime/agent/factory.py::build_model_generate_kwargs
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
  - .agentdocs/archive/260312-realtime-livekit-closeout/*
  - services/livekit_agent/pyproject.toml
  - services/livekit_agent/uv.lock
  - services/livekit_agent/README.md
  - .agentdocs/workflow/2602102130-realtime-livekit-agent-task.md
  - .agentdocs/workflow/2602131031-realtime-livekit-fix-execution-task.md
  - .agentdocs/workflow/2602131414-realtime-e3-enhancements-voice-mode-e4-task.md
- Forbidden Writes:
  - FastAPI/runtime architecture or non-realtime modules.
  - WS TTS, new realtime features, or broad performance refactors.
- Review Mode: FULL_REVIEW
- Escalation Rule: If review finds scope expansion beyond closeout (for example WS TTS, new realtime features, or cross-module refactors), stop and route back to PLAN_DRAFT.

## Invariants
  - livekit-agent must continue to route inference through FastAPI internal endpoints only.
  - Realtime closeout must not change interrupt semantics or public API contract.

## Verification
- Must-Haves:
  - A task-scoped truth matrix that separates real gaps from doc drift.
  - A bounded E4 checklist and minimal regression scope.
  - No scope creep into WS TTS or new feature work.
- Verification Obligations:
  - Plan scope closes only true realtime tail items and matches current code facts.
  - Review inputs are sufficient to validate false-interruption, retry, and voice-mode status as already implemented.
  - Write boundary is limited to realtime closeout files.
- Reviewer Recheck Plan:
  - Confirm README and key legacy workflow updates are necessary and minimal.
  - Confirm explicit dependency handling is treated as real gap, not optional polish.
- UAT:
  - Replay the documented E4 manual acceptance checklist if environment is available.
