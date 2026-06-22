from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .contracts import ContractError, check_definition_hash, validate_check_definition


@dataclass(frozen=True)
class CheckExecution:
    check_id: str
    definition_hash: str
    runner: str
    argv: List[str]
    cwd: Path
    timeout_seconds: int
    started_monotonic: float
    ended_monotonic: float
    exit_code: int
    stdout: str
    stderr: str

    @property
    def duration_seconds(self) -> float:
        return round(self.ended_monotonic - self.started_monotonic, 6)


def resolve_cwd(root: Path, value: str) -> Path:
    candidate = (root / value).resolve()
    root_resolved = root.resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ContractError(f"Check cwd escapes the repository root: {value!r}") from exc
    if not candidate.is_dir():
        raise ContractError(f"Check cwd does not exist or is not a directory: {value!r}")
    return candidate


def execution_argv(definition: Mapping[str, Any]) -> List[str]:
    runner = str(definition.get("runner", "exec"))
    if runner == "exec":
        return [str(value) for value in definition.get("argv", [])]
    shell = str(definition.get("shell", "bash"))
    script = str(definition.get("script", ""))
    return [shell, "-lc", script]


def run_check(
    root: Path,
    check_id: str,
    definition: Mapping[str, Any],
    *,
    argv_override: Optional[Sequence[str]] = None,
    timeout_override: Optional[int] = None,
) -> CheckExecution:
    errors = validate_check_definition(check_id, definition)
    if errors:
        raise ContractError("; ".join(errors))
    runner = str(definition.get("runner", "exec"))
    declared_argv = execution_argv(definition)
    if argv_override:
        provided = list(argv_override)
        if provided and provided[0] == "--":
            provided = provided[1:]
        if provided != declared_argv:
            raise ContractError(
                f"Provided argv must exactly match check {check_id!r}; "
                f"declared={declared_argv!r}, provided={provided!r}."
            )
    argv = declared_argv
    timeout_seconds = int(definition.get("timeout_seconds", 1800))
    if timeout_override is not None:
        if timeout_override <= 0:
            raise ContractError("Timeout override must be positive.")
        timeout_seconds = min(timeout_seconds, timeout_override)
    cwd = resolve_cwd(root, str(definition.get("cwd", ".")))
    env = os.environ.copy()
    configured_env = definition.get("env", {})
    if configured_env:
        if not isinstance(configured_env, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in configured_env.items()):
            raise ContractError(f"Check {check_id} env must be a string-to-string object.")
        env.update(configured_env)
    started = time.monotonic()
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_seconds,
            shell=False,
        )
        exit_code = int(proc.returncode)
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = _decode_stream(exc.stdout)
        stderr = _decode_stream(exc.stderr) + f"\nHarness timeout after {timeout_seconds}s."
    except FileNotFoundError as exc:
        exit_code = 127
        stdout = ""
        stderr = str(exc)
    ended = time.monotonic()
    return CheckExecution(
        check_id=check_id,
        definition_hash=check_definition_hash(check_id, definition),
        runner=runner,
        argv=argv,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        started_monotonic=started,
        ended_monotonic=ended,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
    )


def red_failure_matches(execution: CheckExecution, expected: Mapping[str, Any]) -> tuple[bool, List[str]]:
    reasons: List[str] = []
    kind = str(expected.get("kind", "exit_nonzero"))
    if kind != "exit_nonzero":
        reasons.append(f"Unsupported expected failure kind: {kind!r}.")
    if execution.exit_code == 0:
        reasons.append("RED check exited zero; the behavior is not demonstrably red.")
    exit_codes = expected.get("exit_codes", [])
    if exit_codes:
        allowed = {int(code) for code in exit_codes if isinstance(code, int)}
        if execution.exit_code not in allowed:
            reasons.append(f"RED exit code {execution.exit_code} not in expected exit_codes {sorted(allowed)}.")
    _match_contains(execution.stdout, expected.get("stdout_contains", []), "stdout", reasons)
    _match_contains(execution.stderr, expected.get("stderr_contains", []), "stderr", reasons)
    _match_contains(execution.stdout + "\n" + execution.stderr, expected.get("combined_contains", []), "combined output", reasons)
    _match_regex(execution.stdout, expected.get("stdout_regex", []), "stdout", reasons)
    _match_regex(execution.stderr, expected.get("stderr_regex", []), "stderr", reasons)
    _match_regex(execution.stdout + "\n" + execution.stderr, expected.get("combined_regex", []), "combined output", reasons)
    return not reasons, reasons


def _match_contains(haystack: str, values: Any, label: str, reasons: List[str]) -> None:
    if not values:
        return
    if not isinstance(values, list):
        reasons.append(f"Expected {label}_contains must be an array.")
        return
    for value in values:
        needle = str(value)
        if needle not in haystack:
            reasons.append(f"Expected {label} to contain {needle!r}.")


def _match_regex(haystack: str, values: Any, label: str, reasons: List[str]) -> None:
    if not values:
        return
    if not isinstance(values, list):
        reasons.append(f"Expected {label}_regex must be an array.")
        return
    for value in values:
        pattern = str(value)
        try:
            matched = re.search(pattern, haystack, flags=re.MULTILINE) is not None
        except re.error as exc:
            reasons.append(f"Invalid expected {label} regex {pattern!r}: {exc}.")
            continue
        if not matched:
            reasons.append(f"Expected {label} to match /{pattern}/.")


def _decode_stream(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)
