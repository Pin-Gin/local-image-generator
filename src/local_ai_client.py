from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, request


@dataclass(frozen=True)
class LocalAIChatResult:
    role: str
    model: str
    content: str
    thinking: str | None
    total_duration: int | None
    load_duration: int | None
    prompt_eval_count: int | None
    eval_count: int | None


class LocalAIClient:
    def __init__(self, config: dict[str, Any]) -> None:
        if config.get("schema_version") != 1:
            raise ValueError("local AI config schema_version must be 1")
        if config.get("provider") != "ollama":
            raise ValueError("local AI provider must be ollama")

        base_url = config.get("base_url")
        timeout = config.get("request_timeout_seconds", 300)
        keep_alive = config.get("keep_alive", "5m")
        roles = config.get("roles")

        if not isinstance(base_url, str) or not base_url.strip():
            raise ValueError("local AI base_url must be a non-empty string")
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("local AI request_timeout_seconds must be positive")
        if not isinstance(keep_alive, str) or not keep_alive.strip():
            raise ValueError("local AI keep_alive must be a non-empty string")
        if not isinstance(roles, dict) or not roles:
            raise ValueError("local AI roles must be a non-empty object")

        normalized_roles: dict[str, dict[str, Any]] = {}
        for role_name, role_cfg in roles.items():
            if not isinstance(role_name, str) or not role_name.strip():
                raise ValueError("local AI role names must be non-empty strings")
            if not isinstance(role_cfg, dict):
                raise ValueError(f"local AI role {role_name} must be an object")

            model = role_cfg.get("model")
            vision = role_cfg.get("vision")
            think = role_cfg.get("think", False)
            num_ctx = role_cfg.get("num_ctx", 4096)
            num_predict = role_cfg.get("num_predict", 1024)
            max_history_messages = role_cfg.get("max_history_messages", 6)
            system_prompt = role_cfg.get("system_prompt")

            if not isinstance(model, str) or not model.strip():
                raise ValueError(f"local AI role {role_name}.model must be a non-empty string")
            if not isinstance(vision, bool):
                raise ValueError(f"local AI role {role_name}.vision must be boolean")
            if not isinstance(think, bool):
                raise ValueError(f"local AI role {role_name}.think must be boolean")
            if not isinstance(num_ctx, int) or isinstance(num_ctx, bool) or num_ctx < 4096:
                raise ValueError(f"local AI role {role_name}.num_ctx must be an integer >= 4096")
            if not isinstance(num_predict, int) or isinstance(num_predict, bool) or num_predict <= 0:
                raise ValueError(f"local AI role {role_name}.num_predict must be a positive integer")
            if (
                not isinstance(max_history_messages, int)
                or isinstance(max_history_messages, bool)
                or max_history_messages < 0
            ):
                raise ValueError(
                    f"local AI role {role_name}.max_history_messages must be a non-negative integer"
                )
            if not isinstance(system_prompt, str):
                raise ValueError(f"local AI role {role_name}.system_prompt must be a string")

            normalized_roles[role_name] = {
                "model": model.strip(),
                "vision": vision,
                "think": think,
                "num_ctx": num_ctx,
                "num_predict": num_predict,
                "max_history_messages": max_history_messages,
                "system_prompt": system_prompt.strip(),
            }

        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = float(timeout)
        self.keep_alive = keep_alive
        self.roles = normalized_roles

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        raw_body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            raw_body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"

        req = request.Request(
            f"{self.base_url}{path}",
            data=raw_body,
            headers=headers,
            method=method,
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"local AI HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"local AI connection failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RuntimeError("local AI request timed out") from exc

        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("local AI returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("local AI JSON root must be an object")
        return parsed

    def list_models(self) -> list[str]:
        payload = self._request_json("GET", "/api/tags")
        models = payload.get("models")
        if not isinstance(models, list):
            raise RuntimeError("local AI /api/tags response is missing models")

        names: list[str] = []
        for model in models:
            if not isinstance(model, dict):
                continue
            name = model.get("name")
            if isinstance(name, str) and name:
                names.append(name)
        return sorted(set(names))

    def status(self) -> dict[str, Any]:
        installed = self.list_models()
        return {
            "provider": "ollama",
            "base_url": self.base_url,
            "installed_models": installed,
            "roles": {
                role_name: {
                    "model": role_cfg["model"],
                    "vision": role_cfg["vision"],
                    "think": role_cfg["think"],
                    "num_ctx": role_cfg["num_ctx"],
                    "num_predict": role_cfg["num_predict"],
                    "max_history_messages": role_cfg["max_history_messages"],
                    "installed": role_cfg["model"] in installed,
                }
                for role_name, role_cfg in self.roles.items()
            },
        }

    def chat(
        self,
        role: str,
        message: str,
        *,
        history: list[dict[str, Any]] | None = None,
        images_base64: list[str] | None = None,
    ) -> LocalAIChatResult:
        if role not in self.roles:
            raise ValueError(f"unknown local AI role: {role}")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("local AI message must be a non-empty string")

        role_cfg = self.roles[role]
        images = images_base64 or []
        if images and not role_cfg["vision"]:
            raise ValueError(f"local AI role {role} does not accept images")
        for index, image in enumerate(images):
            if not isinstance(image, str) or not image.strip():
                raise ValueError(f"local AI image {index} must be a non-empty base64 string")

        messages: list[dict[str, Any]] = []
        if role_cfg["system_prompt"]:
            messages.append({"role": "system", "content": role_cfg["system_prompt"]})

        if history is not None:
            if not isinstance(history, list):
                raise ValueError("local AI history must be an array")

            validated_history: list[dict[str, str]] = []
            for index, item in enumerate(history):
                if not isinstance(item, dict):
                    raise ValueError(f"local AI history[{index}] must be an object")
                history_role = item.get("role")
                history_content = item.get("content")
                if history_role not in {"user", "assistant"}:
                    raise ValueError(f"local AI history[{index}].role is invalid")
                if not isinstance(history_content, str):
                    raise ValueError(f"local AI history[{index}].content must be a string")
                validated_history.append({"role": history_role, "content": history_content})

            history_limit = role_cfg["max_history_messages"]
            if history_limit > 0:
                messages.extend(validated_history[-history_limit:])

        user_message: dict[str, Any] = {"role": "user", "content": message.strip()}
        if images:
            user_message["images"] = images
        messages.append(user_message)

        response = self._request_json(
            "POST",
            "/api/chat",
            {
                "model": role_cfg["model"],
                "messages": messages,
                "think": role_cfg["think"],
                "stream": False,
                "keep_alive": self.keep_alive,
                "options": {
                    "num_ctx": role_cfg["num_ctx"],
                    "num_predict": role_cfg["num_predict"],
                },
            },
        )

        response_message = response.get("message")
        if not isinstance(response_message, dict):
            raise RuntimeError("local AI chat response is missing message")
        content = response_message.get("content")
        thinking = response_message.get("thinking")
        if not isinstance(content, str):
            raise RuntimeError("local AI chat response content must be a string")
        if thinking is not None and not isinstance(thinking, str):
            thinking = None

        return LocalAIChatResult(
            role=role,
            model=role_cfg["model"],
            content=content,
            thinking=thinking,
            total_duration=response.get("total_duration") if isinstance(response.get("total_duration"), int) else None,
            load_duration=response.get("load_duration") if isinstance(response.get("load_duration"), int) else None,
            prompt_eval_count=response.get("prompt_eval_count") if isinstance(response.get("prompt_eval_count"), int) else None,
            eval_count=response.get("eval_count") if isinstance(response.get("eval_count"), int) else None,
        )


def load_local_ai_config(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"failed to load local AI config: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("local AI config root must be an object")
    return payload


def encode_image_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    return base64.b64encode(path.read_bytes()).decode("ascii")
