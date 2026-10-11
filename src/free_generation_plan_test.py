from __future__ import annotations

import json
from pathlib import Path

from free_generation_plan import build_free_generation_engine_plan


ROOT = Path(__file__).resolve().parent.parent
PROFILE_PATH = ROOT / "profiles" / "free_sdxl_v1.json"
RENDERING_PATH = ROOT / "shared" / "rendering" / "matte_dimensional_anime.json"


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return payload


def main() -> int:
    profile = _load(PROFILE_PATH)
    rendering = _load(RENDERING_PATH)

    workflow = dict(profile["workflow"])
    generation = rendering["generation"]
    workflow["checkpoint"] = generation["checkpoint"]
    workflow["steps"] = generation["steps"]
    workflow["cfg"] = generation["cfg"]
    workflow["sampler_name"] = generation["sampler_name"]
    workflow["scheduler"] = generation["scheduler"]

    content_positive = "test subject, pose.body.state: standing"
    content_negative = "bad anatomy"

    plan = build_free_generation_engine_plan(
        content_positive=content_positive,
        content_negative=content_negative,
        workflow=workflow,
        shared_rendering=rendering,
    )

    if plan.get("engine_id") != "free-deterministic-v1":
        raise AssertionError(f"unexpected engine id: {plan.get('engine_id')}")
    if plan.get("domain") != "free":
        raise AssertionError(f"unexpected domain: {plan.get('domain')}")

    ai = plan.get("ai_interpretation", {})
    if ai.get("enabled") is not False:
        raise AssertionError(f"FREE plan unexpectedly enables AI interpretation: {ai}")

    conditioning = plan.get("conditioning", {})
    content = conditioning.get("content", {})
    if content.get("positive") != content_positive:
        raise AssertionError(f"content positive was changed: {content.get('positive')!r}")
    if content.get("negative") != content_negative:
        raise AssertionError(f"content negative was changed: {content.get('negative')!r}")

    rendering_channel = conditioning.get("rendering", {})
    if rendering_channel.get("positive") != rendering["prompt"]["positive"]:
        raise AssertionError("rendering positive is not isolated from content")
    if rendering_channel.get("negative") != rendering["prompt"]["negative"]:
        raise AssertionError("rendering negative is not isolated from content")

    lineart = conditioning.get("lineart", {})
    if lineart.get("enabled") is not False:
        raise AssertionError("lineart must start disabled until its dedicated runtime is added")

    if plan.get("pose_control", {}).get("enabled") is not False:
        raise AssertionError("pose control must start disabled")

    postprocess = plan.get("postprocess", {})
    for stage in ("inpaint", "detailer", "upscale"):
        if postprocess.get(stage, {}).get("enabled") is not False:
            raise AssertionError(f"{stage} must start disabled")

    checkpoint = plan.get("checkpoint", {}).get("name")
    if checkpoint != "sd_xl_base_1.0.safetensors":
        raise AssertionError(f"unexpected checkpoint: {checkpoint}")

    print("[FREE:PLAN:STRUCTURE:OK]")
    print("[FREE:PLAN:CONTENT-EXACT:OK]")
    print("[FREE:PLAN:RENDERING-SEPARATED:OK]")
    print("[FREE:PLAN:PLACEHOLDERS:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
