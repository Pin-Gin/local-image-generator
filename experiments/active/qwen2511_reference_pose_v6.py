"""Qwen-Image-Edit-2511 image1=identity/style, image2=pose guide, image3=derived head reference.

local-image-generator experimental v6: no Canon changes, no model training, no
background work. The API graph follows Comfy-Org's native Qwen 2511 blueprint.
Image2 is a semantic pose *reference*, not a hard ControlNet constraint.

Preflight validates available Comfy nodes/models; quality remains UNVERIFIED.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

DEFAULT_MODEL = "qwen_image_edit_2511_int8_convrot.safetensors"
DEFAULT_CLIP = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
DEFAULT_VAE = "qwen_image_vae.safetensors"
MASTER_NAME_IN_GRAPH = "30"
POSE_NAME_IN_GRAPH = "20"
KNOWN_SEATED_M_POSE_SHA256 = "5c878552a3ff18b220886a8c27f1e4e3c1e8df0cfa23e0a2c7a7f74ad49185fd"

class V6Error(RuntimeError):
    def __init__(self, category: str, message: str):
        self.category = category
        super().__init__(message)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def get_previous_names(path: Path) -> tuple[str, str]:
    try:
        graph = json.loads(path.read_text(encoding="utf-8"))
        master = graph[MASTER_NAME_IN_GRAPH]["inputs"]["image"]
        pose = graph[POSE_NAME_IN_GRAPH]["inputs"]["image"]
        if graph[MASTER_NAME_IN_GRAPH]["class_type"] != "LoadImage" or graph[POSE_NAME_IN_GRAPH]["class_type"] != "LoadImage":
            raise ValueError("expected LoadImage nodes")
        if not all(isinstance(n, str) and n for n in (master, pose)):
            raise ValueError("image name empty")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise V6Error("SOURCE_INCOMPATIBLE", f"v1-v3 compiled graph with image nodes 30/20 required: {exc}") from exc
    return master, pose


def resolve_pose(text: str) -> dict[str, Any]:
    # Existing local generator is deliberately reused instead of writing a
    # second pose dictionary that would silently disagree with it.
    try:
        from free_text_pose_poc import classify_request
    except ImportError as exc:
        raise V6Error("ENVIRONMENT", "free_text_pose_poc.py is missing from experiments/active") from exc
    try:
        request = classify_request(text)
    except Exception as exc:
        category = getattr(exc, "code", "PARSE_ERROR")
        raise V6Error(category, str(exc)) from exc
    if request.get("interpretation", {}).get("coverage") != "COMPLETE_FOR_POC":
        raise V6Error("PARSE_INCOMPLETE", "未解釈条件があるため、別のポーズ・衣装へ黙って置き換えず停止します")
    if request.get("pose", {}).get("view") != "front":
        raise V6Error("POSE_UNSUPPORTED", "v6 diagnostic supports front view only")
    return request


def require_same_pose(source: Path, request: dict[str, Any]) -> None:
    """Older saved graph has NO general pose ID; trust only its specific M-seated fixture.

    This is a strict compatibility gate to avoid attaching a stale pose image to
    a different instruction. For other poses, provide --master and generate new pose.
    """
    if request.get("pose", {}).get("id") != "seated_m":
        raise V6Error("POSE_SOURCE_MISMATCH", "既存セッションの骨格画像はM字座位用です。別の姿勢は--masterで再生成してください")
    _, pose = get_previous_names(source)
    # The original tested seated-M pose has a known image fingerprint prefix.
    # A generic POC_POSE prefix alone does not authenticate the actual pose.
    if pose != "POC_POSE_5c878552a3ff.png":
        raise V6Error("POSE_SOURCE_UNVERIFIED", "旧骨格画像はM字座位として未確認です。--masterから新規生成してください")


def pose_prompt(request: dict[str, Any]) -> str:
    pose_id = request["pose"]["id"]
    mapping = {
        "seated_m": "sitting upright on the room floor, hips supported by the floor, both knees bent and pointing outward, lower legs tucked inward, M-shaped seated legs (not cross-legged)",
        "arms_down": "standing upright, both arms resting naturally at her sides",
        "arms_out": "standing upright with both arms spread horizontally at shoulder level",
    }
    if pose_id not in mapping:
        raise V6Error("POSE_UNSUPPORTED", pose_id)
    return mapping[pose_id]


def edit_prompt(text: str, request: dict[str, Any], face_reference: bool) -> str:
    if not isinstance(text, str) or not text.strip():
        raise V6Error("PARSE_ERROR", "instruction is empty")
    pose = pose_prompt(request)
    expression = "a natural gentle smile" if request["deltas"].get("expression") == "soft_smile" else "the reference expression"
    face = ("Image 3 is a close-up crop from the SAME Image 1, provided only to preserve its unique face and short haircut. "
            if face_reference else "")
    return (
        "Edit the provided illustrated adult woman while preserving her identity. "
        "Image 1 is the authoritative full-body MASTER: preserve her precise face, eye shape, expression design, "
        "short light brown bob, head-to-body proportions (7.3 heads where measurable), hair and skin texture, "
        "clothing and their specific material details, and soft matte anime realism rendering. "
        "Image 2 is ONLY an OpenPose skeleton layout guide; use it to understand joint positions and pose. "
        "Do not render Image 2's black background, colored sticks, bones, text, or joints. "
        + face +
        "Change ONLY her physical pose and requested facial expression. Pose target: " + pose + ". "
        "Body and camera face front. Expression: " + expression + ". "
        "Preserve the original room and rug; keep floor contact plausible. "
        "Do not add a chair or bed. Do not replace her with another person or redraw in photorealistic style. "
        "The following is the user's original Japanese instruction; preserve its meaning exactly: 「" + text.strip() + "」"
    )


def build_graph(master_name: str, pose_name: str, text: str, request: dict[str, Any],
                *, face_name: str | None = None, model: str = DEFAULT_MODEL,
                clip: str = DEFAULT_CLIP, vae: str = DEFAULT_VAE,
                seed: int = 975311, steps: int = 20, cfg: float = 4.0,
                filename_prefix: str = "LOCAL_RAG_QWEN2511_V6") -> dict[str, Any]:
    if not master_name or not pose_name:
        raise V6Error("INPUT_MISSING", "master and pose image names must be present")
    if not all(isinstance(x, str) and x.strip() for x in (model, clip, vae)):
        raise V6Error("MODEL_NAME_INVALID", "model names required")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0 or not 1 <= steps <= 100 or not 0 < cfg <= 20:
        raise V6Error("SAMPLING_INVALID", "seed, steps, or cfg out of range")
    prompt = edit_prompt(text, request, bool(face_name))
    g = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": model, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": clip, "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": vae}},
        "4": {"class_type": "LoadImage", "inputs": {"image": master_name}},
        "5": {"class_type": "LoadImage", "inputs": {"image": pose_name}},
        "6": {"class_type": "FluxKontextImageScale", "inputs": {"image": ["4", 0]}},
        "7": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "image1": ["6", 0], "image2": ["5", 0], "prompt": prompt}},
        "8": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["2", 0], "vae": ["3", 0], "image1": ["6", 0], "image2": ["5", 0], "prompt": ""}},
        "9": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["7", 0], "reference_latents_method": "index_timestep_zero"}},
        "10": {"class_type": "FluxKontextMultiReferenceLatentMethod", "inputs": {"conditioning": ["8", 0], "reference_latents_method": "index_timestep_zero"}},
        "11": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["1", 0], "shift": 3.1}},
        "12": {"class_type": "CFGNorm", "inputs": {"model": ["11", 0], "strength": 1.0}},
        "13": {"class_type": "VAEEncode", "inputs": {"pixels": ["6", 0], "vae": ["3", 0]}},
        "14": {"class_type": "KSampler", "inputs": {"model": ["12", 0], "positive": ["9", 0], "negative": ["10", 0], "latent_image": ["13", 0], "seed": seed, "steps": steps, "cfg": float(cfg), "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "15": {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["3", 0]}},
        "16": {"class_type": "SaveImage", "inputs": {"images": ["15", 0], "filename_prefix": filename_prefix}},
    }
    if face_name:
        g["17"] = {"class_type": "LoadImage", "inputs": {"image": face_name}}
        g["7"]["inputs"]["image3"] = ["17", 0]
        g["8"]["inputs"]["image3"] = ["17", 0]
    ensure_graph(g)
    return g


def is_link(x: Any) -> bool:
    return isinstance(x, list) and len(x) == 2 and isinstance(x[0], str) and isinstance(x[1], int)


def ensure_graph(g: dict[str, Any]) -> None:
    if g.get("7", {}).get("class_type") != "TextEncodeQwenImageEditPlus" or g.get("14", {}).get("class_type") != "KSampler":
        raise V6Error("GRAPH_INVALID", "Qwen native graph required")
    if g["7"]["inputs"]["image2"] != ["5", 0] or g["14"]["inputs"]["latent_image"] != ["13", 0]:
        raise V6Error("GRAPH_INVALID", "reference/pose links incorrect")
    visit_stack, done = set(), set()
    def visit(k: str) -> None:
        if k in visit_stack:
            raise V6Error("GRAPH_CYCLE", k)
        if k in done:
            return
        visit_stack.add(k)
        for v in g[k]["inputs"].values():
            if is_link(v):
                if v[0] not in g:
                    raise V6Error("GRAPH_DANGLING_LINK", f"{k}->{v[0]}")
                visit(v[0])
        visit_stack.remove(k)
        done.add(k)
    for node in g:
        visit(node)


def fetch_object_info(base_url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/object_info", timeout=20) as r:
            payload = json.load(r)
    except (OSError, ValueError) as exc:
        raise V6Error("COMFYUI_UNAVAILABLE", str(exc)) from exc
    if not isinstance(payload, dict):
        raise V6Error("COMFYUI_UNAVAILABLE", "/object_info is not an object")
    return payload


def validate_runtime(graph: dict[str, Any], info: dict[str, Any]) -> None:
    for nid, node in graph.items():
        typ = node["class_type"]
        meta = info.get(typ)
        if not isinstance(meta, dict):
            raise V6Error("COMFYUI_NODE_MISSING", f"{nid}:{typ}")
        inputs = meta.get("input", {})
        allowed = set(inputs.get("required", {})) | set(inputs.get("optional", {})) | set(inputs.get("hidden", {}))
        for k in node["inputs"]:
            if k not in allowed:
                raise V6Error("COMFYUI_INPUT_MISSING", f"{nid}:{typ}.{k}")
    for nid, cls, key in (("1", "UNETLoader", "unet_name"), ("2", "CLIPLoader", "clip_name"), ("3", "VAELoader", "vae_name")):
        value = graph[nid]["inputs"][key]
        choices = info[cls]["input"].get("required", {}).get(key, [[]])[0]
        if isinstance(choices, list) and value not in choices:
            raise V6Error("COMFYUI_MODEL_MISSING", f"{value} ({cls})")


def ui_graph(graph: dict[str, Any], info: dict[str, Any]) -> dict[str, Any]:
    """Metadata-derived editable UI JSON. Frontend import remains Windows-unverified."""
    validate_runtime(graph, info)
    positions = {
        "1": (0, 100), "2": (0, 360), "3": (0, 620), "4": (0, 920), "5": (0, 1190), "6": (370, 920),
        "7": (760, 660), "8": (760, 1120), "9": (1160, 660), "10": (1160, 1120),
        "11": (760, 70), "12": (1160, 70), "13": (760, 1450), "14": (1550, 570),
        "15": (1900, 570), "16": (2250, 570), "17": (370, 1470),
    }
    edges = []
    data_nodes = []
    for nid, node in graph.items():
        md = info[node["class_type"]]
        inp = md.get("input", {})
        io = md.get("input_order", {})
        names = list(io.get("required") or list(inp.get("required", {}))) + list(io.get("optional") or list(inp.get("optional", {})))
        names += [k for k in node["inputs"] if k not in names]
        widgets = []
        input_objs = []
        for name in names:
            if name not in node["inputs"]:
                continue
            val = node["inputs"][name]
            if is_link(val):
                src, ix = val
                srcinfo = info[graph[src]["class_type"]]
                outs = srcinfo.get("output", [])
                if ix < 0 or ix >= len(outs):
                    raise V6Error("INVALID_OUTPUT_SLOT", f"{src}[{ix}]")
                edgetype = outs[ix] if isinstance(outs[ix], str) else "*"
                edgeid = len(edges) + 1
                edges.append([edgeid, int(src), ix, int(nid), len(input_objs), edgetype])
                input_objs.append({"name": name, "type": edgetype, "link": edgeid})
            else:
                widgets.append(val)
        out_names = md.get("output_name") or []
        outs = []
        for i, typ in enumerate(md.get("output", [])):
            outs.append({"name": out_names[i] if i < len(out_names) else f"output_{i}",
                         "type": typ if isinstance(typ, str) else "*", "links": None, "slot_index": i})
        x, y = positions.get(nid, (2600, 300))
        data_nodes.append({"id": int(nid), "type": node["class_type"], "pos": [x, y], "size": [340, 200],
                           "flags": {}, "order": len(data_nodes), "mode": 0, "inputs": input_objs,
                           "outputs": outs, "properties": {"Node name for S&R": node["class_type"]}, "widgets_values": widgets})
    byid = {n["id"]: n for n in data_nodes}
    for eid, source, slot, _, _, _ in edges:
        o = byid[source]["outputs"][slot]
        if o["links"] is None:
            o["links"] = []
        o["links"].append(eid)
    return {"last_node_id": max(map(int, graph)), "last_link_id": len(edges), "nodes": data_nodes,
            "links": edges, "groups": [], "config": {}, "extra": {}, "version": 0.4}


def crop_head_from_master(master: Path, dest: Path) -> dict[str, Any]:
    """Diagnostic-only deterministic crop for the specific frontal full-body master layout.

    No face detector is claimed. Fails on non-portrait/atypical layout to avoid
    presenting a wrong crop as a verified face reference.
    """
    from PIL import Image
    with Image.open(master) as im:
        im = im.convert("RGB")
        w, h = im.size
        if not (h / w > 1.4 and w >= 600 and h >= 900):
            raise V6Error("FACE_CROP_UNSUPPORTED", "auto crop supports only portrait full-body frontal masters for this POC")
        box = tuple(round(v) for v in (.31 * w, .004 * h, .69 * w, .194 * h))
        head = im.crop(box)
        dest.parent.mkdir(parents=True, exist_ok=True)
        head.save(dest)
    return {"path": str(dest), "box": list(box), "source_size": [w, h],
            "method": "fixed_relative_crop_diagnostic_not_face_detection", "sha256": digest(dest)}


def create_review_sheet(master: Path, output: Path, destination: Path) -> None:
    """Visual side-by-side QA aid; no numerical identity score is asserted."""
    from PIL import Image, ImageOps, ImageDraw
    w, h = 540, 900
    im1 = Image.open(master).convert("RGB")
    im2 = Image.open(output).convert("RGB")
    canvas = Image.new("RGB", (w * 2, h + 65), (235, 235, 235))
    a = ImageOps.contain(im1, (w - 20, h - 20))
    b = ImageOps.contain(im2, (w - 20, h - 20))
    canvas.paste(a, ((w - a.width) // 2, 60 + (h - a.height) // 2))
    canvas.paste(b, (w + (w - b.width) // 2, 60 + (h - b.height) // 2))
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 20), "MASTER / identity and style source", fill=(0, 0, 0))
    draw.text((w + 20, 20), "V6 OUTPUT - UNVERIFIED", fill=(0, 0, 0))
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination)


def build_from_master(root: Path, master: Path, text: str, out: Path) -> tuple[dict[str, Any], Path]:
    request = resolve_pose(text)
    try:
        from free_text_pose_poc import render_pose
    except ImportError as exc:
        raise V6Error("ENVIRONMENT", "free_text_pose_poc.py missing") from exc
    pose = out / "pose_guide.png"
    render_pose(request["pose"]["id"], pose)
    return request, pose


def runtime_helpers():
    # Delayed until --run; unit tests do not require a project installation.
    from comfyui_client import (fetch_system_stats, upload_input_image, submit_prompt, poll_history, download_image)
    return fetch_system_stats, upload_input_image, submit_prompt, poll_history, download_image


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Qwen-Image-Edit-2511 local image generator v6")
    origin = ap.add_mutually_exclusive_group(required=True)
    origin.add_argument("--source", type=Path, help="existing generated session compiled_workflow.json")
    origin.add_argument("--master", type=Path, help="original local master image (auto pose guide)")
    ap.add_argument("--text", required=True, help="Japanese natural-language instruction")
    ap.add_argument("--face-reference", choices=("off", "auto"), default="auto")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--clip", default=DEFAULT_CLIP)
    ap.add_argument("--vae", default=DEFAULT_VAE)
    ap.add_argument("--seed", type=int, default=975311)
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--cfg", type=float, default=4.0)
    ap.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    ap.add_argument("--preflight", action="store_true")
    ap.add_argument("--make-ui", action="store_true", help="export editable ComfyUI workflow with live node metadata")
    ap.add_argument("--run", action="store_true", help="queue GPU generation once, not retry")
    args = ap.parse_args(argv)
    out = ROOT / "outputs" / "experiments" / "qwen2511_v6" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out.mkdir(parents=True, exist_ok=False)
    report: dict[str, Any] = {"schema_version": 1, "status": "STARTED", "backend": "qwen-image-edit-2511-native-multireference",
                               "identity_qa": "NOT_PERFORMED", "style_qa": "NOT_PERFORMED", "pose_qa": "NOT_PERFORMED",
                               "safety_qa": "NOT_PERFORMED", "user_text": args.text,
                               "notes": ["Image2 is soft semantic pose reference, not ControlNet", "no model training"]}
    try:
        req = resolve_pose(args.text)
        local_master: Path | None = None
        local_pose: Path | None = None
        if args.master:
            if not args.master.is_file():
                raise V6Error("MASTER_MISSING", str(args.master))
            local_master = args.master.resolve()
            req, local_pose = build_from_master(ROOT, local_master, args.text, out)
            master_name = "V6_MASTER_" + digest(local_master)[:16] + local_master.suffix.lower()
            pose_name = "V6_POSE_" + digest(local_pose)[:16] + ".png"
            report["master_sha256"] = digest(local_master)
            report["pose_sha256"] = digest(local_pose)
        else:
            if not args.source.is_file():
                raise V6Error("SOURCE_MISSING", str(args.source))
            require_same_pose(args.source, req)
            master_name, pose_name = get_previous_names(args.source)
            report["source_workflow_sha256"] = digest(args.source)
            report["existing_comfy_master_name"] = master_name
            report["existing_comfy_pose_name"] = pose_name
        report["request"] = req

        if args.preflight or args.make_ui or args.run:
            info = fetch_object_info(args.comfy_url)
            report["comfyui_object_info"] = "READ_SUCCESS"
        else:
            info = None

        # For the prior session, validate the actual stored pose bytes, not just
        # its filename. This avoids stale/replaced ComfyUI inputs becoming a
        # silently incorrect pose guide.
        if args.source and args.run:
            _, _, _, _, dl = runtime_helpers()
            verified_pose = out / "verified_pose_guide.png"
            dl(args.comfy_url, pose_name, "", "input", verified_pose, timeout_seconds=45)
            actual_pose = digest(verified_pose)
            report["pose_sha256"] = actual_pose
            if actual_pose != KNOWN_SEATED_M_POSE_SHA256:
                raise V6Error("POSE_SOURCE_MISMATCH", f"ComfyUI stored pose SHA256 differs: {actual_pose}")

        # In --source mode the input can be fetched from *local* ComfyUI. This
        # does not require a second user reference or modify the original.
        if args.face_reference == "auto" and args.run and local_master is None:
            _, _, _, _, download_image = runtime_helpers()
            local_master = out / "master_for_internal_crop.png"
            download_image(args.comfy_url, master_name, "", "input", local_master, timeout_seconds=45)
            report["master_sha256"] = digest(local_master)

        face_name = None
        face_local = None
        if args.face_reference == "auto" and local_master is not None:
            face_local = out / "head_from_master.png"
            crop_meta = crop_head_from_master(local_master, face_local)
            face_name = "V6_HEAD_" + crop_meta["sha256"][:16] + ".png"
            report["face_reference"] = crop_meta
        else:
            report["face_reference"] = {"status": "NOT_USED", "reason": "crop disabled or original master unavailable before --run"}

        graph = build_graph(master_name, pose_name, args.text, req, face_name=face_name,
                            model=args.model, clip=args.clip, vae=args.vae,
                            seed=args.seed, steps=args.steps, cfg=args.cfg)
        graph_path = out / "workflow_v6_api.json"
        graph_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report.update({"status": "COMPILED_ONLY", "graph": str(graph_path), "graph_sha256": digest(graph_path),
                       "models": {"diffusion": args.model, "clip": args.clip, "vae": args.vae},
                       "generation": {"seed": args.seed, "steps": args.steps, "cfg": args.cfg}})
        if info is not None:
            validate_runtime(graph, info)
            report["runtime_preflight"] = "PASS"
        if args.make_ui and info is not None:
            ui_path = out / "workflow_v6_ui.json"
            ui_path.write_text(json.dumps(ui_graph(graph, info), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            report["ui_graph"] = str(ui_path)
            report["ui_import_test"] = "NOT_PERFORMED"
        if args.run:
            fetch_system_stats, upload_input_image, submit_prompt, poll_history, download_image = runtime_helpers()
            fetch_system_stats(args.comfy_url)
            if args.master:
                graph["4"]["inputs"]["image"] = upload_input_image(args.comfy_url, args.master, remote_name=master_name, timeout_seconds=60)
                assert local_pose is not None
                graph["5"]["inputs"]["image"] = upload_input_image(args.comfy_url, local_pose, remote_name=pose_name, timeout_seconds=60)
            if face_local is not None:
                graph["17"]["inputs"]["image"] = upload_input_image(args.comfy_url, face_local, remote_name=face_name, timeout_seconds=60)
            graph_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            report["graph_sha256"] = digest(graph_path)
            result_id = submit_prompt(args.comfy_url, graph, timeout_seconds=60)
            entry = poll_history(args.comfy_url, result_id, timeout_seconds=1200)
            images = entry.get("outputs", {}).get("16", {}).get("images", [])
            if not images:
                raise V6Error("COMFYUI_OUTPUT_MISSING", "SaveImage node 16 did not produce an image")
            image_info = images[0]
            filename = image_info["filename"]
            dest = out / "images" / filename
            download_image(args.comfy_url, filename, image_info.get("subfolder", ""), image_info.get("type", "output"), dest, timeout_seconds=60)
            if local_master is not None:
                comparison = out / "visual_qa_comparison.png"
                create_review_sheet(local_master, dest, comparison)
                report["visual_qa_comparison"] = str(comparison)
            report.update({"status": "GENERATED_UNVERIFIED", "prompt_id": result_id,
                           "output_path": str(dest), "output_sha256": digest(dest)})
        print(f"[V6:{report['status']}]")
        print(f"[V6:OUTPUT] {out}")
        return 0
    except V6Error as exc:
        report.update(status="FAIL", error_type=exc.category, message=str(exc))
        print(f"[V6:FAIL:{exc.category}] {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        report.update(status="FAIL", error_type="RUNTIME_ERROR", message=str(exc))
        print(f"[V6:FAIL:RUNTIME_ERROR] {exc}", file=sys.stderr)
        return 3
    finally:
        (out / "diagnostic.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
