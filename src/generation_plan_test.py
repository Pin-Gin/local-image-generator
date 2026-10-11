from __future__ import annotations

import json
from pathlib import Path

from chat_contract import MAX_SEED, build_generation_request
from generation_bridge import build_generation_plan


ROOT = Path(__file__).resolve().parent.parent
INTENT_ROOT = ROOT / "intent"
PROFILES_ROOT = ROOT / "profiles"
CACHE_ROOT = ROOT / "cache"
TEXT = "ゆらを白背景で正面立ち、服装と髪型はマスターと同じ、落ち着いた表情、2Dアニメ調で"
PROFILE = "yura-working-master-g3"


def assert_plan_seed(request: dict[str, object], expected_seed: int) -> Path:
    plan_path = build_generation_plan(ROOT, request, PROFILES_ROOT, CACHE_ROOT)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    actual_seed = plan["workflow"]["seed"]
    if actual_seed != expected_seed:
        raise AssertionError(f"seed mismatch expected={expected_seed} actual={actual_seed}")
    return plan_path


def main() -> int:
    request = build_generation_request(
        TEXT,
        PROFILE,
        source="cli",
        dictionary_root=INTENT_ROOT,
        seed_mode="FIXED",
        seed=12345,
    )
    expected_intent = {
        "character": "YURA",
        "outfit": "MASTER_REFERENCE",
        "background": "WHITE",
        "pose": "FRONT_STANDING",
        "expression": "CALM_NEUTRAL",
        "hair": "MASTER_REFERENCE",
        "rendering": "ANIME_2D",
    }
    for key, value in expected_intent.items():
        if request["intent"].get(key) != value:
            raise AssertionError(
                f"intent mismatch key={key} expected={value} actual={request['intent'].get(key)}"
            )

    plan_path = assert_plan_seed(request, 12345)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    positive = plan["prompt"]["positive"]

    required_fragments = (
        "preserve the referenced YURA character identity",
        "preserve the referenced outfit",
        "plain white background",
        "full body, front view, standing",
        "calm neutral expression",
        "preserve the referenced hair identity and hairstyle",
        "2D anime illustration",
        TEXT,
    )
    for fragment in required_fragments:
        if fragment not in positive:
            raise AssertionError(f"effective prompt missing fragment: {fragment}")

    context = plan.get("request_context")
    if not isinstance(context, dict):
        raise AssertionError("generation plan missing request_context")
    if context.get("request_id") != request["request_id"]:
        raise AssertionError("generation plan request_id mismatch")

    random_request = build_generation_request(
        TEXT,
        PROFILE,
        source="cli",
        dictionary_root=INTENT_ROOT,
        seed_mode="RANDOM",
    )
    random_seed = random_request["options"]["seed"]
    if not isinstance(random_seed, int) or random_seed < 0 or random_seed > MAX_SEED:
        raise AssertionError(f"invalid random seed: {random_seed}")
    assert_plan_seed(random_request, random_seed)

    freeform_text = "まだ辞書に登録していない青い傘を持たせる"
    freeform_request = build_generation_request(
        freeform_text,
        PROFILE,
        source="cli",
        dictionary_root=INTENT_ROOT,
        seed_mode="FIXED",
        seed=7,
    )
    if freeform_request["intent"]["status"] != "unparsed":
        raise AssertionError("freeform test must remain unparsed")
    freeform_plan_path = assert_plan_seed(freeform_request, 7)
    freeform_plan = json.loads(freeform_plan_path.read_text(encoding="utf-8"))
    if freeform_text not in freeform_plan["prompt"]["positive"]:
        raise AssertionError("freeform text was not passed to effective positive prompt")

    json_text = json.dumps(
        {
            "positive": "holding a blue umbrella, light rain",
            "negative": "closed eyes",
            "background": "school gate",
        },
        ensure_ascii=False,
    )
    json_request = build_generation_request(
        json_text,
        PROFILE,
        source="cli",
        dictionary_root=INTENT_ROOT,
        seed_mode="FIXED",
        seed=8,
    )
    if json_request["prompt_input"]["mode"] != "json":
        raise AssertionError("JSON input mode was not detected")
    json_plan_path = assert_plan_seed(json_request, 8)
    json_plan = json.loads(json_plan_path.read_text(encoding="utf-8"))
    if "holding a blue umbrella, light rain" not in json_plan["prompt"]["positive"]:
        raise AssertionError("JSON positive prompt was not applied")
    if "closed eyes" not in json_plan["prompt"]["negative"]:
        raise AssertionError("JSON negative prompt was not applied")

    arbitrary_json_text = json.dumps(
        {"background": "school rooftop", "pose": "sitting", "weather": "sunset"},
        ensure_ascii=False,
    )
    arbitrary_request = build_generation_request(
        arbitrary_json_text,
        PROFILE,
        source="cli",
        dictionary_root=INTENT_ROOT,
        seed_mode="FIXED",
        seed=9,
    )
    arbitrary_plan_path = assert_plan_seed(arbitrary_request, 9)
    arbitrary_plan = json.loads(arbitrary_plan_path.read_text(encoding="utf-8"))
    if "school rooftop" not in arbitrary_plan["prompt"]["positive"]:
        raise AssertionError("arbitrary JSON values were not converted into prompt text")

    print("[GENERATION_PLAN:OK]")
    print(f"request_id={request['request_id']}")
    print(f"plan={plan_path}")
    print(f"intent={request['intent']}")
    print(f"fixed_seed={request['options']['seed']}")
    print(f"random_seed={random_seed}")
    print(f"freeform_mode={freeform_request['prompt_input']['mode']}")
    print(f"json_mode={json_request['prompt_input']['mode']}")
    print(f"effective_positive={positive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
