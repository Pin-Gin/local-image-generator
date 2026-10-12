from __future__ import annotations

import json
import sys
import traceback
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from chat_contract import build_generation_request, list_profile_ids
from generation_bridge import run_chat_generation
from json_part_sync import accept_staged_json_part, stage_json_part
from learning_registry import load_registry, resolve_registry_path, select_assets_with_local_ai
from local_ai_client import LocalAIClient, load_local_ai_config
from local_ai_tools import LocalAIToolbox
from oracle_knowledge_store import OracleKnowledgeStore


def _resource_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


ROOT = _resource_root()
UI_ROOT = ROOT / "ui"
PROFILES_ROOT = ROOT / "profiles"
INTENT_ROOT = ROOT / "intent"
CONFIG_PATH = ROOT / "config" / "app.example.json"
LOCAL_AI_CONFIG_PATH = ROOT / "config" / "local_ai.json"
LOCAL_TOOLS_CONFIG_PATH = ROOT / "config" / "local_tools.json"
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

    def _local_ai_client(self) -> LocalAIClient:
        return LocalAIClient(load_local_ai_config(LOCAL_AI_CONFIG_PATH))

    def _local_ai_toolbox(self) -> LocalAIToolbox:
        return LocalAIToolbox(ROOT, LOCAL_TOOLS_CONFIG_PATH)

    def _attach_learned_asset_selection(
        self,
        request_payload: dict[str, Any],
        *,
        user_text: str,
    ) -> dict[str, Any]:
        generation_domain = request_payload.get("generation_domain")
        if generation_domain not in {"free", "memoriela"}:
            raise ValueError("generation_domain must be resolved before learned asset selection")

        registry_path = resolve_registry_path(ROOT)
        registry = load_registry(registry_path)
        selection = select_assets_with_local_ai(
            self._local_ai_client(),
            registry,
            user_text=user_text,
            generation_domain=generation_domain,
        )
        request_payload["learning"] = selection.to_request_payload()
        return request_payload

    def _build_request_from_body(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_text = payload.get("user_text")
        profile_id = payload.get("profile_id")
        if not isinstance(user_text, str) or not isinstance(profile_id, str):
            raise ValueError("user_text_and_profile_id_are_required")

        known_profiles = list_profile_ids(PROFILES_ROOT)
        if profile_id not in known_profiles:
            raise ValueError("unknown_profile_id")

        seed_mode = payload.get("seed_mode", "PROFILE")
        seed = payload.get("seed")
        if not isinstance(seed_mode, str):
            raise ValueError("seed_mode must be a string")
        if seed is not None and (not isinstance(seed, int) or isinstance(seed, bool)):
            raise ValueError("seed must be an integer or null")

        request_payload = build_generation_request(
            user_text,
            profile_id,
            dictionary_root=INTENT_ROOT,
            seed_mode=seed_mode,
            seed=seed,
        )
        return self._attach_learned_asset_selection(request_payload, user_text=user_text)

    def _serve_generated_file(self) -> bool:
        request_path = urlsplit(self.path).path
        prefix = "/generated/"
        if not request_path.startswith(prefix):
            return False

        relative = unquote(request_path[len(prefix):]).replace("\\", "/")
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
        if self.path == "/api/local-ai/status":
            try:
                client = self._local_ai_client()
                self._send_json(HTTPStatus.OK, {"local_ai": client.status()})
            except Exception as exc:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {
                        "error": str(exc) or exc.__class__.__name__,
                        "error_type": exc.__class__.__name__,
                    },
                )
            return
        if self.path == "/api/local-tools/status":
            try:
                toolbox = self._local_ai_toolbox()
                self._send_json(HTTPStatus.OK, {"local_tools": toolbox.status()})
            except Exception as exc:
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {
                        "error": str(exc) or exc.__class__.__name__,
                        "error_type": exc.__class__.__name__,
                    },
                )
            return
        if self.path == "/api/learning-registry":
            try:
                registry_path = resolve_registry_path(ROOT)
                registry = load_registry(registry_path)
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "registry": {
                            "registry_version": registry["registry_version"],
                            "asset_count": len(registry["assets"]),
                            "assets": [
                                {
                                    "asset_id": asset["asset_id"],
                                    "enabled": asset["enabled"],
                                    "selection_mode": asset["selection_mode"],
                                    "domains": asset["domains"],
                                    "category": asset["category"],
                                    "runtime_type": asset["runtime"]["type"],
                                }
                                for asset in registry["assets"]
                            ],
                        }
                    },
                )
            except Exception as exc:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "error": str(exc) or exc.__class__.__name__,
                        "error_type": exc.__class__.__name__,
                    },
                )
            return
        super().do_GET()

    def _validate_local_ai_payload(self, payload: dict[str, Any]) -> tuple[str, str, list[Any] | None, list[str] | None]:
        role = payload.get("role")
        message = payload.get("message")
        history = payload.get("history")
        images = payload.get("images")

        if not isinstance(role, str):
            raise ValueError("local AI role is required")
        if not isinstance(message, str):
            raise ValueError("local AI message is required")
        if history is not None and not isinstance(history, list):
            raise ValueError("local AI history must be an array")
        if images is not None and not isinstance(images, list):
            raise ValueError("local AI images must be an array")
        return role, message, history, images

    def _send_local_ai_result(self, result: Any) -> None:
        self._send_json(
            HTTPStatus.OK,
            {
                "local_ai": {
                    "role": result.role,
                    "model": result.model,
                    "content": result.content,
                    "total_duration": result.total_duration,
                    "load_duration": result.load_duration,
                    "prompt_eval_count": result.prompt_eval_count,
                    "eval_count": result.eval_count,
                }
            },
        )

    def _handle_local_ai_chat(self, payload: dict[str, Any], *, with_tools: bool = False) -> None:
        role, message, history, images = self._validate_local_ai_payload(payload)
        client = self._local_ai_client()
        if with_tools:
            toolbox = self._local_ai_toolbox()
            tools = toolbox.tools_for_role(role)
            if tools:
                result = client.chat_with_tools(
                    role,
                    message,
                    tools=tools,
                    execute_tool=toolbox.execute,
                    history=history,
                    images_base64=images,
                )
            else:
                result = client.chat(role, message, history=history, images_base64=images)
        else:
            result = client.chat(role, message, history=history, images_base64=images)
        self._send_local_ai_result(result)

    def _handle_json_part_save(self, payload: dict[str, Any]) -> None:
        document = payload.get("document")
        if not isinstance(document, dict):
            raise ValueError("document must be a JSON object")
        accept_requested = payload.get("accept", False)
        if not isinstance(accept_requested, bool):
            raise ValueError("accept must be a boolean")
        if document.get("status") != "staging":
            raise ValueError("application-managed JSON Part persistence requires status='staging'")

        staged = stage_json_part(ROOT, document, enforce_free_role=True)
        if not accept_requested:
            self._send_json(
                HTTPStatus.OK,
                {
                    "json_part": {
                        "ref": staged.ref,
                        "status": "staging",
                        "part_type": staged.part_type,
                        "path": str(staged.path),
                        "sha256": staged.sha256,
                        "payload_sha256": staged.payload_sha256,
                        "oracle_indexed": False,
                    }
                },
            )
            return

        accepted = accept_staged_json_part(
            ROOT,
            staged.ref,
            expected_sha256=staged.sha256,
            enforce_free_role=True,
        )

        oracle_indexed = False
        oracle_error: str | None = None
        oracle_result: dict[str, Any] | None = None
        store_db = OracleKnowledgeStore(ROOT)
        if store_db.configured():
            try:
                oracle_result = store_db.upsert_json_part(
                    accepted.accepted_document,
                    file_path=str(accepted.accepted_path),
                )
                oracle_indexed = True
            except Exception as exc:
                oracle_error = str(exc) or exc.__class__.__name__

        self._send_json(
            HTTPStatus.OK,
            {
                "json_part": {
                    "ref": accepted.ref,
                    "status": "accepted",
                    "part_type": accepted.part_type,
                    "path": str(accepted.accepted_path),
                    "sha256": accepted.accepted_sha256,
                    "staged_sha256": accepted.staged_sha256,
                    "payload_sha256": accepted.payload_sha256,
                    "semantic_preservation": "status-only",
                    "receipt_path": str(accepted.receipt_path),
                    "oracle_indexed": oracle_indexed,
                    "oracle": oracle_result,
                    "oracle_error": oracle_error,
                }
            },
        )

    def do_POST(self) -> None:
        if self.path in {"/api/local-ai/chat", "/api/local-ai/tool-chat"}:
            try:
                self._handle_local_ai_chat(
                    self._read_json_body(),
                    with_tools=self.path == "/api/local-ai/tool-chat",
                )
            except Exception as exc:
                detail = traceback.format_exc(limit=8)
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "error": str(exc) or exc.__class__.__name__,
                        "error_type": exc.__class__.__name__,
                        "detail": detail,
                    },
                )
            return

        if self.path == "/api/knowledge/json-part":
            try:
                self._handle_json_part_save(self._read_json_body())
            except Exception as exc:
                detail = traceback.format_exc(limit=8)
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "error": str(exc) or exc.__class__.__name__,
                        "error_type": exc.__class__.__name__,
                        "detail": detail,
                    },
                )
            return

        if self.path not in {"/api/chat/request", "/api/chat/generate"}:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        try:
            payload = self._read_json_body()
            request_payload = self._build_request_from_body(payload)

            if self.path == "/api/chat/request":
                self._send_json(HTTPStatus.OK, {"request": request_payload})
                return

            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if not isinstance(config, dict):
                raise ValueError("application config root must be an object")

            result = run_chat_generation(ROOT, request_payload, config)
            relative_output = result.output_path.relative_to(OUTPUTS_ROOT).as_posix()

            request_options = request_payload.get("options", {})
            self._send_json(
                HTTPStatus.OK,
                {
                    "request": request_payload,
                    "generation": {
                        "generation_id": result.generation_id,
                        "prompt_id": result.prompt_id,
                        "seed_mode": request_options.get("seed_mode"),
                        "seed": request_options.get("seed"),
                        "output_url": f"/generated/{relative_output}",
                        "output_sha256": result.output_sha256,
                        "manifest_path": str(result.manifest_path),
                        "manifest_sha256": result.manifest_sha256,
                        "generation_plan_path": str(result.generation_plan_path),
                        "database_path": str(result.database_path),
                        "generation_mode": result.generation_mode,
                        "learned_asset_ids": list(result.learned_asset_ids),
                    },
                },
            )
        except Exception as exc:
            detail = traceback.format_exc(limit=8)
            try:
                self._send_json(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "error": str(exc) or exc.__class__.__name__,
                        "error_type": exc.__class__.__name__,
                        "detail": detail,
                    },
                )
            except Exception:
                pass


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
