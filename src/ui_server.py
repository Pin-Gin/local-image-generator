from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from chat_contract import build_generation_request, list_profile_ids
from generation_bridge import run_chat_generation


ROOT = Path(__file__).resolve().parent.parent
UI_ROOT = ROOT / "ui"
PROFILES_ROOT = ROOT / "profiles"
INTENT_ROOT = ROOT / "intent"
CONFIG_PATH = ROOT / "config" / "app.example.json"
OUTPUTS_ROOT = ROOT / "outputs"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(UI_ROOT), **kwargs)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json_body(self) -> dict[str, Any]:
        length_header = self.headers.get("Content-Length", "0")
        try:
            length = int(length_header)
        except ValueError as exc:
            raise ValueError("invalid_content_length") from exc
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid_json") from exc
        if not isinstance(payload, dict):
            raise ValueError("body_must_be_object")
        return payload

    def _build_request_from_body(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_text = payload.get("user_text")
        profile_id = payload.get("profile_id")
        if not isinstance(user_text, str) or not isinstance(profile_id, str):
            raise ValueError("user_text_and_profile_id_are_required")

        known_profiles = list_profile_ids(PROFILES_ROOT)
        if profile_id not in known_profiles:
            raise ValueError("unknown_profile_id")

        return build_generation_request(
            user_text,
            profile_id,
            dictionary_root=INTENT_ROOT,
        )

    def _serve_generated_file(self) -> bool:
        prefix = "/generated/"
        if not self.path.startswith(prefix):
            return False

        relative = unquote(self.path[len(prefix):]).replace("\\", "/")
        target = (OUTPUTS_ROOT / relative).resolve()
        outputs_root = OUTPUTS_ROOT.resolve()
        try:
            target.relative_to(outputs_root)
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN)
            return True

        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return True

        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)
        return True

    def do_GET(self) -> None:
        if self._serve_generated_file():
            return
        if self.path == "/api/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return
        if self.path == "/api/profiles":
            self._send_json(HTTPStatus.OK, {"profiles": list_profile_ids(PROFILES_ROOT)})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path not in {"/api/chat/request", "/api/chat/generate"}:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        try:
            payload = self._read_json_body()
            request_payload = self._build_request_from_body(payload)
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        if self.path == "/api/chat/request":
            self._send_json(HTTPStatus.OK, {"request": request_payload})
            return

        try:
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if not isinstance(config, dict):
                raise ValueError("application config root must be an object")
            result = run_chat_generation(ROOT, request_payload, config)
            relative_output = result.output_path.relative_to(OUTPUTS_ROOT).as_posix()
        except (OSError, KeyError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        self._send_json(
            HTTPStatus.OK,
            {
                "request": request_payload,
                "generation": {
                    "generation_id": result.generation_id,
                    "prompt_id": result.prompt_id,
                    "output_url": f"/generated/{relative_output}",
                    "output_sha256": result.output_sha256,
                    "manifest_path": str(result.manifest_path),
                    "manifest_sha256": result.manifest_sha256,
                    "generation_plan_path": str(result.generation_plan_path),
                    "database_path": str(result.database_path),
                },
            },
        )


def main() -> int:
    host = "127.0.0.1"
    port = 8765
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"[UI:OK] http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
