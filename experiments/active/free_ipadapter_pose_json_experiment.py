from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from comfyui_client import run_workflow_and_download, upload_input_image
from free_compiler import compile_free_generation
from free_generation_plan import build_free_generation_engine_plan
from json_parts import load_json_part
from model_catalog import resolve_project_checkpoint


CONFIG_PATH = ROOT / "config" / "app.example.json"
PROFILE_PATH = ROOT / "profiles" / "free_sdxl_v1.json"
RENDERING_PATH = ROOT / "shared" / "rendering" / "matte_dimensional_anime.json"
LINEART_PATH = ROOT / "shared" / "lineart" / "strong_anime_lineart.json"
POSE_MODEL = "SDXL/controlnet-openpose-sdxl-1.0/diffusion_pytorch_model.safetensors"
SUPPORTED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
DEFAULT_DIAGNOSTIC_PART = "part:diagnostic.authority_probe@1"


def _load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _weighted_prompt(text: str, strength: float) -> str:
    stripped = text.strip()
    if abs(strength - 1.0) < 1e-9:
        return stripped
    return f"({stripped}:{strength:g})"


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
            "Experimental FREE authority split: source image -> IP-Adapter appearance, "
            "pose image -> DWPose/OpenPose ControlNet, JSON Part -> exact content, "
            "shared Matte Dimensional Anime -> rendering, strong lineart conditioning -> contours. "
            "No local LLM is used."
        )
    )
    parser.add_argument("source_image", type=_image_arg)
    parser.add_argument("pose_image", type=_image_arg)
    parser.add_argument(
        "--part",
        default=DEFAULT_DIAGNOSTIC_PART,
        help=f"Accepted JSON Part ref. Default: {DEFAULT_DIAGNOSTIC_PART}",
    )
    parser.add_argument(
        "--ip-weight",
        type=float,
        default=0.75,
        help="IP-Adapter appearance weight. Lowered from the first experiment so pose control has more room. Default: 0.75",
    )
    parser.add_argument(
        "--ip-start",
        type=float,
        default=0.30,
        help="IP-Adapter start percentage. Later start lets DWPose establish body structure first. Default: 0.30",
    )
    parser.add_argument(
        "--pose-strength",
        type=float,
        default=1.20,
        help="OpenPose ControlNet strength. Default: 1.20",
    )
    parser.add_argument(
        "--rendering-strength",
        type=float,
        default=1.25,
        help="Prompt weight applied only to Matte Dimensional Anime rendering conditioning. Default: 1.25",
    )
    parser.add_argument(
        "--lineart-strength",
        type=float,
        default=1.65,
        help="Strong Anime Lineart conditioning strength. Default: 1.65",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=28,
        help="KSampler steps for this multi-conditioning diagnostic. Default: 28",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=975311,
        help="KSampler seed. Default: 975311",
    )
    parser.add_argument(
        "--repeat-check",
        action="store_true",
        help="Run the exact same workflow twice and report whether output file SHA256 is identical.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not 0.0 < args.ip_weight <= 5.0:
        raise ValueError("--ip-weight must be > 0 and <= 5.0")
    if not 0.0 <= args.ip_start < 1.0:
        raise ValueError("--ip-start must be >= 0 and < 1.0")
    if not 0.0 < args.pose_strength <= 2.0:
        raise ValueError("--pose-strength must be > 0 and <= 2.0")
    if not 0.0 < args.rendering_strength <= 2.0:
        raise ValueError("--rendering-strength must be > 0 and <= 2.0")
    if not 0.0 < args.lineart_strength <= 2.0:
        raise ValueError("--lineart-strength must be > 0 and <= 2.0")
    if args.steps <= 0:
        raise ValueError("--steps must be a positive integer")
    if args.seed < 0:
        raise ValueError("--seed must be a non-negative integer")

    config = _load_json(CONFIG_PATH)
    profile = _load_json(PROFILE_PATH)
    rendering = _load_json(RENDERING_PATH)
    lineart = _load_json(LINEART_PATH)
    part = load_json_part(ROOT, args.part)

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
        remote_name=f"LOCAL_RAG_IP_SOURCE_{source_sha[:12]}{args.source_image.suffix.lower()}",
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
    workflow["steps"] = args.steps
    workflow["cfg"] = generation["cfg"]
    workflow["sampler_name"] = generation["sampler_name"]
    workflow["scheduler"] = generation["scheduler"]
    workflow["denoise"] = 1.0

    rendering_for_plan = copy.deepcopy(rendering)
    base_rendering_positive = rendering_for_plan["prompt"]["positive"]
    rendering_for_plan["prompt"]["positive"] = _weighted_prompt(
        base_rendering_positive,
        args.rendering_strength,
    )

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
        content_positive=part.positive,
        content_negative=part.negative,
        workflow=workflow,
        shared_rendering=rendering_for_plan,
        lineart_profile=lineart,
        lineart_enabled=True,
        lineart_strength=args.lineart_strength,
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
        filename_prefix="LOCAL_RAG_FREE_IP_POSE_JSON",
    )

    workflow_json = compiled.compiled_workflow

    # The deterministic FREE compiler already provides exact JSON content,
    # stronger shared rendering conditioning, strong lineart conditioning,
    # optional configured rendering/lineart LoRAs, and DWPose/OpenPose control.
    # IP-Adapter is inserted only on the MODEL path. The sampler uses a fresh
    # latent so source-image pose is not carried in through img2img.
    base_model_ref = workflow_json["7"]["inputs"]["model"]
    workflow_json["30"] = {
        "class_type": "LoadImage",
        "inputs": {
            "image": source_remote,
        },
    }
    workflow_json["40"] = {
        "class_type": "IPAdapterUnifiedLoader",
        "inputs": {
            "model": base_model_ref,
            "preset": "PLUS (high strength)",
        },
    }
    workflow_json["41"] = {
        "class_type": "IPAdapterAdvanced",
        "inputs": {
            "model": ["40", 0],
            "ipadapter": ["40", 1],
            "image": ["30", 0],
            "weight": float(args.ip_weight),
            "weight_type": "linear",
            "combine_embeds": "concat",
            "start_at": float(args.ip_start),
            "end_at": 1.0,
            "embeds_scaling": "K+mean(V) w/ C penalty",
        },
    }
    workflow_json["7"]["inputs"]["model"] = ["41", 0]
    workflow_json["7"]["inputs"]["denoise"] = 1.0

    result = run_workflow_and_download(
        base_url=base_url,
        workflow=workflow_json,
        output_dir=output_root,
        request_timeout_seconds=request_timeout,
        generation_timeout_seconds=generation_timeout,
    )
    first_output_sha = _sha256(result.output_path)

    repeat_result = None
    repeat_output_sha = None
    if args.repeat_check:
        repeat_root = output_root / "repeat"
        repeat_result = run_workflow_and_download(
            base_url=base_url,
            workflow=workflow_json,
            output_dir=repeat_root,
            request_timeout_seconds=request_timeout,
            generation_timeout_seconds=generation_timeout,
        )
        repeat_output_sha = _sha256(repeat_result.output_path)

    rendering_lora = plan["loras"]["rendering"]
    lineart_lora = plan["loras"]["lineart"]
    manifest = {
        "schema_version": 1,
        "experiment": "free-ipadapter-plus-json-plus-dwpose-strong-render-line-v2",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "ai_interpretation": False,
        "source_image": {
            "path": str(args.source_image),
            "sha256": source_sha,
            "uploaded_name": source_remote,
            "role": "IP-Adapter appearance authority",
            "weight": args.ip_weight,
            "start_at": args.ip_start,
            "end_at": 1.0,
            "preset": "PLUS (high strength)",
        },
        "json_part": {
            "ref": part.ref,
            "path": str(part.path),
            "sha256": part.sha256,
            "positive": part.positive,
            "negative": part.negative,
        },
        "pose_control": {
            "source": str(args.pose_image),
            "source_sha256": pose_sha,
            "uploaded_name": pose_remote,
            "backend": "dwpose",
            "controlnet_model": POSE_MODEL,
            "strength": args.pose_strength,
            "start_percent": 0.0,
            "end_percent": 1.0,
        },
        "rendering": {
            "rendering_id": rendering.get("rendering_id"),
            "conditioning_enabled": True,
            "conditioning_strength": args.rendering_strength,
            "lora_enabled": bool(rendering_lora.get("enabled")),
            "lora_name": rendering_lora.get("lora_name"),
        },
        "lineart": {
            "enabled": True,
            "conditioning_strength": args.lineart_strength,
            "lora_enabled": bool(lineart_lora and lineart_lora.get("enabled")),
            "lora_name": None if lineart_lora is None else lineart_lora.get("lora_name"),
        },
        "sampler": {
            "steps": args.steps,
            "seed": args.seed,
        },
        "latent": {
            "mode": "fresh-text2img-latent",
            "denoise": 1.0,
        },
        "output": {
            "path": str(result.output_path),
            "sha256": first_output_sha,
        },
        "repeat_check": None if repeat_result is None else {
            "path": str(repeat_result.output_path),
            "sha256": repeat_output_sha,
            "same_sha256": first_output_sha == repeat_output_sha,
        },
        "comfyui": {
            "prompt_id": result.prompt_id,
            "repeat_prompt_id": None if repeat_result is None else repeat_result.prompt_id,
        },
    }
    manifest_path = output_root / "experiment_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[FREE:IPADAPTER:SOURCE-UPLOAD:OK] {source_remote}")
    print(f"[FREE:IPADAPTER:JSON-PART:OK] {part.ref}")
    print(f"[FREE:IPADAPTER:POSE-UPLOAD:OK] {pose_remote}")
    print(f"[FREE:IPADAPTER:APPEARANCE:OK] weight={args.ip_weight:g} start={args.ip_start:g}")
    print(f"[FREE:IPADAPTER:DWPOSE:OK] strength={args.pose_strength:g}")
    print(
        f"[FREE:IPADAPTER:RENDERING-CONDITIONING:OK] "
        f"{rendering.get('rendering_id')} strength={args.rendering_strength:g}"
    )
    print(f"[FREE:IPADAPTER:LINEART:OK] strength={args.lineart_strength:g}")
    print(
        "[FREE:IPADAPTER:RENDERING-LORA:{}] {}".format(
            "ON" if rendering_lora.get("enabled") else "OFF",
            rendering_lora.get("lora_name"),
        )
    )
    print(
        "[FREE:IPADAPTER:LINEART-LORA:{}] {}".format(
            "ON" if lineart_lora and lineart_lora.get("enabled") else "OFF",
            None if lineart_lora is None else lineart_lora.get("lora_name"),
        )
    )
    print(f"[FREE:IPADAPTER:FRESH-LATENT:OK] denoise=1 steps={args.steps} seed={args.seed}")
    print(f"[FREE:IPADAPTER:COMFYUI:OK] prompt_id={result.prompt_id}")
    print(f"[FREE:IPADAPTER:OUTPUT:OK] {result.output_path}")
    if repeat_result is not None:
        same = first_output_sha == repeat_output_sha
        print(f"[FREE:IPADAPTER:REPEAT:OUTPUT] {repeat_result.output_path}")
        print(
            f"[FREE:IPADAPTER:REPEAT:SHA256:{'SAME' if same else 'DIFFERENT'}] "
            f"first={first_output_sha} repeat={repeat_output_sha}"
        )
    print(f"[FREE:IPADAPTER:MANIFEST:OK] {manifest_path}")
    print("[FREE:IPADAPTER:EXPERIMENT:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
