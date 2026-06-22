"""Thin, fail-closed adapters for platform-owned coding-agent sessions.

The controller remains lifecycle authority. These adapters only create/resume a
platform process, capture its real session/thread identifier, and return the
platform's structured result. Command construction is kept pure for conformance
and dry-run tests.
"""
from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence


class AdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class CapabilityProbe:
    platform: str
    available: bool
    executable: str
    capabilities: Dict[str, bool]
    detail: str = ""


@dataclass(frozen=True)
class ReviewRun:
    platform: str
    session_id: str
    raw_result: str
    structured_result: Dict[str, Any]
    command: List[str]


@dataclass(frozen=True)
class WorkerRun:
    platform: str
    session_id: str
    raw_result: str
    structured_result: Dict[str, Any]
    command: List[str]


@dataclass(frozen=True)
class GoalBinding:
    """A persisted Codex thread Goal created through the stable app-server API."""

    platform: str
    thread_id: str
    session_id: str
    objective: str
    goal: Dict[str, Any]
    transcript: List[Dict[str, Any]]


class _CodexAppServer:
    """Small synchronous JSONL client used only for thread/goal bootstrap.

    Execution still happens through ``codex exec``. Keeping this adapter narrow
    avoids growing a second orchestration runtime while allowing the Harness to
    bind the worker to Codex's actual persisted Goal state.
    """

    def __init__(self, binary: str, *, cwd: Path) -> None:
        try:
            self.process = subprocess.Popen(
                [binary, "app-server"],
                cwd=cwd,
                env=os.environ.copy(),
                text=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
            )
        except OSError as exc:
            raise AdapterError(f"Could not start Codex app-server: {exc}") from exc
        if self.process.stdin is None or self.process.stdout is None or self.process.stderr is None:
            self.close()
            raise AdapterError("Codex app-server did not expose the required stdio transport.")
        self._messages: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self.transcript: List[Dict[str, Any]] = []
        self.stderr_lines: List[str] = []
        self._stdout_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._stderr_thread = threading.Thread(target=self._read_stderr, daemon=True)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def _read_stdout(self) -> None:
        assert self.process.stdout is not None
        for raw_line in self.process.stdout:
            line = raw_line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                value = {"method": "transport/non-json", "params": {"line": line}}
            if isinstance(value, dict):
                self._messages.put(value)
        self._messages.put({"method": "transport/eof"})

    def _read_stderr(self) -> None:
        assert self.process.stderr is not None
        for raw_line in self.process.stderr:
            self.stderr_lines.append(raw_line.rstrip())
            if len(self.stderr_lines) > 200:
                del self.stderr_lines[:50]

    def _send(self, message: Mapping[str, Any]) -> None:
        if self.process.poll() is not None:
            detail = "\n".join(self.stderr_lines[-20:])
            raise AdapterError(f"Codex app-server exited before request dispatch. {detail}".strip())
        assert self.process.stdin is not None
        try:
            self.process.stdin.write(json.dumps(dict(message), ensure_ascii=False) + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            detail = "\n".join(self.stderr_lines[-20:])
            raise AdapterError(f"Codex app-server transport failed: {exc}. {detail}".strip()) from exc

    def notify(self, method: str, params: Optional[Mapping[str, Any]] = None) -> None:
        self._send({"method": method, "params": dict(params or {})})

    def request(
        self,
        method: str,
        params: Optional[Mapping[str, Any]],
        *,
        request_id: int,
        timeout_seconds: int,
    ) -> Dict[str, Any]:
        self._send({"method": method, "id": request_id, "params": dict(params or {})})
        deadline = time.monotonic() + timeout_seconds
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AdapterError(f"Codex app-server request {method} timed out after {timeout_seconds}s.")
            try:
                message = self._messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise AdapterError(f"Codex app-server request {method} timed out after {timeout_seconds}s.") from exc
            self.transcript.append(message)
            if message.get("method") == "transport/eof":
                detail = "\n".join(self.stderr_lines[-20:])
                raise AdapterError(f"Codex app-server closed while handling {method}. {detail}".strip())
            if message.get("id") != request_id:
                continue
            if message.get("error"):
                raise AdapterError(f"Codex app-server {method} failed: {json.dumps(message['error'], ensure_ascii=False)}")
            result = message.get("result", {})
            if not isinstance(result, dict):
                raise AdapterError(f"Codex app-server {method} returned a non-object result.")
            return dict(result)

    def initialize(self, *, timeout_seconds: int) -> None:
        self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "coding_agent_harness",
                    "title": "Coding Agent Harness",
                    "version": "0.3.0",
                }
            },
            request_id=0,
            timeout_seconds=timeout_seconds,
        )
        self.notify("initialized", {})

    def close(self) -> None:
        process = getattr(self, "process", None)
        if process is None:
            return
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        if process.poll() is None:
            try:
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
        stdout_thread = getattr(self, "_stdout_thread", None)
        stderr_thread = getattr(self, "_stderr_thread", None)
        for thread in (stdout_thread, stderr_thread):
            if thread is not None:
                thread.join(timeout=0.5)
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass


def _help(binary: str, args: Sequence[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            [binary, *args],
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    return proc.returncode, proc.stdout


def probe(platform: str, executable: str = "") -> CapabilityProbe:
    if platform == "manual":
        return CapabilityProbe("manual", True, "", {"resume": False, "structured_output": False, "read_only": True, "workspace_write": False})
    if platform not in {"codex", "claude"}:
        return CapabilityProbe(platform, False, executable, {}, f"unknown platform {platform!r}")
    binary = executable or ("codex" if platform == "codex" else "claude")
    resolved = shutil.which(binary)
    if not resolved:
        return CapabilityProbe(platform, False, binary, {}, "executable not found")

    return_code, top_help = _help(resolved, ["--help"])
    detail = top_help
    if platform == "codex":
        exec_code, exec_help = _help(resolved, ["exec", "--help"])
        resume_code, resume_help = _help(resolved, ["exec", "resume", "--help"])
        app_server_code, app_server_help = _help(resolved, ["app-server", "--help"])
        help_text = "\n".join((top_help, exec_help, resume_help, app_server_help)).lower()
        capabilities = {
            "resume": resume_code == 0 and "resume" in help_text,
            "structured_output": "--json" in help_text and "--output-schema" in help_text,
            "read_only": "--sandbox" in help_text,
            "workspace_write": "workspace-write" in help_text or "--sandbox" in help_text,
            "goal_control_plane": app_server_code == 0,
        }
        available = return_code == 0 and exec_code == 0
        detail = "\n".join((top_help, exec_help, resume_help, app_server_help))[:3000]
    else:
        help_text = top_help.lower()
        capabilities = {
            "resume": "--resume" in help_text,
            "structured_output": "--output-format" in help_text and ("--json-schema" in help_text or "json" in help_text),
            "read_only": "--permission-mode" in help_text or "--tools" in help_text,
            "workspace_write": "--permission-mode" in help_text or "--tools" in help_text,
        }
        available = return_code == 0
    return CapabilityProbe(platform, available, resolved, capabilities, detail[:3000])


def ensure_codex_goal(
    *,
    cwd: Path,
    objective: str,
    session_id: str = "",
    executable: str = "",
    token_budget: int = 40000,
    timeout_seconds: int = 30,
) -> GoalBinding:
    """Create/resume a Codex thread and bind its actual persisted Goal.

    Goal state augments long-running execution. Failure to create it must never
    weaken Controller evidence/review gates; callers may explicitly degrade to
    ordinary ``codex exec`` while recording the adapter warning.
    """

    normalized_objective = objective.strip()
    if not normalized_objective:
        raise AdapterError("Codex Goal objective must not be empty.")
    if len(normalized_objective) > 4000:
        raise AdapterError("Codex Goal objective exceeds the 4,000-character platform limit.")
    if token_budget <= 0:
        raise AdapterError("Codex Goal token budget must be positive.")
    binary = executable or "codex"
    resolved = shutil.which(binary)
    if not resolved:
        raise AdapterError("Codex executable not found for Goal bootstrap.")

    client = _CodexAppServer(resolved, cwd=cwd)
    try:
        client.initialize(timeout_seconds=timeout_seconds)
        if session_id:
            thread_result = client.request(
                "thread/resume",
                {"threadId": session_id},
                request_id=1,
                timeout_seconds=timeout_seconds,
            )
        else:
            thread_result = client.request(
                "thread/start",
                {
                    "cwd": str(cwd),
                    "sandbox": "workspaceWrite",
                    "serviceName": "coding_agent_harness",
                },
                request_id=1,
                timeout_seconds=timeout_seconds,
            )
        thread = thread_result.get("thread", {})
        if not isinstance(thread, dict) or not str(thread.get("id", "")):
            raise AdapterError("Codex app-server did not return a thread id.")
        thread_id = str(thread["id"])
        session_root = str(thread.get("sessionId", "")) or thread_id
        goal_result = client.request(
            "thread/goal/set",
            {
                "threadId": thread_id,
                "objective": normalized_objective,
                "status": "active",
                "tokenBudget": token_budget,
            },
            request_id=2,
            timeout_seconds=timeout_seconds,
        )
        goal = goal_result.get("goal", {})
        if not isinstance(goal, dict):
            raise AdapterError("Codex app-server did not return persisted Goal state.")
        if str(goal.get("threadId", "")) != thread_id or str(goal.get("objective", "")) != normalized_objective:
            raise AdapterError("Codex app-server Goal response did not match the requested thread/objective.")
        return GoalBinding(
            platform="codex",
            thread_id=thread_id,
            session_id=session_root,
            objective=normalized_objective,
            goal=dict(goal),
            transcript=list(client.transcript),
        )
    finally:
        client.close()


def review_command(
    platform: str,
    *,
    prompt_file: Path,
    schema_file: Path,
    cwd: Path,
    session_id: str = "",
    executable: str = "",
    output_file: Optional[Path] = None,
) -> List[str]:
    prompt = prompt_file.read_text(encoding="utf-8")
    if platform == "codex":
        binary = executable or "codex"
        if session_id:
            command = [binary, "exec", "resume", session_id, "--json", "--output-schema", str(schema_file)]
        else:
            command = [binary, "exec", "--json", "--sandbox", "read-only", "--output-schema", str(schema_file), "-C", str(cwd)]
        if output_file is not None:
            command.extend(["--output-last-message", str(output_file)])
        command.append(prompt)
        return command
    if platform == "claude":
        binary = executable or "claude"
        # Claude's CLI accepts the JSON Schema itself, not a filesystem path.
        # Keep the schema in a file inside the Harness for auditability, but
        # project its content into the platform-specific argv here.
        inline_schema = schema_file.read_text(encoding="utf-8")
        command = [
            binary,
            "-p",
            "--output-format",
            "json",
            "--permission-mode",
            "plan",
            "--tools",
            "Read,Grep,Glob,Bash",
            "--json-schema",
            inline_schema,
            "--agent",
            "harness-reviewer",
        ]
        if session_id:
            command.extend(["--resume", session_id])
        command.append(prompt)
        return command
    raise AdapterError(f"Platform {platform!r} cannot be dispatched automatically.")


def worker_command(
    platform: str,
    *,
    prompt_file: Path,
    schema_file: Path,
    cwd: Path,
    session_id: str = "",
    executable: str = "",
    output_file: Optional[Path] = None,
) -> List[str]:
    prompt = prompt_file.read_text(encoding="utf-8")
    if platform == "codex":
        binary = executable or "codex"
        if session_id:
            command = [binary, "exec", "resume", session_id, "--json", "--output-schema", str(schema_file)]
        else:
            command = [binary, "exec", "--json", "--sandbox", "workspace-write", "--output-schema", str(schema_file), "-C", str(cwd)]
        if output_file is not None:
            command.extend(["--output-last-message", str(output_file)])
        command.append(prompt)
        return command
    if platform == "claude":
        binary = executable or "claude"
        inline_schema = schema_file.read_text(encoding="utf-8")
        command = [
            binary,
            "-p",
            "--output-format",
            "json",
            "--permission-mode",
            "acceptEdits",
            "--tools",
            "Read,Grep,Glob,Edit,Write,Bash",
            "--json-schema",
            inline_schema,
            "--agent",
            "harness-worker",
        ]
        if session_id:
            command.extend(["--resume", session_id])
        command.append(prompt)
        return command
    raise AdapterError(f"Platform {platform!r} cannot be dispatched automatically.")


def _required_capabilities(platform: str, role: str) -> tuple[str, ...]:
    if role == "reviewer":
        return ("resume", "structured_output", "read_only")
    return ("structured_output", "workspace_write")


def _run_agent(
    role: str,
    platform: str,
    *,
    prompt_file: Path,
    schema_file: Path,
    cwd: Path,
    session_id: str = "",
    executable: str = "",
    timeout_seconds: int = 3600,
    env: Optional[Mapping[str, str]] = None,
) -> tuple[str, str, Dict[str, Any], List[str]]:
    probe_result = probe(platform, executable)
    if not probe_result.available:
        raise AdapterError(f"{platform} adapter unavailable: {probe_result.detail}")
    missing = [name for name in _required_capabilities(platform, role) if not probe_result.capabilities.get(name)]
    if missing:
        raise AdapterError(f"{platform} {role} adapter capability probe failed: missing {', '.join(missing)}")
    output_file = prompt_file.with_suffix(".result.json") if platform == "codex" else None
    builder = review_command if role == "reviewer" else worker_command
    command = builder(
        platform,
        prompt_file=prompt_file,
        schema_file=schema_file,
        cwd=cwd,
        session_id=session_id,
        executable=probe_result.executable,
        output_file=output_file,
    )
    process_env = os.environ.copy()
    if env:
        process_env.update({str(key): str(value) for key, value in env.items()})
    try:
        proc = subprocess.run(
            command,
            cwd=cwd,
            env=process_env,
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise AdapterError(f"{platform} {role} timed out after {timeout_seconds}s") from exc
    if proc.returncode != 0:
        raise AdapterError(f"{platform} {role} exited {proc.returncode}: {proc.stderr[-2000:]}")
    if platform == "codex":
        detected_session = session_id
        for line in proc.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "thread.started":
                detected_session = str(event.get("thread_id", "")) or detected_session
        raw = output_file.read_text(encoding="utf-8") if output_file and output_file.exists() else proc.stdout
        structured = _extract_json_object(raw)
        return detected_session, raw, structured, command
    envelope = _extract_json_object(proc.stdout)
    detected_session = str(envelope.get("session_id", "")) or session_id
    structured_value = envelope.get("structured_output") or envelope.get("result") or envelope
    if isinstance(structured_value, str):
        structured = _extract_json_object(structured_value)
    elif isinstance(structured_value, dict):
        structured = dict(structured_value)
    else:
        raise AdapterError(f"Claude response did not contain structured {role} output.")
    return detected_session, proc.stdout, structured, command


def run_review(
    platform: str,
    *,
    prompt_file: Path,
    schema_file: Path,
    cwd: Path,
    session_id: str = "",
    executable: str = "",
    timeout_seconds: int = 3600,
) -> ReviewRun:
    detected, raw, structured, command = _run_agent(
        "reviewer",
        platform,
        prompt_file=prompt_file,
        schema_file=schema_file,
        cwd=cwd,
        session_id=session_id,
        executable=executable,
        timeout_seconds=timeout_seconds,
        env={"HARNESS_ROLE": "reviewer"},
    )
    return ReviewRun(platform, detected, raw, structured, command)


def run_worker(
    platform: str,
    *,
    prompt_file: Path,
    schema_file: Path,
    cwd: Path,
    session_id: str = "",
    executable: str = "",
    timeout_seconds: int = 7200,
    env: Optional[Mapping[str, str]] = None,
) -> WorkerRun:
    detected, raw, structured, command = _run_agent(
        "worker",
        platform,
        prompt_file=prompt_file,
        schema_file=schema_file,
        cwd=cwd,
        session_id=session_id,
        executable=executable,
        timeout_seconds=timeout_seconds,
        env={"HARNESS_ROLE": "worker", **dict(env or {})},
    )
    return WorkerRun(platform, detected, raw, structured, command)


def _extract_json_object(text: str) -> Dict[str, Any]:
    stripped = text.strip()
    try:
        value = json.loads(stripped)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    starts = [index for index, char in enumerate(text) if char == "{"]
    for start in starts:
        try:
            value, _end = json.JSONDecoder().raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise AdapterError("Agent output did not contain a JSON object.")
