---
name: harness-ground
description: Ground a spec, plan, review, or debugging task in current repository truth using minimal targeted exploration. Use before asking factual questions or trusting summaries/documents about current behavior（before using harness-clarigy）.
---

# Harness Ground

Read in this order:

1. `docs/spec/<WU-ID>.md` for approved desired behavior.
2. Nearby project instructions and local rules.
3. Current implementation and public interfaces.
4. Tests that define or contradict current behavior.
5. Runtime/config/CI surfaces needed for the claim.
6. Only the ADRs/docs explicitly relevant to touched areas.

Record concise pointers, not copied content. Surface code/docs/test conflicts. Do not promote a proposed design into current project truth before it is implemented and verified.
