from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


QA_STATUSES = ("unreviewed", "accepted", "rejected")


@dataclass(frozen=True)
class GenerationRecord:
    generation_id: str
    created_at_utc: str
    manifest_path: str
    manifest_sha256: str
    output_path: str
    output_sha256: str
    character: str | None
    profile_id: str | None
    authority_commit: str | None
    compiled_workflow_sha256: str | None
    seed: int | None
    qa_status: str


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def connect_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(path: Path) -> None:
    with connect_database(path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS generations (
                generation_id TEXT PRIMARY KEY,
                created_at_utc TEXT NOT NULL,
                manifest_path TEXT NOT NULL,
                manifest_sha256 TEXT NOT NULL,
                output_path TEXT NOT NULL,
                output_sha256 TEXT NOT NULL,
                character TEXT,
                profile_id TEXT,
                authority_commit TEXT,
                compiled_workflow_sha256 TEXT,
                seed INTEGER,
                qa_status TEXT NOT NULL DEFAULT 'unreviewed'
                    CHECK (qa_status IN ('unreviewed', 'accepted', 'rejected')),
                inserted_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at_utc TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_generations_created_at
                ON generations(created_at_utc DESC);

            CREATE INDEX IF NOT EXISTS idx_generations_qa_status
                ON generations(qa_status);
            """
        )


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read manifest JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("manifest root must be an object")
    return payload


def _require_string(payload: dict[str, Any], key: str, context: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context}.{key} must be a non-empty string")
    return value


def _generation_id_from_manifest_path(path: Path) -> str:
    generation_id = path.parent.name
    if not generation_id:
        raise ValueError("Could not derive generation_id from manifest parent directory")
    return generation_id


def import_manifest(database_path: Path, manifest_path: Path) -> GenerationRecord:
    manifest_path = manifest_path.resolve()
    payload = load_manifest(manifest_path)

    created_at_utc = _require_string(payload, "created_at_utc", "manifest")
    profile = payload.get("profile")
    authority = payload.get("authority")
    workflow = payload.get("workflow")
    generation = payload.get("generation")
    output = payload.get("output")
    qa = payload.get("qa")

    if not isinstance(profile, dict):
        raise ValueError("manifest.profile must be an object")
    if not isinstance(authority, dict):
        raise ValueError("manifest.authority must be an object")
    if not isinstance(workflow, dict):
        raise ValueError("manifest.workflow must be an object")
    if not isinstance(generation, dict):
        raise ValueError("manifest.generation must be an object")
    if not isinstance(output, dict):
        raise ValueError("manifest.output must be an object")
    if not isinstance(qa, dict):
        raise ValueError("manifest.qa must be an object")

    output_path = _require_string(output, "path", "manifest.output")
    output_sha256 = _require_string(output, "sha256", "manifest.output")
    if not Path(output_path).is_file():
        raise ValueError(f"manifest output file does not exist: {output_path}")
    actual_output_sha256 = _sha256_file(Path(output_path))
    if actual_output_sha256 != output_sha256:
        raise ValueError(
            f"manifest output SHA-256 mismatch: expected={output_sha256} actual={actual_output_sha256}"
        )

    qa_status = qa.get("status", "unreviewed")
    if qa_status not in QA_STATUSES:
        raise ValueError(f"Unsupported qa.status: {qa_status}")

    generation_id = _generation_id_from_manifest_path(manifest_path)
    manifest_sha256 = _sha256_file(manifest_path)
    character = profile.get("character") if isinstance(profile.get("character"), str) else None
    profile_id = profile.get("profile_id") if isinstance(profile.get("profile_id"), str) else None
    authority_commit = authority.get("commit_sha") if isinstance(authority.get("commit_sha"), str) else None
    compiled_sha = workflow.get("compiled_sha256") if isinstance(workflow.get("compiled_sha256"), str) else None
    seed = generation.get("seed") if isinstance(generation.get("seed"), int) else None

    initialize_database(database_path)
    with connect_database(database_path) as connection:
        connection.execute(
            """
            INSERT INTO generations (
                generation_id, created_at_utc, manifest_path, manifest_sha256,
                output_path, output_sha256, character, profile_id,
                authority_commit, compiled_workflow_sha256, seed, qa_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(generation_id) DO UPDATE SET
                created_at_utc = excluded.created_at_utc,
                manifest_path = excluded.manifest_path,
                manifest_sha256 = excluded.manifest_sha256,
                output_path = excluded.output_path,
                output_sha256 = excluded.output_sha256,
                character = excluded.character,
                profile_id = excluded.profile_id,
                authority_commit = excluded.authority_commit,
                compiled_workflow_sha256 = excluded.compiled_workflow_sha256,
                seed = excluded.seed,
                updated_at_utc = CURRENT_TIMESTAMP
            """,
            (
                generation_id, created_at_utc, str(manifest_path), manifest_sha256,
                output_path, output_sha256, character, profile_id,
                authority_commit, compiled_sha, seed, qa_status,
            ),
        )

    record = get_generation(database_path, generation_id)
    if record is None:
        raise RuntimeError("generation insert succeeded but lookup returned no row")
    return record


def _row_to_record(row: sqlite3.Row) -> GenerationRecord:
    return GenerationRecord(
        generation_id=row["generation_id"],
        created_at_utc=row["created_at_utc"],
        manifest_path=row["manifest_path"],
        manifest_sha256=row["manifest_sha256"],
        output_path=row["output_path"],
        output_sha256=row["output_sha256"],
        character=row["character"],
        profile_id=row["profile_id"],
        authority_commit=row["authority_commit"],
        compiled_workflow_sha256=row["compiled_workflow_sha256"],
        seed=row["seed"],
        qa_status=row["qa_status"],
    )


def get_generation(database_path: Path, generation_id: str) -> GenerationRecord | None:
    initialize_database(database_path)
    with connect_database(database_path) as connection:
        row = connection.execute(
            "SELECT * FROM generations WHERE generation_id = ?",
            (generation_id,),
        ).fetchone()
    return _row_to_record(row) if row is not None else None


def list_generations(database_path: Path, limit: int = 20) -> list[GenerationRecord]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    initialize_database(database_path)
    with connect_database(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM generations ORDER BY created_at_utc DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def update_qa_status(database_path: Path, generation_id: str, qa_status: str) -> GenerationRecord:
    if qa_status not in QA_STATUSES:
        raise ValueError(f"qa_status must be one of: {', '.join(QA_STATUSES)}")
    initialize_database(database_path)
    with connect_database(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE generations
            SET qa_status = ?, updated_at_utc = CURRENT_TIMESTAMP
            WHERE generation_id = ?
            """,
            (qa_status, generation_id),
        )
        if cursor.rowcount != 1:
            raise KeyError(f"generation_id not found: {generation_id}")

    record = get_generation(database_path, generation_id)
    if record is None:
        raise RuntimeError("status update succeeded but lookup returned no row")
    return record
