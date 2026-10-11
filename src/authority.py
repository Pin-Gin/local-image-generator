from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AuthorityFile:
    path: str
    git_blob_sha: str
    sha256: str
    size: int
    local_path: Path


@dataclass(frozen=True)
class AuthorityBundle:
    repository: str
    branch: str
    commit_sha: str
    files: dict[str, AuthorityFile]
    expected_master_sha256: str


def _request_json(url: str, timeout_seconds: float = 15.0) -> Any:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "local-RAG"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"GitHub HTTP error: {exc.code} {exc.reason} ({url})") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub connection failed: {exc.reason} ({url})") from exc

    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"GitHub returned invalid JSON ({url})") from exc


def _download_bytes(url: str, timeout_seconds: float = 30.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "local-RAG"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Authority download HTTP error: {exc.code} {exc.reason} ({url})") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Authority download failed: {exc.reason} ({url})") from exc


def _repo_parts(repository: str) -> tuple[str, str]:
    parts = repository.split("/", 1)
    if len(parts) != 2 or not all(parts):
        raise ValueError("authority.repository must be owner/name")
    return parts[0], parts[1]


def _resolve_commit(repository: str, branch: str) -> str:
    owner, repo = _repo_parts(repository)
    url = f"https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/commits/{urllib.parse.quote(branch)}"
    payload = _request_json(url)
    sha = payload.get("sha") if isinstance(payload, dict) else None
    if not isinstance(sha, str) or len(sha) != 40:
        raise RuntimeError("Could not resolve MEMORIELA source commit SHA")
    return sha


def _fetch_file_metadata(repository: str, path: str, commit_sha: str) -> dict[str, Any]:
    owner, repo = _repo_parts(repository)
    quoted_path = "/".join(urllib.parse.quote(part) for part in path.split("/"))
    url = f"https://api.github.com/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/contents/{quoted_path}?ref={commit_sha}"
    payload = _request_json(url)
    if not isinstance(payload, dict) or payload.get("type") != "file":
        raise RuntimeError(f"Authority path is not a file: {path}")
    return payload


def _raw_url(repository: str, commit_sha: str, path: str) -> str:
    owner, repo = _repo_parts(repository)
    quoted_path = "/".join(urllib.parse.quote(part) for part in path.split("/"))
    return f"https://raw.githubusercontent.com/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}/{commit_sha}/{quoted_path}"


def _cache_target(cache_root: Path, repository: str, commit_sha: str, source_path: str) -> Path:
    owner, repo = _repo_parts(repository)
    return cache_root / "authority" / owner / repo / commit_sha / Path(source_path)


def _store_authority_file(
    repository: str,
    source_path: str,
    commit_sha: str,
    cache_root: Path,
) -> AuthorityFile:
    metadata = _fetch_file_metadata(repository, source_path, commit_sha)
    git_blob_sha = metadata.get("sha")
    if not isinstance(git_blob_sha, str) or len(git_blob_sha) != 40:
        raise RuntimeError(f"Missing Git blob SHA for authority file: {source_path}")

    raw = _download_bytes(_raw_url(repository, commit_sha, source_path))
    local_path = _cache_target(cache_root, repository, commit_sha, source_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(raw)

    return AuthorityFile(
        path=source_path,
        git_blob_sha=git_blob_sha,
        sha256=hashlib.sha256(raw).hexdigest(),
        size=len(raw),
        local_path=local_path,
    )


def _read_text(file: AuthorityFile) -> str:
    try:
        return file.local_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError(f"Expected UTF-8 authority text: {file.path}") from exc


def resolve_authority_bundle(profile: dict[str, Any], cache_root: Path) -> AuthorityBundle:
    authority = profile.get("authority")
    if not isinstance(authority, dict):
        raise ValueError("profile.authority must be an object")

    repository = authority.get("repository")
    branch = authority.get("branch")
    allowed_paths = authority.get("allowed_paths")
    master_path = authority.get("master_image_path")
    status_path = authority.get("master_status_path")
    lifecycle_path = authority.get("lifecycle_path")

    if not isinstance(repository, str) or not repository:
        raise ValueError("profile.authority.repository must be a non-empty string")
    if not isinstance(branch, str) or not branch:
        raise ValueError("profile.authority.branch must be a non-empty string")
    if not isinstance(allowed_paths, list) or not allowed_paths or not all(isinstance(item, str) for item in allowed_paths):
        raise ValueError("profile.authority.allowed_paths must be a non-empty string array")
    if not all(isinstance(value, str) and value in allowed_paths for value in (master_path, status_path, lifecycle_path)):
        raise ValueError("master/status/lifecycle paths must be explicitly listed in allowed_paths")

    commit_sha = _resolve_commit(repository, branch)
    files: dict[str, AuthorityFile] = {}
    for source_path in allowed_paths:
        files[source_path] = _store_authority_file(repository, source_path, commit_sha, cache_root)

    status_text = _read_text(files[status_path])
    lifecycle_text = _read_text(files[lifecycle_path])

    for marker in authority.get("required_status_markers", []):
        if not isinstance(marker, str) or marker not in status_text:
            raise RuntimeError(f"Required working-Master status marker missing: {marker}")

    for marker in authority.get("required_lifecycle_markers", []):
        if not isinstance(marker, str) or marker not in lifecycle_text:
            raise RuntimeError(f"Required lifecycle marker missing: {marker}")

    match = re.search(r"asset_sha256\s*=\s*([0-9a-fA-F]{64})", status_text)
    if not match:
        raise RuntimeError("YURA_VISUAL_MASTER_STATUS.md does not declare asset_sha256")
    expected_master_sha256 = match.group(1).lower()

    actual_master_sha256 = files[master_path].sha256.lower()
    if actual_master_sha256 != expected_master_sha256:
        raise RuntimeError(
            "YURA working Master SHA-256 mismatch: "
            f"expected={expected_master_sha256} actual={actual_master_sha256}"
        )

    return AuthorityBundle(
        repository=repository,
        branch=branch,
        commit_sha=commit_sha,
        files=files,
        expected_master_sha256=expected_master_sha256,
    )
