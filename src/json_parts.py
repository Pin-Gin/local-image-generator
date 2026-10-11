from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PART_REF_RE = re.compile(r"^part:([a-z0-9][a-z0-9._-]{1,127})@([1-9][0-9]*)$")
STORE_RELATIVE_PATH = Path("learning/local-ai/store/json-parts")


@dataclass(frozen=True)
class ResolvedJsonPart:
    ref: str
    part_id: str
    version: int
    part_type: str
    name: str
    path: Path
    sha256: str
    positive: str
    negative: str

    def to_request_payload(self) -> dict[str, Any]:
        return {
            "ref": self.ref,
            "part_id": self.part_id,
            "version": self.version,
            "part_type": self.part_type,
            "name": self.name,
            "path": str(self.path),
            "sha256": self.sha256,
            "generation": {
                "positive": self.positive,
                "negative": self.negative,
            },
        }


def _candidate_project_roots(resource_root: Path) -> list[Path]:
    candidates: list[Path] = []
    cwd = Path.cwd().resolve()
    candidates.extend([cwd, *cwd.parents])

    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        candidates.extend([executable.parent, *executable.parents])

    resolved_resource = resource_root.resolve()
    candidates.extend([resolved_resource, *resolved_resource.parents])

    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique.append(candidate)
    return unique


def resolve_json_part_store(resource_root: Path) -> Path:
    for root in _candidate_project_roots(resource_root):
        candidate = root / STORE_RELATIVE_PATH
        if candidate.is_dir():
            return candidate
    return resource_root.resolve() / STORE_RELATIVE_PATH


def parse_part_ref(value: str) -> tuple[str, int]:
    if not isinstance(value, str):
        raise ValueError("JSON part reference must be a string")
    match = PART_REF_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(
            "JSON part reference must use part:<part_id>@<version>, for example part:pose.hair-touch@1"
        )
    return match.group(1), int(match.group(2))


def validate_json_part(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema_version") != 1:
        raise ValueError("JSON part schema_version must be 1")
    if payload.get("document_type") != "local-rag/json-part":
        raise ValueError("JSON part document_type must be local-rag/json-part")

    part_id = payload.get("part_id")
    version = payload.get("version")
    part_type = payload.get("part_type")
    name = payload.get("name")
    status = payload.get("status")
    aliases = payload.get("aliases")
    tags = payload.get("tags")
    part_payload = payload.get("payload")
    provenance = payload.get("provenance")

    if not isinstance(part_id, str) or PART_REF_RE.fullmatch(f"part:{part_id}@1") is None:
        raise ValueError("JSON part part_id is invalid")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError("JSON part version must be an integer >= 1")
    if not isinstance(part_type, str) or not part_type.strip():
        raise ValueError("JSON part part_type must be a non-empty string")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("JSON part name must be a non-empty string")
    if status not in {"staging", "accepted", "retired"}:
        raise ValueError("JSON part status must be staging, accepted, or retired")
    if not isinstance(aliases, list) or any(not isinstance(item, str) for item in aliases):
        raise ValueError("JSON part aliases must be an array of strings")
    if not isinstance(tags, list) or any(not isinstance(item, str) for item in tags):
        raise ValueError("JSON part tags must be an array of strings")
    if not isinstance(part_payload, dict):
        raise ValueError("JSON part payload must be an object")
    if not isinstance(provenance, dict):
        raise ValueError("JSON part provenance must be an object")

    source_type = provenance.get("source_type")
    source_ref = provenance.get("source_ref")
    if not isinstance(source_type, str) or not source_type.strip():
        raise ValueError("JSON part provenance.source_type must be a non-empty string")
    if not isinstance(source_ref, str):
        raise ValueError("JSON part provenance.source_ref must be a string")

    generation = part_payload.get("generation", {})
    if generation is None:
        generation = {}
    if not isinstance(generation, dict):
        raise ValueError("JSON part payload.generation must be an object")
    positive = generation.get("positive", "")
    negative = generation.get("negative", "")
    if not isinstance(positive, str) or not isinstance(negative, str):
        raise ValueError("JSON part generation positive/negative values must be strings")

    normalized = dict(payload)
    normalized["part_id"] = part_id.strip()
    normalized["part_type"] = part_type.strip()
    normalized["name"] = name.strip()
    normalized["aliases"] = [item.strip() for item in aliases if item.strip()]
    normalized["tags"] = [item.strip() for item in tags if item.strip()]
    normalized["payload"] = dict(part_payload)
    normalized["payload"]["generation"] = {
        "positive": positive.strip(),
        "negative": negative.strip(),
    }
    return normalized


def json_part_filename(part_id: str, version: int) -> str:
    parse_part_ref(f"part:{part_id}@{version}")
    return f"{part_id}.v{version}.json"


def load_json_part(resource_root: Path, ref: str, *, accepted_only: bool = True) -> ResolvedJsonPart:
    part_id, version = parse_part_ref(ref)
    store = resolve_json_part_store(resource_root)
    path = store / json_part_filename(part_id, version)
    if not path.is_file():
        raise FileNotFoundError(f"JSON part not found: {ref} ({path})")

    raw = path.read_bytes()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid JSON part file: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON part root must be an object: {path}")
    payload = validate_json_part(payload)

    if payload["part_id"] != part_id or payload["version"] != version:
        raise ValueError(f"JSON part filename/ref does not match document identity: {ref}")
    if accepted_only and payload["status"] != "accepted":
        raise ValueError(f"JSON part is not accepted: {ref} status={payload['status']}")

    generation = payload["payload"].get("generation", {})
    return ResolvedJsonPart(
        ref=ref,
        part_id=part_id,
        version=version,
        part_type=payload["part_type"],
        name=payload["name"],
        path=path,
        sha256=hashlib.sha256(raw).hexdigest(),
        positive=generation.get("positive", ""),
        negative=generation.get("negative", ""),
    )


def resolve_generation_parts(resource_root: Path, refs: Any) -> list[ResolvedJsonPart]:
    if refs is None:
        return []
    if not isinstance(refs, list):
        raise ValueError("generation JSON parts must be an array")

    resolved: list[ResolvedJsonPart] = []
    seen: set[str] = set()
    for index, value in enumerate(refs):
        if not isinstance(value, str):
            raise ValueError(f"generation JSON parts[{index}] must be a string")
        ref = value.strip()
        if ref in seen:
            continue
        seen.add(ref)
        resolved.append(load_json_part(resource_root, ref))
    return resolved
