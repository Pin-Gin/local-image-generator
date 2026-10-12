from __future__ import annotations

import copy
import http.client
import json
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import ui_server


def _candidate() -> dict:
    return {
        "schema_version": 1,
        "document_type": "local-rag/json-part",
        "part_id": "test.ui-api-sync",
        "version": 1,
        "part_type": "background_scene",
        "name": "UI API sync test",
        "status": "staging",
        "aliases": ["ui api test"],
        "tags": ["test", "ui-api"],
        "payload": {
            "generation": {
                "positive": "neutral diagnostic background",
                "negative": "text, watermark",
            },
            "structured": {
                "preserve": "this exact payload",
                "sequence": [1, 2, 1],
            },
        },
        "provenance": {
            "source_type": "integration-test",
            "source_ref": "json_part_ui_api_test",
        },
    }


def main() -> int:
    original_root = ui_server.ROOT
    with tempfile.TemporaryDirectory(prefix="local-rag-json-ui-api-") as temp:
        resource_root = Path(temp)
        (resource_root / "learning/local-ai/store/json-parts").mkdir(parents=True)
        (resource_root / "learning/local-ai/store/staging").mkdir(parents=True)
        ui_server.ROOT = resource_root

        server = ThreadingHTTPServer(("127.0.0.1", 0), ui_server.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            candidate = _candidate()
            original_payload = copy.deepcopy(candidate["payload"])
            body = json.dumps({"document": candidate, "accept": True}).encode("utf-8")
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
            connection.request(
                "POST",
                "/api/knowledge/json-part",
                body=body,
                headers={"Content-Type": "application/json", "Content-Length": str(len(body))},
            )
            response = connection.getresponse()
            raw = response.read()
            connection.close()
            if response.status != 200:
                raise AssertionError(f"UI JSON Part API failed: HTTP {response.status}: {raw.decode('utf-8', 'replace')}")

            payload = json.loads(raw.decode("utf-8"))
            result = payload["json_part"]
            if result["status"] != "accepted":
                raise AssertionError("UI API did not return accepted status")
            if result.get("semantic_preservation") != "status-only":
                raise AssertionError("UI API did not report status-only semantic preservation")

            accepted_path = Path(result["path"])
            if not accepted_path.is_file():
                raise AssertionError("accepted JSON Part was not written")
            accepted_document = json.loads(accepted_path.read_text(encoding="utf-8"))
            if accepted_document["payload"] != original_payload:
                raise AssertionError("payload changed through UI API acceptance")
            if accepted_document["status"] != "accepted":
                raise AssertionError("accepted document status is not accepted")

            staging_path = resource_root / "learning/local-ai/store/staging/test.ui-api-sync.v1.json"
            if staging_path.exists():
                raise AssertionError("staging file remained after successful UI API acceptance")
            receipt_path = Path(result["receipt_path"])
            if not receipt_path.is_file():
                raise AssertionError("acceptance receipt was not written")

            print("[JSON-UI-API:HTTP:OK]")
            print("[JSON-UI-API:HASH-GATED-ACCEPT:OK]")
            print("[JSON-UI-API:PAYLOAD-PRESERVED:OK]")
            print("[JSON-UI-API:RECEIPT:OK]")
            print("[JSON-UI-API:TEST:OK]")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            ui_server.ROOT = original_root

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
