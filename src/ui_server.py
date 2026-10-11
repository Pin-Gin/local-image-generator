from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from chat_contract import build_generation_request, list_profile_ids


ROOT = Path(__file__).resolve().parent.parent
UI_ROOT = ROOT / "ui"
PROFILES_ROOT = ROOT / "profiles"


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

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return
        if self.path == "/api/profiles":
            self._send_json(HTTPStatus.OK, {"profiles": list_profile_ids(PROFILES_ROOT)})
            return
        super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/chat/request":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        length_header = self.headers.get("Content-Length", "0")
        try:
            length = int(length_header)
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_content_length"})
            return

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return

        if not isinstance(payload, dict):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "body_must_be_object"})
            return

        user_text = payload.get("user_text")
        profile_id = payload.get("profile_id")
        if not isinstance(user_text, str) or not isinstance(profile_id, str):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "user_text_and_profile_id_are_required"})
            return

        known_profiles = list_profile_ids(PROFILES_ROOT)
        if profile_id not in known_profiles:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "unknown_profile_id"})
            return

        try:
            request_payload = build_generation_request(user_text, profile_id)
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.OK, {"request": request_payload})


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
