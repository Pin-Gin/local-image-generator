from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/migration/reset_free_json_store.py"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="local-rag-free-json-reset-") as temp:
        root = Path(temp)
        accepted = root / "learning/local-ai/store/json-parts"
        staging = root / "learning/local-ai/store/staging"
        receipts = root / "learning/local-ai/store/receipts"
        accepted.mkdir(parents=True)
        staging.mkdir(parents=True)
        receipts.mkdir(parents=True)

        (accepted / "old.accepted.v1.json").write_text("{}\n", encoding="utf-8")
        (staging / "old.staging.v1.json").write_text("{}\n", encoding="utf-8")
        (receipts / "old.acceptance.json").write_text("{}\n", encoding="utf-8")
        (accepted / ".gitkeep").write_text("", encoding="utf-8")

        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--apply"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stdout + "\n" + completed.stderr)

        expected_part = accepted / "free.test.background_scene.v1.json"
        expected_receipt = receipts / "free.test.background_scene.v1.acceptance.json"
        if not expected_part.is_file():
            raise AssertionError("bootstrap accepted JSON Part was not created")
        if not expected_receipt.is_file():
            raise AssertionError("bootstrap acceptance receipt was not created")
        if (accepted / "old.accepted.v1.json").exists():
            raise AssertionError("old accepted JSON was not deleted")
        if (staging / "old.staging.v1.json").exists():
            raise AssertionError("old staging JSON was not deleted")
        if (receipts / "old.acceptance.json").exists():
            raise AssertionError("old receipt JSON was not deleted")
        if not (accepted / ".gitkeep").is_file():
            raise AssertionError("non-JSON files should not be deleted")

        document = json.loads(expected_part.read_text(encoding="utf-8"))
        receipt = json.loads(expected_receipt.read_text(encoding="utf-8"))
        if document.get("status") != "accepted":
            raise AssertionError("bootstrap document was not accepted")
        if document.get("part_type") != "background_scene":
            raise AssertionError("bootstrap document has wrong part_type")
        structured = document.get("payload", {}).get("structured", {})
        application = structured.get("application", {})
        if application.get("mode") != "delta":
            raise AssertionError("bootstrap background must use delta application mode")
        if application.get("preserve_unspecified") is not True:
            raise AssertionError("bootstrap background must preserve unspecified details")
        if "rendering_technique" not in structured.get("must_not_define", []):
            raise AssertionError("bootstrap background must not own rendering technique")
        if receipt.get("ref") != "part:free.test.background_scene@1":
            raise AssertionError("receipt ref mismatch")
        if receipt.get("semantic_change") != "status: staging -> accepted only":
            raise AssertionError("receipt semantic-change marker mismatch")

        print("[FREE-JSON-RESET:DELETE-OLD:OK]")
        print("[FREE-JSON-RESET:BOOTSTRAP-PART:OK]")
        print("[FREE-JSON-RESET:BOOTSTRAP-SLOT-CONTRACT:OK]")
        print("[FREE-JSON-RESET:BOOTSTRAP-RECEIPT:OK]")
        print("[FREE-JSON-RESET:TEST:OK]")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
