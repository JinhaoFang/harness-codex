#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ALLOWED_STATES = {
    "DISCUSS",
    "ALIGN_PROOF",
    "ALIGN",
    "BOOTSTRAP",
    "ISSUE_SYNC",
    "PLAN_DRAFT",
    "PLAN_REVIEW",
    "BUILD",
    "CLOSE_REVIEW",
    "ARCHIVE",
    "BLOCKED",
    "EXCEPTION_RECOVERY",
}

LEGAL_TRANSITIONS = {
    "DISCUSS": {"ALIGN_PROOF", "EXCEPTION_RECOVERY"},
    "ALIGN_PROOF": {"BOOTSTRAP", "EXCEPTION_RECOVERY"},
    "BOOTSTRAP": {"ISSUE_SYNC", "EXCEPTION_RECOVERY"},
    "ISSUE_SYNC": {"PLAN_DRAFT", "EXCEPTION_RECOVERY"},
    "PLAN_DRAFT": {"PLAN_REVIEW", "EXCEPTION_RECOVERY"},
    "PLAN_REVIEW": {"PLAN_DRAFT", "BUILD", "EXCEPTION_RECOVERY"},
    "BUILD": {"BUILD", "PLAN_DRAFT", "CLOSE_REVIEW", "BLOCKED", "EXCEPTION_RECOVERY"},
    "CLOSE_REVIEW": {"BUILD", "ARCHIVE", "BLOCKED", "EXCEPTION_RECOVERY"},
    "ARCHIVE": set(),
    "BLOCKED": {"DISCUSS", "ALIGN_PROOF", "BOOTSTRAP", "ISSUE_SYNC", "PLAN_DRAFT", "PLAN_REVIEW", "BUILD", "CLOSE_REVIEW", "EXCEPTION_RECOVERY"},
    "EXCEPTION_RECOVERY": {"DISCUSS", "ALIGN_PROOF", "PLAN_DRAFT", "PLAN_REVIEW", "BUILD", "CLOSE_REVIEW", "BLOCKED"},
}


def extract(text: str, label: str) -> str:
    m = re.search(rf"^- {re.escape(label)}: (?P<v>.+)$", text, re.MULTILINE)
    return m.group("v").strip() if m else ""


def normalize_ref(value: str) -> str:
    return value.strip().strip("`")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workflow", required=True)
    args = ap.parse_args()

    path = Path(args.workflow)
    text = path.read_text(encoding="utf-8")
    errors = []

    current_state = extract(text, "Current State")
    allowed_next = extract(text, "Allowed Next State")
    illegal_seen = extract(text, "Illegal Transition Seen")
    exception_status = extract(text, "Exception Status")
    draft_status = extract(text, "Draft Status")
    review_status = extract(text, "Review Status")
    final_status = extract(text, "Final Status")

    if current_state not in ALLOWED_STATES:
        errors.append(f"Invalid Current State: {current_state or '<missing>'}")

    if current_state in LEGAL_TRANSITIONS:
        next_tokens = [token.strip() for token in allowed_next.split("|") if token.strip()]
        legal_next = LEGAL_TRANSITIONS[current_state]
        if not legal_next:
            if (allowed_next or "").strip() not in {"<none>", "NONE", "<NONE>"}:
                errors.append(f"{current_state} requires Allowed Next State = <none>")
        elif not next_tokens:
            errors.append(f"{current_state} requires at least one Allowed Next State")
        else:
            invalid = [token for token in next_tokens if token not in legal_next]
            if invalid:
                errors.append(f"{current_state} has invalid Allowed Next State values: {', '.join(invalid)}")

    if current_state == "BUILD" and review_status != "PASS":
        errors.append("BUILD requires Review Status = PASS")

    if current_state == "ARCHIVE" and final_status != "PASS":
        errors.append("ARCHIVE requires Final Status = PASS")

    if final_status == "PASS" and review_status != "PASS":
        errors.append("Final Status = PASS requires Plan Review PASS")

    if illegal_seen == "YES" and exception_status == "NONE":
        errors.append("Illegal transition seen requires Exception Status != NONE")

    phase_lines = []
    in_phase_board = False
    for line in text.splitlines():
        if line.startswith("## 4) Phase Board"):
            in_phase_board = True
            continue
        if in_phase_board and line.startswith("## "):
            break
        if in_phase_board and line.startswith("|") and "Plan §" in line:
            phase_lines.append(line)

    for line in phase_lines:
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 8:
            continue
        phase, _spec, owner, status, verify_run, evidence_ref, _checkpoint, _handoff = cols[:8]
        verify_value = verify_run or ""
        normalized_ref = normalize_ref(evidence_ref)
        if owner in {"plan_reviewer", "close_reviewer"}:
            errors.append(f"{phase}: Phase Board must not track review gates owned by {owner}")
        if status == "DONE":
            if not verify_value:
                errors.append(f"{phase}: DONE phase missing Verification")
            if not evidence_ref:
                errors.append(f"{phase}: DONE phase missing Evidence Ref")
            elif "/reviews/" in normalized_ref:
                errors.append(f"{phase}: Evidence Ref must not point to reviews/")
            elif "/evidence/" not in normalized_ref:
                errors.append(f"{phase}: Evidence Ref does not point to an evidence bundle")

    if not allowed_next:
        errors.append("Missing Allowed Next State")

    if errors:
        print("WORKFLOW_STATE_CHECK=FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("WORKFLOW_STATE_CHECK=PASS")
    print(f"- Current State: {current_state}")
    print(f"- Allowed Next State: {allowed_next}")
    print(f"- Review Status: {review_status or '<missing>'}")
    print(f"- Final Status: {final_status or '<missing>'}")
    print(f"- Exception Status: {exception_status or '<missing>'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
