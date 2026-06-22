---
name: harness-spec
description: Create and obtain explicit user approval for the tracked feature spec under docs/spec after clarification. Use before technical planning for any non-trivial coding task.
---

# Harness Spec

The tracked spec is desired-intent truth. Current code/tests/runtime remain current-project truth.

1. Create the Work Unit if needed:

```bash
harnessctl new --id <WU-ID> --title "..." --type <type> --risk <risk>
```

2. Complete `docs/spec/<WU-ID>.md` with observable behavior, non-goals, write boundary, out-of-bounds paths, executable evidence claims, stop conditions, clarification decisions, and minimal context pointers.
   `scope.write_boundary` and `scope.out_of_bounds` must be repo-relative path/glob patterns such as `app/**`, `tests/**`, or `package.json`, not descriptive prose. `scope.likely_changed_areas` may stay higher-level, but path-like values are preferred.
3. Do not put the technical implementation plan into the tracked spec.
4. Run:

```bash
harnessctl check --id <WU-ID> --gate spec --strict
```

5. Walk the spec through with the user. Only after explicit approval run:

```bash
harnessctl approve-spec --id <WU-ID> --approved-by human:<IDENTITY> --approval-ref "<issue comment, review note, or other durable approval reference>"
```

If the tracked spec changes later, approval and plan review become stale. Re-approve intentionally; never let a future design artifact rewrite current repository facts.
