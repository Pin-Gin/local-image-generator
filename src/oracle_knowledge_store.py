from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from json_parts import parse_part_ref, validate_json_part


ENV_FILE_NAME = ".env.local-ai"


def _candidate_roots(resource_root: Path) -> list[Path]:
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


def resolve_env_file(resource_root: Path) -> Path | None:
    for root in _candidate_roots(resource_root):
        candidate = root / ENV_FILE_NAME
        if candidate.is_file():
            return candidate
    return None


def load_env_file(path: Path | None) -> dict[str, str]:
    values: dict[str, str] = {}
    if path is None or not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


class OracleKnowledgeStore:
    def __init__(self, resource_root: Path) -> None:
        env_file = resolve_env_file(resource_root)
        file_values = load_env_file(env_file)
        self.env_file = env_file
        self.dsn = os.getenv("LOCALRAG_ORACLE_DSN") or file_values.get("LOCALRAG_ORACLE_DSN", "")
        self.user = os.getenv("LOCALRAG_ORACLE_USER") or file_values.get("LOCALRAG_ORACLE_USER", "")
        self.password = os.getenv("LOCALRAG_ORACLE_PASSWORD") or file_values.get("LOCALRAG_ORACLE_PASSWORD", "")

    def configured(self) -> bool:
        return bool(self.dsn and self.user and self.password)

    def _driver(self):
        try:
            import oracledb  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "python-oracledb is not installed. Run setup_local_tools.ps1 first."
            ) from exc
        return oracledb

    def _connect(self):
        if not self.configured():
            raise RuntimeError(
                "Oracle knowledge store is not configured. Create .env.local-ai from .env.local-ai.example."
            )
        oracledb = self._driver()
        return oracledb.connect(user=self.user, password=self.password, dsn=self.dsn)

    def health(self) -> dict[str, Any]:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT META_VALUE FROM LR_SCHEMA_META WHERE META_KEY = 'schema_version'")
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("Oracle schema metadata is missing")
                cursor.execute("SELECT SYS_CONTEXT('USERENV','CURRENT_SCHEMA') FROM dual")
                schema_row = cursor.fetchone()
        return {
            "configured": True,
            "online": True,
            "dsn": self.dsn,
            "schema": schema_row[0] if schema_row else self.user,
            "schema_version": str(row[0]),
            "env_file": str(self.env_file) if self.env_file else None,
        }

    def search_knowledge(self, query: str, *, limit: int = 10) -> list[dict[str, Any]]:
        text = query.strip()
        if not text:
            raise ValueError("knowledge search query must not be empty")
        limit = max(1, min(int(limit), 50))
        pattern = f"%{text.casefold()}%"
        sql = """
            SELECT KNOWLEDGE_ID, KIND, TITLE, SUMMARY, STATUS, SOURCE_TYPE, SOURCE_REF, CONTENT_JSON
            FROM (
              SELECT KNOWLEDGE_ID, KIND, TITLE, SUMMARY, STATUS, SOURCE_TYPE, SOURCE_REF, CONTENT_JSON, UPDATED_AT
              FROM LR_KNOWLEDGE_ITEM
              WHERE STATUS = 'accepted'
                AND (
                  LOWER(TITLE) LIKE :pattern
                  OR LOWER(NVL(SUMMARY, '')) LIKE :pattern
                  OR LOWER(DBMS_LOB.SUBSTR(CONTENT_JSON, 4000, 1)) LIKE :pattern
                )
              ORDER BY UPDATED_AT DESC
            )
            WHERE ROWNUM <= :row_limit
        """
        results: list[dict[str, Any]] = []
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, pattern=pattern, row_limit=limit)
                for row in cursor:
                    raw_json = row[7].read() if hasattr(row[7], "read") else row[7]
                    try:
                        content = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
                    except json.JSONDecodeError:
                        content = {"raw": raw_json}
                    results.append(
                        {
                            "knowledge_id": row[0],
                            "kind": row[1],
                            "title": row[2],
                            "summary": row[3],
                            "status": row[4],
                            "source_type": row[5],
                            "source_ref": row[6],
                            "content": content,
                        }
                    )
        return results

    def get_json_part(self, ref: str) -> dict[str, Any] | None:
        part_id, version = parse_part_ref(ref)
        sql = """
            SELECT DOCUMENT_JSON, FILE_PATH, CONTENT_SHA256, STATUS
            FROM LR_JSON_PART
            WHERE PART_ID = :part_id AND PART_VERSION = :version
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, part_id=part_id, version=version)
                row = cursor.fetchone()
        if row is None:
            return None
        raw_json = row[0].read() if hasattr(row[0], "read") else row[0]
        if isinstance(raw_json, dict):
            document = raw_json
        elif isinstance(raw_json, (str, bytes, bytearray)):
            document = json.loads(raw_json)
        else:
            raise TypeError(f"unexpected Oracle JSON value type: {type(raw_json).__name__}")
        return {
            "ref": ref,
            "document": document,
            "file_path": row[1],
            "sha256": row[2],
            "status": row[3],
        }

    def upsert_json_part(self, document: dict[str, Any], *, file_path: str | None = None) -> dict[str, Any]:
        part = validate_json_part(document)
        canonical = json.dumps(part, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        sql = """
            MERGE INTO LR_JSON_PART target
            USING (
              SELECT :part_id AS PART_ID, :part_version AS PART_VERSION FROM dual
            ) source
            ON (target.PART_ID = source.PART_ID AND target.PART_VERSION = source.PART_VERSION)
            WHEN MATCHED THEN UPDATE SET
              PART_TYPE = :part_type,
              PART_NAME = :part_name,
              DOCUMENT_JSON = :document_json,
              FILE_PATH = :file_path,
              CONTENT_SHA256 = :content_sha256,
              STATUS = :status,
              UPDATED_AT = SYSTIMESTAMP
            WHEN NOT MATCHED THEN INSERT (
              PART_ID, PART_VERSION, PART_TYPE, PART_NAME, DOCUMENT_JSON,
              FILE_PATH, CONTENT_SHA256, STATUS
            ) VALUES (
              :part_id, :part_version, :part_type, :part_name, :document_json,
              :file_path, :content_sha256, :status
            )
        """
        params = {
            "part_id": part["part_id"],
            "part_version": part["version"],
            "part_type": part["part_type"],
            "part_name": part["name"],
            "document_json": canonical,
            "file_path": file_path,
            "content_sha256": digest,
            "status": part["status"],
        }
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
            connection.commit()
        return {
            "ref": f"part:{part['part_id']}@{part['version']}",
            "sha256": digest,
            "status": part["status"],
        }

    def save_knowledge(
        self,
        *,
        kind: str,
        title: str,
        content: dict[str, Any],
        summary: str = "",
        source_type: str = "local-ai",
        source_ref: str = "",
        status: str = "accepted",
    ) -> dict[str, Any]:
        if status not in {"staging", "accepted", "retired"}:
            raise ValueError("knowledge status must be staging, accepted, or retired")
        if not kind.strip() or not title.strip():
            raise ValueError("knowledge kind/title must not be empty")
        canonical = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        knowledge_id = uuid.uuid4().hex
        sql = """
            INSERT INTO LR_KNOWLEDGE_ITEM (
              KNOWLEDGE_ID, KIND, TITLE, SUMMARY, CONTENT_JSON, STATUS,
              SOURCE_TYPE, SOURCE_REF, CONTENT_SHA256
            ) VALUES (
              :knowledge_id, :kind, :title, :summary, :content_json, :status,
              :source_type, :source_ref, :content_sha256
            )
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql,
                    knowledge_id=knowledge_id,
                    kind=kind.strip(),
                    title=title.strip(),
                    summary=summary.strip(),
                    content_json=canonical,
                    status=status,
                    source_type=source_type.strip(),
                    source_ref=source_ref.strip(),
                    content_sha256=digest,
                )
            connection.commit()
        return {"knowledge_id": knowledge_id, "sha256": digest, "status": status}
