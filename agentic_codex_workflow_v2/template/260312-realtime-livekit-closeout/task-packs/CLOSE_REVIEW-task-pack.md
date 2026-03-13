# Task Pack

## Identity
- Task ID: 260312-realtime-livekit-closeout
- Title: 快速开发版收尾：Realtime + LiveKit
- Phase: CLOSE_REVIEW
- Current State: CLOSE_REVIEW
- Allowed Next State: ARCHIVE
- Owner: close_reviewer

## Understanding Proof
- Goal Restatement: Review the bounded realtime/livekit closeout and decide PASS or NEEDS_FIX based on code, tests, config, and task-scoped evidence.
- Explicit Non-Goals:
  - Do not implement WS realtime TTS, new UX features, or deeper performance tuning.
  - Do not reopen false interruption resume, 5xx retry, interrupt semantics, or voice-mode behavior.
- 95% Understanding Check: YES
- Missing Pieces:
  - <none>

## Source Pointers
- Spec Source:
  - .agentdocs/archive/260312-realtime-livekit-closeout/plan.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/workflow.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/findings/realtime-closeout-sync-snapshot-2026-03-12.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/findings/realtime-e4-acceptance-and-regression-pack-2026-03-12.md
- Review Inputs:
  - .agentdocs/archive/260312-realtime-livekit-closeout/task-packs/BUILD-task-pack.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/evidence/BUILD-truth-audit-20260312.json
  - .agentdocs/archive/260312-realtime-livekit-closeout/evidence/BUILD-ruff-check-20260312.json
  - .agentdocs/archive/260312-realtime-livekit-closeout/evidence/BUILD-pytest-20260312.json

## Frozen Context
- Frozen Decisions:
  - Closeout scope stays within explicit dependency, doc-state cleanup, and E4 acceptance/regression artifacts.
  - false interruption resume, 5xx retry, interrupt retry, and voice-mode thinking remain treated as already implemented.
- Known Non-Reopen Decisions:
  - WS realtime TTS and deeper realtime UX/performance work remain out of scope.
- Open Risks / Escalations:
  - Manual E4 items (compose/App/Playground/Jaeger) were documented but not executed in this session; review must treat them as UAT obligations, not fabricated evidence.
  - livekit-agent uv.lock was aligned by root package metadata update; review should confirm explicit dependency declaration is now contractually visible.
- Previous Findings:
  - <none>

## Read Boundary
- Must Read:
  - AGENTS.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/workflow.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/plan.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/task-packs/BUILD-task-pack.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/findings/realtime-closeout-sync-snapshot-2026-03-12.md
  - .agentdocs/archive/260312-realtime-livekit-closeout/findings/realtime-e4-acceptance-and-regression-pack-2026-03-12.md
  - services/livekit_agent/pyproject.toml
  - services/livekit_agent/uv.lock
  - services/livekit_agent/README.md
  - .agentdocs/workflow/2602102130-realtime-livekit-agent-task.md
  - .agentdocs/workflow/2602121821-livekit-agent-e3-hardening-tracing-task.md
  - .agentdocs/workflow/2602131031-realtime-livekit-fix-execution-task.md
  - .agentdocs/workflow/2602131414-realtime-e3-enhancements-voice-mode-e4-task.md
- Verified Adjacent Context:
  - .agentdocs/workflow/2602131555-livekit-agent-false-interruption-resume-task.md
- Unread But Potentially Relevant:
  - <none>
- Coverage Decision: SUFFICIENT

## Current Truth Anchors
- Code Paths:
  - services/livekit_agent/pyproject.toml
  - services/livekit_agent/uv.lock
  - services/livekit_agent/README.md
  - services/livekit_agent/adapters/dashscope_asr.py
  - services/livekit_agent/adapters/fastapi_internal_client.py
  - services/livekit_agent/adapters/livekit_text_stream.py
  - services/livekit_agent/app/worker_entrypoint.py
- Key Symbols / Entry Points:
  - services/livekit_agent/adapters/dashscope_asr.py::DashScopeOpenAICompatibleASR
  - services/livekit_agent/adapters/fastapi_internal_client.py::FastAPIInternalClient
  - services/livekit_agent/adapters/fastapi_internal_client.py::build_internal_responses_payload
  - services/livekit_agent/core/interruption_gate.py::InterruptionGate
  - services/livekit_agent/app/worker_entrypoint.py::_entrypoint
- Tests / Checks:
  - tests/services/livekit_agent/core/test_interruption_gate.py
  - tests/services/livekit_agent/adapters/test_fastapi_internal_client.py
  - tests/services/livekit_agent/adapters/test_livekit_text_stream.py
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
  - .agentdocs/archive/260312-realtime-livekit-closeout/reviews/close-review-*.json
- Forbidden Writes:
  - src/**, services/**, tests/**
  - .agentdocs/architecture/**
  - .agentdocs/prd/**
- Review Mode: FULL_REVIEW
- Escalation Rule: If a claimed fix requires new realtime features, API/contract changes, or non-realtime module edits, stop and return NEEDS_FIX with a minimal closure delta.

## Invariants
  - Inference and interrupt routing must continue through FastAPI internal endpoints only.
  - Close review must reject any scope creep beyond realtime closeout.

## Verification
- Must-Haves:
  - Explicit openai dependency is visible in livekit-agent service contract and lock metadata.
  - README and key legacy workflow docs no longer label completed realtime items as unfinished.
  - E4 acceptance/regression pack is executable and clearly separates automated regression from remaining manual UAT.
- Verification Obligations:
  - Sample the dependency/doc changes against code anchors and evidence bundles.
  - Recheck targeted lint/pytest evidence and ensure no business-code scope expansion occurred.
- Reviewer Recheck Plan:
  - Spot-check services/livekit_agent/pyproject.toml, services/livekit_agent/uv.lock, and services/livekit_agent/adapters/dashscope_asr.py for explicit dependency closure.
  - Spot-check README plus the 260210/260212/260213 workflow docs to ensure status wording matches code facts and closeout scope.
  - Verify BUILD-truth-audit / BUILD-ruff-check / BUILD-pytest evidence plus the E4 pack are mutually consistent.
- UAT:
  - If compose/App/Playground is not run during review, keep the E4 checklist items as user-side UAT obligations rather than failing the code/doc closeout.
