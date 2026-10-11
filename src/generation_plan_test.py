from __future__ import annotations

import json
from pathlib import Path

from chat_contract import build_generation_request
from generation_bridge import build_generation_plan


ROOT = Path(__file__).resolve().parent.parent
INTENT_ROOT = ROOT / "intent"
PROFILES_ROOT = ROOT / "profiles"
CACHE_ROOT = ROOT / "cache"


def main() -> int:
    request = build_generation_request(
        "ゆらを白背景で正面立ち、服装と髪型はマスターと同じ、落ち着いた表情、2Dアニメ調で",
        "yura-working-master-g3",
        source="cli",
        dictionary_root=INTENT_ROOT,
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

    plan_path = build_generation_plan(ROOT, request, PROFILES_ROOT, CACHE_ROOT)
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
    )
    for fragment in required_fragments:
        if fragment not in positive:
            raise AssertionError(f"effective prompt missing fragment: {fragment}")

    context = plan.get("request_context")
    if not isinstance(context, dict):
        raise AssertionError("generation plan missing request_context")
    if context.get("request_id") != request["request_id"]:
        raise AssertionError("generation plan request_id mismatch")

    print("[GENERATION_PLAN:OK]")
    print(f"request_id={request['request_id']}")
    print(f"plan={plan_path}")
    print(f"intent={request['intent']}")
    print(f"effective_positive={positive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
