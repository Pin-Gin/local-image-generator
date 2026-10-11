from __future__ import annotations

import argparse
import sys
from pathlib import Path

from local_ai_client import LocalAIClient, encode_image_file, load_local_ai_config


def repository_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the project-local Ollama runtime and a configured model role")
    parser.add_argument("--role", default="learn", choices=("learn", "dev"))
    parser.add_argument("--prompt", default="Give a short self-introduction.")
    parser.add_argument("--image", type=Path)
    args = parser.parse_args()

    root = repository_root()
    config_path = root / "config" / "local_ai.json"

    try:
        client = LocalAIClient(load_local_ai_config(config_path))
        status = client.status()
    except Exception as exc:
        print(f"[LOCAL-AI:FAIL] {exc}", file=sys.stderr)
        return 1

    role_status = status["roles"].get(args.role)
    if not isinstance(role_status, dict):
        print(f"[LOCAL-AI:FAIL] unknown role: {args.role}", file=sys.stderr)
        return 1

    print(f"[LOCAL-AI:OK] provider={status['provider']}")
    print(f"[LOCAL-AI:OK] base_url={status['base_url']}")
    print(f"[LOCAL-AI:OK] role={args.role}")
    print(f"[LOCAL-AI:OK] model={role_status['model']}")
    print(f"[LOCAL-AI:OK] installed={role_status['installed']}")

    if not role_status["installed"]:
        print("[LOCAL-AI:FAIL] configured model is not installed", file=sys.stderr)
        return 2

    images: list[str] = []
    if args.image is not None:
        image_path = args.image if args.image.is_absolute() else (root / args.image).resolve()
        try:
            images.append(encode_image_file(image_path))
        except OSError as exc:
            print(f"[LOCAL-AI:FAIL] image: {exc}", file=sys.stderr)
            return 3

    try:
        result = client.chat(args.role, args.prompt, images_base64=images)
    except Exception as exc:
        print(f"[LOCAL-AI:FAIL] chat: {exc}", file=sys.stderr)
        return 4

    if not result.content.strip():
        print("[LOCAL-AI:FAIL] model returned empty content", file=sys.stderr)
        print(f"[LOCAL-AI:DIAG] thinking_present={bool(result.thinking and result.thinking.strip())}", file=sys.stderr)
        if result.prompt_eval_count is not None:
            print(f"prompt_eval_count={result.prompt_eval_count}", file=sys.stderr)
        if result.eval_count is not None:
            print(f"eval_count={result.eval_count}", file=sys.stderr)
        return 5

    print("[LOCAL-AI:CHAT:OK]")
    print(f"model={result.model}")
    print(f"content={result.content}")
    if result.prompt_eval_count is not None:
        print(f"prompt_eval_count={result.prompt_eval_count}")
    if result.eval_count is not None:
        print(f"eval_count={result.eval_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
