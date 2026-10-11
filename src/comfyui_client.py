from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ComfyUIStatus:
    base_url: str
    endpoint: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ComfyUIGenerationResult:
    prompt_id: str
    history: dict[str, Any]
    output_path: Path
    remote_filename: str
    remote_subfolder: str
    remote_type: str


def normalize_base_url(base_url: str) -> str:
    value = base_url.strip().rstrip("/")
    if not value:
        raise ValueError("config.comfyui.base_url must be a non-empty string")
    if not value.startswith(("http://", "https://")):
        raise ValueError("config.comfyui.base_url must start with http:// or https://")
    return value


def _request_json(
    request: urllib.request.Request,
    timeout_seconds: float,
    context: str,
) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read()
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"{context} returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        suffix = f": {detail}" if detail else ""
        raise RuntimeError(f"{context} HTTP error: {exc.code} {exc.reason}{suffix}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{context} connection failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError(f"{context} timed out") from exc

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{context} did not return valid UTF-8 JSON") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"{context} response must be a JSON object")
    return payload


def fetch_system_stats(base_url: str, timeout_seconds: float = 5.0) -> ComfyUIStatus:
    normalized = normalize_base_url(base_url)
    endpoint = f"{normalized}/system_stats"
    request = urllib.request.Request(
        endpoint,
        headers={"Accept": "application/json"},
        method="GET",
    )
    payload = _request_json(request, timeout_seconds, "ComfyUI /system_stats")
    return ComfyUIStatus(base_url=normalized, endpoint=endpoint, payload=payload)


def submit_prompt(base_url: str, workflow: dict[str, Any], timeout_seconds: float = 10.0) -> str:
    normalized = normalize_base_url(base_url)
    endpoint = f"{normalized}/prompt"
    body = json.dumps({"prompt": workflow}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    payload = _request_json(request, timeout_seconds, "ComfyUI /prompt")
    prompt_id = payload.get("prompt_id")
    if not isinstance(prompt_id, str) or not prompt_id:
        raise RuntimeError("ComfyUI /prompt response did not contain prompt_id")
    return prompt_id


def poll_history(
    base_url: str,
    prompt_id: str,
    timeout_seconds: float = 180.0,
    poll_interval_seconds: float = 1.0,
) -> dict[str, Any]:
    normalized = normalize_base_url(base_url)
    deadline = time.monotonic() + timeout_seconds
    endpoint = f"{normalized}/history/{urllib.parse.quote(prompt_id, safe='')}"

    while time.monotonic() < deadline:
        request = urllib.request.Request(endpoint, headers={"Accept": "application/json"}, method="GET")
        payload = _request_json(request, min(10.0, timeout_seconds), "ComfyUI /history")
        entry = payload.get(prompt_id)
        if isinstance(entry, dict):
            status = entry.get("status")
            if isinstance(status, dict) and status.get("status_str") == "error":
                raise RuntimeError(f"ComfyUI generation failed: {json.dumps(status, ensure_ascii=False)}")
            outputs = entry.get("outputs")
            if isinstance(outputs, dict) and outputs:
                return entry
        time.sleep(poll_interval_seconds)

    raise RuntimeError(f"ComfyUI generation timed out after {timeout_seconds:.1f} seconds")


def extract_first_image(history_entry: dict[str, Any]) -> tuple[str, str, str]:
    outputs = history_entry.get("outputs")
    if not isinstance(outputs, dict):
        raise RuntimeError("ComfyUI history has no outputs object")

    for node_output in outputs.values():
        if not isinstance(node_output, dict):
            continue
        images = node_output.get("images")
        if not isinstance(images, list):
            continue
        for image in images:
            if not isinstance(image, dict):
                continue
            filename = image.get("filename")
            subfolder = image.get("subfolder", "")
            image_type = image.get("type", "output")
            if isinstance(filename, str) and filename:
                return filename, str(subfolder), str(image_type)

    raise RuntimeError("ComfyUI history did not contain an output image")


def download_image(
    base_url: str,
    filename: str,
    subfolder: str,
    image_type: str,
    destination: Path,
    timeout_seconds: float = 30.0,
) -> None:
    normalized = normalize_base_url(base_url)
    query = urllib.parse.urlencode(
        {"filename": filename, "subfolder": subfolder, "type": image_type}
    )
    endpoint = f"{normalized}/view?{query}"
    request = urllib.request.Request(endpoint, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            data = response.read()
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"ComfyUI /view returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"ComfyUI /view HTTP error: {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ComfyUI /view connection failed: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError("ComfyUI /view timed out") from exc

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)


def run_workflow_and_download(
    base_url: str,
    workflow: dict[str, Any],
    output_dir: Path,
    request_timeout_seconds: float = 10.0,
    generation_timeout_seconds: float = 180.0,
) -> ComfyUIGenerationResult:
    prompt_id = submit_prompt(base_url, workflow, request_timeout_seconds)
    history = poll_history(base_url, prompt_id, generation_timeout_seconds)
    filename, subfolder, image_type = extract_first_image(history)
    destination = output_dir / filename
    download_image(base_url, filename, subfolder, image_type, destination, request_timeout_seconds)
    return ComfyUIGenerationResult(
        prompt_id=prompt_id,
        history=history,
        output_path=destination,
        remote_filename=filename,
        remote_subfolder=subfolder,
        remote_type=image_type,
    )
