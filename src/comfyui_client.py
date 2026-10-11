from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ComfyUIStatus:
    base_url: str
    endpoint: str
    payload: dict[str, Any]


def normalize_base_url(base_url: str) -> str:
    value = base_url.strip().rstrip("/")
    if not value:
        raise ValueError("config.comfyui.base_url must be a non-empty string")
    if not value.startswith(("http://", "https://")):
        raise ValueError("config.comfyui.base_url must start with http:// or https://")
    return value


def fetch_system_stats(base_url: str, timeout_seconds: float = 5.0) -> ComfyUIStatus:
    normalized = normalize_base_url(base_url)
    endpoint = f"{normalized}/system_stats"
    request = urllib.request.Request(
        endpoint,
        headers={"Accept": "application/json"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
            if response.status != 200:
                raise RuntimeError(f"ComfyUI returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"ComfyUI HTTP error: {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ComfyUI connection failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError("ComfyUI connection timed out") from exc

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("ComfyUI /system_stats did not return valid UTF-8 JSON") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("ComfyUI /system_stats response must be a JSON object")

    return ComfyUIStatus(
        base_url=normalized,
        endpoint=endpoint,
        payload=payload,
    )
