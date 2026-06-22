# Tracked Feature Specifications

Approved user/product intent for non-trivial Work Units lives here as `docs/spec/<WU-ID>.md`.

Each file contains human-readable walkthrough notes plus one marked canonical JSON contract. The contract records intent, observable outcomes, non-goals, scope, claim IDs, structured check definitions, stop conditions, clarification decisions, context pointers and stable delivery references. It must remain understandable without access to an agent transcript.

Technical plans, receipts, command logs, Reviewer session lineage, checkpoints and handoffs remain under ignored `.harness/`.

```bash
# Local runtime still exists and belongs to this repository/worktree/branch.
harnessctl resume-session --id <WU-ID>

# Local runtime is gone; deliberately rebuild a conservative starting point.
harnessctl reconstruct --id <WU-ID>
```

Reconstruction never claims that old local evidence or review survived.
