from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from json_parts import json_part_filename, parse_part_ref, validate_json_part


FREE_CONTENT_PART_TYPES = frozenset(
    {
        "character_body",
        "outfit_prop",
        "expression_face",
        "camera_composition",
        "background_scene",
    }
)
JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*([\s\S]*?)\s*```$", re.IGNORECASE)
ACCEPTED_RELATIVE_PATH = Path("learning/local-ai/store/json-parts")
STAGING_RELATIVE_PATH = Path("learning/local-ai/store/staging")
RECEIPTS_RELATIVE_PATH = Path("learning/local-ai/store/receipts")


@dataclass(frozen=True)
class StageResult:
    ref: str
    part_type: str
    path: Path
    sha256: str
    payload_sha256: str


@dataclass(frozen=True)
class AcceptResult:
    ref: str
    part_type: str
    staged_path: Path
    accepted_path: Path
    staged_sha256: str
    accepted_sha256: str
    payload_sha256: str
    receipt_path: Path
    accepted_document: dict[str, Any]


def _canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _semantic_sha256(value: Any) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8-sig").strip()
    except UnicodeDecodeError as exc:
        raise ValueError(f"invalid UTF-8 JSON file: {path}") from exc
    if not text:
        raise ValueError(f"JSON file is empty: {path}")
    fence = JSON_FENCE_RE.fullmatch(text)
    if fence is not None:
        text = fence.group(1).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _validate_candidate(
    document: dict[str, Any],
    *,
    expected_status: str,
    enforce_free_role: bool,
) -> dict[str, Any]:
    validated = validate_json_part(document)
    status = document.get("status")
    if status != expected_status:
        raise ValueError(f"JSON Part status must be {expected_status!r}; got {status!r}")
    part_type = validated["part_type"]
    if enforce_free_role and part_type not in FREE_CONTENT_PART_TYPES:
        allowed = ", ".join(sorted(FREE_CONTENT_PART_TYPES))
        raise ValueError(
            f"FREE content JSON Part part_type must be one of: {allowed}; got {part_type!r}"
        )
    return validated


def resolve_accepted_store(resource_root: Path) -> Path:
    return resource_root.resolve() / ACCEPTED_RELATIVE_PATH


def resolve_staging_store(resource_root: Path) -> Path:
    return resource_root.resolve() / STAGING_RELATIVE_PATH


def resolve_receipt_store(resource_root: Path) -> Path:
    return resource_root.resolve() / RECEIPTS_RELATIVE_PATH


def stage_json_part(
    resource_root: Path,
    document: dict[str, Any],
    *,
    enforce_free_role: bool = True,
) -> StageResult:
    validated = _validate_candidate(
        document,
        expected_status="staging",
        enforce_free_role=enforce_free_role,
    )
    ref = f"part:{validated['part_id']}@{validated['version']}"
    filename = json_part_filename(validated["part_id"], validated["version"])

    accepted_store = resolve_accepted_store(resource_root)
    accepted_path = accepted_store / filename
    if accepted_path.exists():
        raise FileExistsError(
            f"accepted JSON Part already exists; create a new version instead: {ref}"
        )

    staging_store = resolve_staging_store(resource_root)
    staging_store.mkdir(parents=True, exist_ok=True)
    target = staging_store / filename
    raw = _canonical_bytes(document)
    digest = hashlib.sha256(raw).hexdigest()

    if target.exists():
        existing_sha = _file_sha256(target)
        if existing_sha != digest:
            raise FileExistsError(
                f"different staging JSON Part already exists for {ref}; remove it or increment the version"
            )
        return StageResult(
            ref=ref,
            part_type=validated["part_type"],
            path=target,
            sha256=digest,
            payload_sha256=_semantic_sha256(document["payload"]),
        )

    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=staging_store,
        prefix=f".{filename}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        tmp_path = Path(handle.name)
        handle.write(raw)
    tmp_path.replace(target)

    return StageResult(
        ref=ref,
        part_type=validated["part_type"],
        path=target,
        sha256=digest,
        payload_sha256=_semantic_sha256(document["payload"]),
    )


def inspect_staged_json_part(
    resource_root: Path,
    ref: str,
    *,
    enforce_free_role: bool = True,
) -> StageResult:
    part_id, version = parse_part_ref(ref)
    path = resolve_staging_store(resource_root) / json_part_filename(part_id, version)
    if not path.is_file():
        raise FileNotFoundError(f"staging JSON Part not found: {ref} ({path})")
    document = _load_json_object(path)
    validated = _validate_candidate(
        document,
        expected_status="staging",
        enforce_free_role=enforce_free_role,
    )
    if validated["part_id"] != part_id or validated["version"] != version:
        raise ValueError(f"staging JSON Part filename/ref identity mismatch: {ref}")
    return StageResult(
        ref=ref,
        part_type=validated["part_type"],
        path=path,
        sha256=_file_sha256(path),
        payload_sha256=_semantic_sha256(document["payload"]),
    )


def accept_staged_json_part(
    resource_root: Path,
    ref: str,
    *,
    expected_sha256: str | None = None,
    enforce_free_role: bool = True,
    remove_staging: bool = True,
) -> AcceptResult:
    staged = inspect_staged_json_part(
        resource_root,
        ref,
        enforce_free_role=enforce_free_role,
    )
    if expected_sha256 is not None and staged.sha256.casefold() != expected_sha256.strip().casefold():
        raise ValueError(
            f"staging SHA256 changed before acceptance: expected={expected_sha256} actual={staged.sha256}"
        )

    document = _load_json_object(staged.path)
    part_id, version = parse_part_ref(ref)
    accepted_store = resolve_accepted_store(resource_root)
    accepted_store.mkdir(parents=True, exist_ok=True)
    accepted_path = accepted_store / json_part_filename(part_id, version)
    if accepted_path.exists():
        raise FileExistsError(
            f"accepted JSON Part already exists; create a new version instead: {ref}"
        )

    before_without_status = copy.deepcopy(document)
    before_without_status.pop("status", None)
    payload_sha = _semantic_sha256(document["payload"])

    accepted_document = copy.deepcopy(document)
    accepted_document["status"] = "accepted"
    validated = _validate_candidate(
        accepted_document,
        expected_status="accepted",
        enforce_free_role=enforce_free_role,
    )
    if validated["part_id"] != part_id or validated["version"] != version:
        raise ValueError(f"accepted JSON Part identity mismatch: {ref}")

    after_without_status = copy.deepcopy(accepted_document)
    after_without_status.pop("status", None)
    if _semantic_sha256(before_without_status) != _semantic_sha256(after_without_status):
        raise RuntimeError("JSON Part changed during acceptance beyond the status field")
    if payload_sha != _semantic_sha256(accepted_document["payload"]):
        raise RuntimeError("JSON Part payload changed during acceptance")

    accepted_raw = _canonical_bytes(accepted_document)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=accepted_store,
        prefix=f".{accepted_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        tmp_path = Path(handle.name)
        handle.write(accepted_raw)
    tmp_path.replace(accepted_path)
    accepted_sha = hashlib.sha256(accepted_raw).hexdigest()

    receipts = resolve_receipt_store(resource_root)
    receipts.mkdir(parents=True, exist_ok=True)
    receipt_path = receipts / f"{part_id}.v{version}.acceptance.json"
    receipt = {
        "schema_version": 1,
        "ref": ref,
        "accepted_at_utc": datetime.now(timezone.utc).isoformat(),
        "part_type": validated["part_type"],
        "staged_sha256": staged.sha256,
        "accepted_sha256": accepted_sha,
        "payload_sha256": payload_sha,
        "semantic_change": "status: staging -> accepted only",
    }
    receipt_path.write_bytes(_canonical_bytes(receipt))

    if remove_staging:
        staged.path.unlink()

    return AcceptResult(
        ref=ref,
        part_type=validated["part_type"],
        staged_path=staged.path,
        accepted_path=accepted_path,
        staged_sha256=staged.sha256,
        accepted_sha256=accepted_sha,
        payload_sha256=payload_sha,
        receipt_path=receipt_path,
        accepted_document=accepted_document,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Mechanically stage/validate/accept local-RAG JSON Parts without semantic rewriting."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    stage = sub.add_parser("stage-file", help="Validate a canonical staging JSON file and copy it into staging.")
    stage.add_argument("path", type=Path)
    stage.add_argument("--allow-non-free-role", action="store_true")

    validate = sub.add_parser("validate", help="Validate an already staged Part and print only metadata/hashes.")
    validate.add_argument("--ref", required=True)
    validate.add_argument("--allow-non-free-role", action="store_true")

    accept = sub.add_parser("accept", help="Promote one staged Part to accepted using an optional SHA256 gate.")
    accept.add_argument("--ref", required=True)
    accept.add_argument("--expected-sha256")
    accept.add_argument("--allow-non-free-role", action="store_true")

    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    root = Path(__file__).resolve().parent.parent
    enforce_free = not args.allow_non_free_role

    if args.command == "stage-file":
        source = args.path.expanduser().resolve()
        document = _load_json_object(source)
        result = stage_json_part(root, document, enforce_free_role=enforce_free)
        print(f"[JSON-SYNC:STAGE:OK] ref={result.ref} role={result.part_type}")
        print(f"[JSON-SYNC:STAGE:SHA256] {result.sha256}")
        print(f"[JSON-SYNC:PAYLOAD:SHA256] {result.payload_sha256}")
        print(f"[JSON-SYNC:STAGE:PATH] {result.path}")
        return 0

    if args.command == "validate":
        result = inspect_staged_json_part(root, args.ref, enforce_free_role=enforce_free)
        print(f"[JSON-SYNC:VALIDATE:OK] ref={result.ref} role={result.part_type}")
        print(f"[JSON-SYNC:STAGE:SHA256] {result.sha256}")
        print(f"[JSON-SYNC:PAYLOAD:SHA256] {result.payload_sha256}")
        return 0

    result = accept_staged_json_part(
        root,
        args.ref,
        expected_sha256=args.expected_sha256,
        enforce_free_role=enforce_free,
    )
    print(f"[JSON-SYNC:ACCEPT:OK] ref={result.ref} role={result.part_type}")
    print(f"[JSON-SYNC:STAGED:SHA256] {result.staged_sha256}")
    print(f"[JSON-SYNC:ACCEPTED:SHA256] {result.accepted_sha256}")
    print(f"[JSON-SYNC:PAYLOAD:SHA256] {result.payload_sha256}")
    print("[JSON-SYNC:SEMANTIC-PRESERVATION:OK] status-only change")
    print(f"[JSON-SYNC:ACCEPTED:PATH] {result.accepted_path}")
    print(f"[JSON-SYNC:RECEIPT:PATH] {result.receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
