from __future__ import annotations

from pathlib import Path

from intent_parser import parse_intent


ROOT = Path(__file__).resolve().parent.parent
INTENT_ROOT = ROOT / "intent"


def assert_case(text: str, expected: dict[str, object]) -> None:
    actual = parse_intent(text, INTENT_ROOT)
    for key, value in expected.items():
        if actual.get(key) != value:
            raise AssertionError(
                f"text={text!r} key={key!r} expected={value!r} actual={actual.get(key)!r} full={actual!r}"
            )
    print(f"[INTENT:CASE:OK] {text} -> {actual}")


def main() -> int:
    assert_case(
        "ゆらを白背景で正面立ちにして",
        {
            "status": "parsed",
            "character": "YURA",
            "background": "WHITE",
            "pose": "FRONT_STANDING",
        },
    )
    assert_case(
        "久遠ゆらを背景は白で正面を向いて立つ感じにして",
        {
            "status": "parsed",
            "character": "YURA",
            "background": "WHITE",
            "pose": "FRONT_STANDING",
        },
    )
    assert_case(
        "YURA を 白い背景 で 正面立ち姿 にして",
        {
            "status": "parsed",
            "character": "YURA",
            "background": "WHITE",
            "pose": "FRONT_STANDING",
        },
    )
    assert_case(
        "ゆらを白背景で正面立ち、服装と髪型はマスターと同じ、落ち着いた表情、2Dアニメ調で",
        {
            "status": "parsed",
            "character": "YURA",
            "outfit": "MASTER_REFERENCE",
            "background": "WHITE",
            "pose": "FRONT_STANDING",
            "expression": "CALM_NEUTRAL",
            "hair": "MASTER_REFERENCE",
            "rendering": "ANIME_2D",
        },
    )
    assert_case(
        "まだ辞書にない条件だけを指定する",
        {
            "status": "unparsed",
            "character": None,
            "outfit": None,
            "background": None,
            "pose": None,
            "expression": None,
            "hair": None,
            "rendering": None,
        },
    )
    print("[INTENT:OK]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
