from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

ROOT_MARKERS = (".git", "pyproject.toml", "AGENTS.md", "CLAUDE.md")
NON_IMPLEMENTATION_PREFIXES = (".harness/", "docs/spec/")
NON_IMPLEMENTATION_EXACT = {".gitignore"}


def safe_cwd() -> Path:
    """Return a usable cwd even when a caller deleted its current directory."""
    try:
        return Path.cwd()
    except FileNotFoundError:
        for candidate in (os.environ.get("PWD", ""), os.environ.get("HOME", ""), "/"):
            if candidate and Path(candidate).is_dir():
                return Path(candidate)
        return Path("/")


def find_root(start: Path) -> Path:
    try:
        cur = start.resolve()
    except FileNotFoundError:
        cur = safe_cwd().resolve()
    while True:
        if any((cur / marker).exists() for marker in ROOT_MARKERS):
            return cur
        if cur.parent == cur:
            return cur
        cur = cur.parent


def _run_git_process(
    root: Path,
    args: Sequence[str],
    *,
    timeout: int = 15,
    binary: bool = False,
) -> subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[str] | None:
    try:
        configured_timeout = float(os.environ.get("HARNESS_GIT_TIMEOUT_SECONDS", timeout))
        env = {
            **os.environ,
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
        }
        return subprocess.run(
            ["git", "--no-pager", *args],
            cwd=root,
            env=env,
            text=not binary,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=configured_timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def run_git(root: Path, args: Sequence[str], default: str = "", timeout: int = 15) -> str:
    proc = _run_git_process(root, args, timeout=timeout)
    if proc is None or proc.returncode != 0:
        return default
    assert isinstance(proc.stdout, str)
    return proc.stdout.rstrip("\r\n")


def is_git_repo(root: Path) -> bool:
    return run_git(root, ["rev-parse", "--is-inside-work-tree"], "false") == "true"


def current_branch(root: Path) -> str:
    return run_git(root, ["branch", "--show-current"], "no-git") or "detached"


def head_commit(root: Path) -> str:
    return run_git(root, ["rev-parse", "--verify", "HEAD"], "no-git")


def git_common_dir(root: Path) -> str:
    return run_git(root, ["rev-parse", "--git-common-dir"], "")


def repository_root(root: Path) -> str:
    return run_git(root, ["rev-parse", "--show-toplevel"], str(root.resolve()))


def _absolute_common_dir(root: Path, common: str) -> str:
    if not common:
        return ""
    value = Path(common)
    return str(value.resolve() if value.is_absolute() else (root / value).resolve())


def repository_id(root: Path) -> str:
    """Identity shared by linked worktrees of one local repository.

    A remote URL is preferred when present; otherwise the canonical Git common
    directory is used. The worktree path is deliberately excluded so a linked
    worktree does not become a different repository identity.
    """
    common = _absolute_common_dir(root, git_common_dir(root))
    # Local runtime identity must be cheap and deterministic. Git remote lookup
    # is integration metadata and may invoke slow/locked global config; the
    # shared common directory is sufficient to identify linked worktrees.
    raw = common or str(root.resolve())
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def workspace_id(root: Path) -> str:
    common = _absolute_common_dir(root, git_common_dir(root))
    raw = f"{root.resolve()}\0{common}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _decode(value: bytes) -> str:
    return value.decode("utf-8", errors="surrogateescape")


def _parse_porcelain_v2(data: bytes) -> tuple[str, str, List[str]]:
    branch = "no-git"
    head = "no-git"
    paths: List[str] = []
    records = data.split(b"\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if record.startswith(b"# branch.head "):
            value = _decode(record[len(b"# branch.head ") :])
            branch = "detached" if value == "(detached)" else value
            continue
        if record.startswith(b"# branch.oid "):
            value = _decode(record[len(b"# branch.oid ") :])
            head = "no-git" if value == "(initial)" else value
            continue
        kind = record[:1]
        try:
            if kind == b"1":
                path = record.split(b" ", 8)[8]
                paths.append(_decode(path))
            elif kind == b"2":
                # Porcelain v2 rename/copy: current path is field 10 and the
                # original path is the following NUL-delimited record.
                path = record.split(b" ", 9)[9]
                paths.append(_decode(path))
                if index < len(records) and records[index]:
                    paths.append(_decode(records[index]))
                    index += 1
            elif kind == b"u":
                path = record.split(b" ", 10)[10]
                paths.append(_decode(path))
            elif kind == b"?":
                paths.append(_decode(record[2:]))
        except IndexError:
            # Fail conservatively: malformed status output should not crash the
            # controller, but it also should not invent a path.
            continue
    return branch, head, list(dict.fromkeys(paths))


def _status_snapshot(root: Path) -> tuple[str, str, List[str]]:
    proc = _run_git_process(
        root,
        ["status", "--porcelain=v2", "--branch", "--untracked-files=all", "-z"],
        binary=True,
    )
    if proc is None or proc.returncode != 0:
        return "no-git", "no-git", []
    assert isinstance(proc.stdout, bytes)
    return _parse_porcelain_v2(proc.stdout)


def status_paths(root: Path) -> List[str]:
    return sorted(_status_snapshot(root)[2])


def is_non_implementation_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    return normalized in NON_IMPLEMENTATION_EXACT or any(normalized.startswith(prefix) for prefix in NON_IMPLEMENTATION_PREFIXES)


def _diff_paths(root: Path, base_commit: str, head: str) -> List[str]:
    if not base_commit or base_commit in {"no-git", head} or head == "no-git":
        return []
    out = run_git(root, ["diff", "--name-only", "--diff-filter=ACDMRTUXB", f"{base_commit}..{head}"], "")
    return [line for line in out.splitlines() if line]


def _diff_hash(root: Path, paths: Iterable[str], base_commit: str = "") -> str:
    h = hashlib.sha256()
    h.update((base_commit or "").encode("utf-8"))
    for rel in sorted(paths):
        h.update(rel.encode("utf-8", errors="surrogateescape"))
        path = root / rel
        if path.is_file():
            h.update(path.read_bytes())
        else:
            h.update(b"<missing>")
    return h.hexdigest()


@dataclass(frozen=True)
class RepoSnapshot:
    repository_id: str
    workspace_id: str
    worktree: str
    branch: str
    base_commit: str
    head_commit: str
    changed_files: tuple[str, ...]
    implementation_changed_files: tuple[str, ...]
    diff_hash: str
    implementation_diff_hash: str

    @classmethod
    def capture(cls, root: Path, base_commit: str = "") -> "RepoSnapshot":
        root = root.resolve()
        meta = run_git(root, ["rev-parse", "--show-toplevel", "--git-common-dir"], "")
        lines = meta.splitlines()
        if len(lines) >= 2:
            common = _absolute_common_dir(root, lines[1])
            repository_raw = common
        else:
            common = ""
            repository_raw = str(root)
        branch, head, dirty_paths = _status_snapshot(root)
        all_paths = sorted(set(dirty_paths).union(_diff_paths(root, base_commit, head)))
        implementation_paths = [path for path in all_paths if not is_non_implementation_path(path)]
        repo_id = hashlib.sha256(repository_raw.encode("utf-8")).hexdigest()[:20]
        work_id = hashlib.sha256(f"{root}\0{common}".encode("utf-8")).hexdigest()[:20]
        return cls(
            repository_id=repo_id,
            workspace_id=work_id,
            worktree=str(root),
            branch=branch,
            base_commit=base_commit,
            head_commit=head,
            changed_files=tuple(all_paths),
            implementation_changed_files=tuple(implementation_paths),
            diff_hash=_diff_hash(root, all_paths, base_commit),
            implementation_diff_hash=_diff_hash(root, implementation_paths, base_commit),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "repository_id": self.repository_id,
            "workspace_id": self.workspace_id,
            "worktree": self.worktree,
            "branch": self.branch,
            "base_commit": self.base_commit,
            "head_commit": self.head_commit,
            "changed_files": list(self.changed_files),
            "implementation_changed_files": list(self.implementation_changed_files),
            "diff_hash": self.diff_hash,
            "implementation_diff_hash": self.implementation_diff_hash,
        }


def work_unit_changed_files(root: Path, base_commit: str = "") -> List[str]:
    return list(RepoSnapshot.capture(root, base_commit).changed_files)


def implementation_changed_files(root: Path, base_commit: str = "") -> List[str]:
    return list(RepoSnapshot.capture(root, base_commit).implementation_changed_files)


def implementation_diff_hash(root: Path, base_commit: str = "") -> str:
    return RepoSnapshot.capture(root, base_commit).implementation_diff_hash


def full_diff_hash(root: Path, base_commit: str = "") -> str:
    return RepoSnapshot.capture(root, base_commit).diff_hash


def git_identity(root: Path, base_commit: str = "") -> dict[str, object]:
    return RepoSnapshot.capture(root, base_commit).as_dict()
