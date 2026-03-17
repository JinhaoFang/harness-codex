# Optional modules on top of the v3 runtime

These modules are intentionally **not** part of the runtime core.
Use them only when the task or repository actually benefits from them.

## Module classes

### 1. Repo guardrails
- `.githooks/*`
- `.github/workflows/security-checks.yml`

Purpose: prevent obvious secrets, dangerous commands, and protected-branch mistakes.

### 2. External collaboration adapters
- `github-collaboration`

Purpose: mirror task progress or review results into external systems without making those systems the source of truth.

### 3. Execution workspace helpers
- `worktree-isolation`
- `session-recovery`

Purpose: isolate risky work, resume interrupted sessions, and keep parallel work disciplined without introducing a second state ledger.

### 4. Durable contract artifacts
- `docs/contracts/*`
- `contract-artifacts`

Purpose: capture business/API/UI contracts that should outlive one task and be reusable across tasks.

## Runtime boundary

Optional modules may:
- read `plan.md`, `workflow.md`, reviews, evidence, and current code/test reality
- add repo tooling or external mirrors
- generate removable helper artifacts

Optional modules may not:
- redefine Goal truth
- redefine Process truth
- replace review verdicts
- create a second long-term task ledger
