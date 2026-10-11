from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from comfyui_client import run_workflow_and_download, upload_input_image
from free_compiler import compile_free_generation
from free_generation_plan import build_free_generation_engine_plan
from model_catalog import resolve_project_checkpoint


ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "app.example.json"
PROFILE_PATH = ROOT / "profiles" / "free_sdxl_v1.json"
RENDERING_PATH = ROOT / "shared" / "rendering" / "matte_dimensional_anime.json"
LINEART_PATH = ROOT / "shared" / "lineart" / "strong_anime_lineart.json"
POSE_MODEL = "SDXL/controlnet-openpose-sdxl-1.0/diffusion_pytorch_model.safetensors"
SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _image_arg(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"image file not found: {path}")
    if path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
        raise argparse.ArgumentTypeError(f"unsupported image type: {path.suffix}")
    return path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Experimental FREE image-authority test: use one source image as img2img identity/appearance "
            "authority and a second image only as DWPose/ControlNet pose authority. No local LLM is used."
        )
    )
    parser.add_argument(
        "source_image",
        type=_image_arg,
        help="Image whose character appearance/clothing/hair should be preserved as strongly as img2img allows.",
    )
    parser.add_argument(
        "pose_image",
        type=_image_arg,
        help="Image used only to extract pose through DWPose.",
    )
    parser.add_argument(
        "--denoise",
        type=float,
        default=0.45,
        help="Img2img denoise. Lower preserves the source image more strongly; higher allows larger pose changes. Default: 0.45",
    )
    parser.add_argument(
        "--pose-strength",
        type=float,
        default=0.9,
        help="ControlNet pose strength. Default: 0.9",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=975311,
        help="KSampler seed. Default: 975311",
    )
    parser.add_argument(
        "--positive",
        default="adult anime character, full body, preserve source appearance, preserve source clothing and hairstyle",
        help="Content conditioning used alongside the source-image latent.",
    )
    parser.add_argument(
        "--negative",
        default="bad anatomy, blurry, identity drift, clothing drift, hairstyle drift",
        help="Negative content conditioning.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not 0.0 < args.denoise <= 1.0:
        raise ValueError("--denoise must be > 0 and <= 1.0")
    if not 0.0 < args.pose_strength <= 2.0:
        raise ValueError("--pose-strength must be > 0 and <= 2.0")
    if args.seed < 0:
        raise ValueError("--seed must be a non-negative integer")

    config = _load_json(CONFIG_PATH)
    profile = _load_json(PROFILE_PATH)
    rendering = _load_json(RENDERING_PATH)
    lineart = _load_json(LINEART_PATH)

    comfyui = config.get("comfyui")
    if not isinstance(comfyui, dict):
        raise RuntimeError("config.comfyui must be an object")
    base_url = comfyui.get("base_url")
    if not isinstance(base_url, str) or not base_url.strip():
        raise RuntimeError("config.comfyui.base_url must be configured")
    request_timeout = float(comfyui.get("timeout_seconds", 5))
    generation_timeout = float(comfyui.get("generation_timeout_seconds", 180))

    source_sha = _sha256(args.source_image)
    pose_sha = _sha256(args.pose_image)
    source_remote = upload_input_image(
        base_url,
        args.source_image,
        remote_name=f"LOCAL_RAG_SOURCE_{source_sha[:12]}{args.source_image.suffix.lower()}",
        timeout_seconds=max(request_timeout, 30.0),
    )
    pose_remote = upload_input_image(
        base_url,
        args.pose_image,
        remote_name=f"LOCAL_RAG_POSE_{pose_sha[:12]}{args.pose_image.suffix.lower()}",
        timeout_seconds=max(request_timeout, 30.0),
    )

    workflow = dict(profile["workflow"])
    generation = rendering["generation"]
    checkpoint = resolve_project_checkpoint(ROOT, generation["checkpoint"])
    workflow["checkpoint"] = checkpoint
    workflow["steps"] = generation["steps"]
    workflow["cfg"] = generation["cfg"]
    workflow["sampler_name"] = generation["sampler_name"]
    workflow["scheduler"] = generation["scheduler"]
    workflow["denoise"] = args.denoise

    pose_control = {
        "enabled": True,
        "backend": "dwpose",
        "source": {
            "local_path": str(args.pose_image),
            "input_name": pose_remote,
            "sha256": pose_sha,
        },
        "preprocessor": {
            "detect_hand": True,
            "detect_body": True,
            "detect_face": False,
            "resolution": 1024,
            "bbox_detector": "yolox_l.onnx",
            "pose_estimator": "dw-ll_ucoco_384_bs5.torchscript.pt",
            "scale_stick_for_xinsr_cn": True,
        },
        "controlnet": {
            "model": POSE_MODEL,
            "strength": args.pose_strength,
            "start_percent": 0.0,
            "end_percent": 1.0,
        },
    }

    plan = build_free_generation_engine_plan(
        content_positive=args.positive,
        content_negative=args.negative,
        workflow=workflow,
        shared_rendering=rendering,
        lineart_profile=lineart,
        lineart_enabled=False,
        pose_control=pose_control,
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    cache_root = ROOT / "cache" / "experiments" / timestamp
    output_root = ROOT / "outputs" / "experiments" / timestamp
    compiled = compile_free_generation(
        ROOT,
        plan,
        cache_root,
        seed=args.seed,
        filename_prefix="LOCAL_RAG_FREE_IMAGE_POSE",
    )

    workflow_json = compiled.compiled_workflow
    workflow_json["30"] = {
        "class_type": "LoadImage",
        "inputs": {
            "image": source_remote,
        },
    }
    workflow_json["31"] = {
        "class_type": "VAEEncode",
        "inputs": {
            "pixels": ["30", 0],
            "vae": ["1", 2],
        },
    }
    workflow_json["7"]["inputs"]["latent_image"] = ["31", 0]
    workflow_json["7"]["inputs"]["denoise"] = float(args.denoise)

    result = run_workflow_and_download(
        base_url=base_url,
        workflow=workflow_json,
        output_dir=output_root,
        request_timeout_seconds=request_timeout,
        generation_timeout_seconds=generation_timeout,
    )

    manifest = {
        "schema_version": 1,
        "experiment": "free-image-authority-plus-json-pose-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "ai_interpretation": False,
        "source_image": {
            "path": str(args.source_image),
            "sha256": source_sha,
            "uploaded_name": source_remote,
            "role": "img2img appearance authority",
        },
        "json_change": {
            "pose_control": {
                "source": str(args.pose_image),
                "source_sha256": pose_sha,
                "uploaded_name": pose_remote,
                "backend": "dwpose",
                "controlnet_model": POSE_MODEL,
                "strength": args.pose_strength,
            },
            "positive": args.positive,
            "negative": args.negative,
        },
        "img2img": {
            "denoise": args.denoise,
            "latent_source_node": "31",
        },
        "output": {
            "path": str(result.output_path),
            "sha256": _sha256(result.output_path),
        },
        "comfyui": {
            "prompt_id": result.prompt_id,
        },
    }
    manifest_path = output_root / "experiment_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[FREE:IMAGE-AUTHORITY:SOURCE-UPLOAD:OK] {source_remote}")
    print(f"[FREE:IMAGE-AUTHORITY:POSE-UPLOAD:OK] {pose_remote}")
    print(f"[FREE:IMAGE-AUTHORITY:IMG2IMG:OK] denoise={args.denoise:g}")
    print(f"[FREE:IMAGE-AUTHORITY:DWPOSE:OK] strength={args.pose_strength:g}")
    print(f"[FREE:IMAGE-AUTHORITY:COMFYUI:OK] prompt_id={result.prompt_id}")
    print(f"[FREE:IMAGE-AUTHORITY:OUTPUT:OK] {result.output_path}")
    print(f"[FREE:IMAGE-AUTHORITY:MANIFEST:OK] {manifest_path}")
    print("[FREE:IMAGE-AUTHORITY:EXPERIMENT:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
