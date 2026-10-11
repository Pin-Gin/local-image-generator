from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


class LocalGitTools:
    def __init__(self, resource_root: Path, config_path: Path) -> None:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        git_cfg = payload.get("git") if isinstance(payload, dict) else None
        if not isinstance(git_cfg, dict):
            raise ValueError("local tools git config is missing")
        if git_cfg.get("read_only") is not True:
            raise ValueError("local Git tools must remain read-only")
        repositories = git_cfg.get("repositories")
        if not isinstance(repositories, list):
            raise ValueError("local Git repositories must be an array")

        self.resource_root = resource_root
        self.repo_defs = repositories
        self.allowed_actions = set(git_cfg.get("allowed_actions") or [])

    def _candidate_project_roots(self) -> list[Path]:
        candidates: list[Path] = []
        cwd = Path.cwd().resolve()
        candidates.extend([cwd, *cwd.parents])
        if getattr(sys, "frozen", False):
            executable = Path(sys.executable).resolve()
            candidates.extend([executable.parent, *executable.parents])
        resolved_resource = self.resource_root.resolve()
        candidates.extend([resolved_resource, *resolved_resource.parents])

        unique: list[Path] = []
        seen: set[Path] = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            unique.append(candidate)
        return unique

    def _project_root(self) -> Path:
        for candidate in self._candidate_project_roots():
            if (candidate / ".git").exists() and (candidate / "src").is_dir():
                return candidate
        return Path.cwd().resolve()

    def _resolve_repo(self, repo_id: str) -> Path:
        for item in self.repo_defs:
            if not isinstance(item, dict) or item.get("repo_id") != repo_id:
                continue

            path_value = item.get("path")
            path_env = item.get("path_env")
            optional = bool(item.get("optional"))

            if isinstance(path_env, str) and path_env:
                env_value = os.getenv(path_env, "").strip()
                if not env_value:
                    if optional:
                        raise FileNotFoundError(f"optional Git repository is not configured: {repo_id}")
                    raise FileNotFoundError(f"Git repository environment variable is empty: {path_env}")
                path = Path(env_value).expanduser().resolve()
            elif isinstance(path_value, str) and path_value:
                path = (self._project_root() / path_value).resolve()
            else:
                raise ValueError(f"Git repository config is invalid: {repo_id}")

            if not path.is_dir() or not (path / ".git").exists():
                raise FileNotFoundError(f"Git repository is unavailable: {repo_id} -> {path}")
            return path

        raise ValueError(f"unknown Git repository id: {repo_id}")

    def _run(self, repo_id: str, args: list[str], *, timeout: int = 30) -> str:
        repo = self._resolve_repo(repo_id)
        command = ["git", "-C", str(repo), *args]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("git executable was not found. Run setup_local_tools.ps1.") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Git command timed out") from exc

        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(f"Git command failed ({completed.returncode}): {detail}")
        return completed.stdout

    def status(self, repo_id: str) -> dict[str, Any]:
        output = self._run(repo_id, ["status", "--short", "--branch"])
        return {"repo_id": repo_id, "status": output.rstrip()}

    def log(self, repo_id: str, *, max_count: int = 10) -> dict[str, Any]:
        count = max(1, min(int(max_count), 50))
        output = self._run(
            repo_id,
            ["log", f"--max-count={count}", "--date=iso-strict", "--pretty=format:%H%x09%ad%x09%s"],
        )
        rows: list[dict[str, str]] = []
        for line in output.splitlines():
            parts = line.split("\t", 2)
            if len(parts) == 3:
                rows.append({"sha": parts[0], "date": parts[1], "subject": parts[2]})
        return {"repo_id": repo_id, "commits": rows}

    def diff(self, repo_id: str, *, ref: str = "HEAD", path: str | None = None) -> dict[str, Any]:
        args = ["diff", "--no-ext-diff", ref]
        if path:
            args.extend(["--", path])
        output = self._run(repo_id, args, timeout=45)
        return {"repo_id": repo_id, "ref": ref, "path": path, "diff": output}

    def list_files(self, repo_id: str, *, path_prefix: str = "") -> dict[str, Any]:
        args = ["ls-files"]
        if path_prefix:
            args.extend(["--", path_prefix])
        output = self._run(repo_id, args)
        files = [line for line in output.splitlines() if line.strip()]
        return {"repo_id": repo_id, "files": files[:2000], "truncated": len(files) > 2000}

    def read_file(self, repo_id: str, path: str, *, ref: str = "HEAD") -> dict[str, Any]:
        clean = path.replace("\\", "/").strip("/")
        if not clean or clean.startswith(".git/") or "/../" in f"/{clean}/" or clean == ".git":
            raise ValueError("invalid Git file path")
        output = self._run(repo_id, ["show", f"{ref}:{clean}"], timeout=30)
        if len(output) > 250_000:
            raise ValueError("Git file exceeds local AI read limit (250 KB)")
        return {"repo_id": repo_id, "ref": ref, "path": clean, "content": output}

    def search(self, repo_id: str, query: str, *, max_results: int = 50) -> dict[str, Any]:
        text = query.strip()
        if not text:
            raise ValueError("Git search query must not be empty")
        limit = max(1, min(int(max_results), 200))
        try:
            output = self._run(repo_id, ["grep", "-n", "-I", "-e", text, "--", "."], timeout=45)
        except RuntimeError as exc:
            # `git grep` returns 1 when there are simply no matches.
            message = str(exc)
            if "(1):" in message and not message.split(":", 1)[-1].strip():
                output = ""
            else:
                raise
        rows: list[dict[str, Any]] = []
        for line in output.splitlines()[:limit]:
            parts = line.split(":", 2)
            if len(parts) == 3:
                path, line_number, content = parts
                try:
                    number = int(line_number)
                except ValueError:
                    number = None
                rows.append({"path": path, "line": number, "content": content})
        return {"repo_id": repo_id, "query": text, "results": rows}
