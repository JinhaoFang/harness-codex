# Workflow

## 1. Clarify

Start with `harness-clarify`. Ask one high-value question at a time, give a recommended answer when useful, and inspect the repository when the answer is already available there. Do not modify product files.

The output is a draft `docs/spec/<WU-ID>.md` containing intent, observable outcome, non-goals, write boundary, out-of-bounds paths, evidence claims, stop conditions, decisions and remaining assumptions.

## 2. Approve the tracked spec

The user approves a concrete revision:

```bash
python3 harness/cli/harnessctl.py approve-spec \
  --id <WU-ID> --approved-by human:<identity> --approval-ref <issue/comment/ref>
```

The controller writes approval metadata and a content hash into the tracked spec. Editing approved content makes that marker stale until it is explicitly reapproved or amended.

## 3. Design locally

The technical plan is an intermediate artifact:

```text
.harness/work-units/active/<WU-ID>/plan.md
```

It must be rebuilt from the approved spec, current code/tests/runtime, Git/GitHub context and local rules. It includes architecture tradeoffs, the change map, TDD behavior slices, verification commands, risks and the questions the reviewer must revisit.

## 4. Plan review

A reviewer reads the current repository, approved spec and local plan directly. It does not review formatting alone and does not rely primarily on the planner's narrative.

```bash
harnessctl request-review --mode plan --reviewer-id <REVIEWER-ID> --reviewer-session <REVIEW-SESSION> --planner-id <PLANNER-ID> --planner-session <PLANNER-SESSION>
harnessctl submit-review  --mode plan --request-id <ID> --decision PASS ...
```

The first request creates one review track. Close review normally reuses that reviewer identity.

## 5. Isolated implementation with TDD

After plan review:

```bash
harnessctl start-work --id <WU-ID> --builder-id <ID> --builder-session <SESSION>
```

Use a separate worker session/worktree where practical. For behavior changes:

```bash
harnessctl verify --claim EV1 --phase red   --expect fail -- <targeted-test>
harnessctl verify --claim EV1 --phase green --expect pass -- <targeted-test>
harnessctl verify --claim EV1 --phase final
```

A RED run counts only when the command actually exits non-zero as expected. The plan must state the expected failure reason so the worker checks that the test failed for the intended behavior rather than setup noise. GREEN helps the worker keep the slice honest during implementation; final verification is the acceptance-grade receipt used by completion gates.

## 6. Verification

`harnessctl verify` launches the process, captures stdout/stderr, records argv/cwd/time/exit code, and binds the receipt to the current implementation content. Users do not provide a `pass` result.

If a required check cannot run, use `record-skipped` to make the blocker visible. The task remains blocked until the evidence is produced or the evidence contract is materially revised and the spec is reapproved.

## 7. Close review

The same review track reads the current diff, code, tests and fresh evidence. The reviewer is read-only; findings return to the worker. Changes after evidence or close review invalidate the affected gate.

```bash
harnessctl request-review --mode close --reviewer-id <same-ID> --reviewer-session <fresh-session>
harnessctl submit-review  --mode close --request-id <ID> --decision PASS --evidence-ref <receipt>
harnessctl finalize-check --id <WU-ID> --strict
```

## 8. Git/GitHub and recovery

Git branches/worktrees isolate execution; commits and diffs are execution truth; GitHub issues/PRs/CI/human reviews are collaboration and integration truth. They do not replace the approved spec or controller-observed verification.

Generate a local handoff before transferring work. To continue an existing local handoff or cleared blocker, run `resume-work` with a fresh worker session; no generic state mutation command is provided. If `.harness/` is lost:

```bash
harnessctl resume --id <WU-ID>
```

An approved marker in the tracked spec allows recovery into `spec_approved`; otherwise recovery returns to clarification. Old local plan, evidence and review are never invented.
