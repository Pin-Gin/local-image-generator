from __future__ import annotations

import json
import uuid
from pathlib import Path

from local_ai_client import LocalAIClient, load_local_ai_config
from local_ai_tools import LocalAIToolbox
from oracle_knowledge_store import OracleKnowledgeStore


ROOT = Path(__file__).resolve().parent.parent
STAGING_ROOT = ROOT / "learning" / "local-ai" / "store" / "staging"


def _write_test_part(part_id: str) -> tuple[str, Path, dict]:
    ref = f"part:{part_id}@1"
    document = {
        "schema_version": 1,
        "document_type": "local-rag/json-part",
        "part_id": part_id,
        "version": 1,
        "part_type": "test",
        "name": "Local stack integration test",
        "status": "staging",
        "aliases": [],
        "tags": ["test", "integration"],
        "payload": {
            "generation": {
                "positive": "local stack integration marker",
                "negative": "",
            }
        },
        "provenance": {
            "source_type": "integration-test",
            "source_ref": "src/local_stack_integration_test.py",
        },
    }
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    path = STAGING_ROOT / f"{part_id}.v1.json"
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return ref, path, document


def _safe_remove_file(path: Path) -> None:
    resolved_root = STAGING_ROOT.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise RuntimeError(f"test cleanup refuses file outside staging root: {resolved}") from exc
    if resolved.exists():
        resolved.unlink()


def main() -> int:
    part_id = f"test.integration-{uuid.uuid4().hex[:12]}"
    ref, file_path, document = _write_test_part(part_id)
    store = OracleKnowledgeStore(ROOT)
    oracle_inserted = False

    try:
        health = store.health()
        if not health.get("online"):
            raise RuntimeError(f"Oracle is not online: {health}")
        print(
            f"[INTEGRATION:ORACLE:OK] schema={health.get('schema')} version={health.get('schema_version')}"
        )

        upsert = store.upsert_json_part(document, file_path=str(file_path))
        oracle_inserted = True
        if upsert.get("ref") != ref or upsert.get("status") != "staging":
            raise RuntimeError(f"unexpected Oracle upsert result: {upsert}")
        print(f"[INTEGRATION:UPSERT:OK] {ref}")

        direct = store.get_json_part(ref)
        if direct is None:
            raise RuntimeError("Oracle direct readback returned no row")
        if direct.get("status") != "staging":
            raise RuntimeError(f"unexpected direct read status: {direct.get('status')}")
        if direct.get("document", {}).get("part_id") != part_id:
            raise RuntimeError("Oracle direct readback part_id mismatch")
        print("[INTEGRATION:READBACK:OK]")

        toolbox = LocalAIToolbox(ROOT, ROOT / "config" / "local_tools.json")
        git_status = toolbox.git.status("local-image-generator")
        if "status" not in git_status:
            raise RuntimeError("Git tool status response is missing status")
        print("[INTEGRATION:GIT-READ:OK]")

        tool_result = toolbox.execute("json_part_get", {"ref": ref})
        if tool_result.get("source") != "oracle":
            raise RuntimeError(f"json_part_get did not resolve from Oracle: {tool_result}")
        if tool_result.get("status") != "staging":
            raise RuntimeError(f"json_part_get status mismatch: {tool_result.get('status')}")
        print("[INTEGRATION:TOOLBOX:OK]")

        client = LocalAIClient(load_local_ai_config(ROOT / "config" / "local_ai.json"))
        prompt = (
            "必ず json_part_get ツールを使用して次の参照を取得してください。\n"
            f"{ref}\n"
            "取得したツール結果だけを根拠に、payload.generation.positive の値をそのまま回答に含めてください。"
        )
        ai_result = client.chat_with_tools(
            "learn",
            prompt,
            tools=toolbox.tools_for_role("learn"),
            execute_tool=toolbox.execute,
            max_rounds=6,
        )
        if "local stack integration marker" not in ai_result.content:
            raise RuntimeError(
                "local AI did not return the expected Oracle-backed marker; "
                f"content={ai_result.content!r}"
            )
        print(f"[INTEGRATION:LOCAL-AI-TOOL:OK] model={ai_result.model}")
        print("[LOCAL-STACK:INTEGRATION:OK]")
        return 0
    finally:
        cleanup_errors: list[str] = []
        if oracle_inserted:
            try:
                result = store.delete_staging_test_json_part(ref)
                if not result.get("deleted"):
                    cleanup_errors.append(f"Oracle cleanup did not delete test row: {result}")
            except Exception as exc:  # cleanup must not hide the primary test failure
                cleanup_errors.append(f"Oracle cleanup failed: {exc}")
        try:
            _safe_remove_file(file_path)
        except Exception as exc:
            cleanup_errors.append(f"file cleanup failed: {exc}")

        if cleanup_errors:
            print("[INTEGRATION:CLEANUP:WARN] " + " | ".join(cleanup_errors))
        else:
            print(f"[INTEGRATION:CLEANUP:OK] {ref}")


if __name__ == "__main__":
    raise SystemExit(main())
