"""v8.1 Qwen direct editor: image1 MASTER, image2 POSE-ONLY OpenPose,
image3 face/outfit reference board derived exclusively from MASTER.

No mannequin RGB in the final graph. Qwen uses image2 as a semantic reference,
NOT a hard positional constraint; v8_pipeline must enforce the mode gate.
"""
from __future__ import annotations

from typing import Any

from qwen2511_reference_pose_v6 import build_graph, ensure_graph
from v8_conditioning import validate_geometry_graph


class V8GraphError(ValueError):
    pass


def v8_edit_prompt(raw_text: str, *, pose_warnings: list[str] | None = None) -> str:
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise V8GraphError('USER_TEXT_MISSING')
    warnings = pose_warnings or []
    if any('ANKLES_OUTSIDE_KNEES' in warning for warning in warnings):
        warning_text = ('The supplied geometry has ankles outside the knees in 2D. '
                        'Do not silently correct it to the previously described feet-inward M-seat. ')
    else:
        warning_text = ''
    return (
        'Edit IMAGE 1, the master illustration of one adult woman. Only IMAGE 1 and IMAGE 3 '
        'are appearance references. Preserve the unique face, eyes, bob hair, facial proportions, '
        'body type, pale lace-trimmed camisole, shorts, colors, soft matte anime-realism style, '
        'and room where unchanged by the user. '
        'IMAGE 2 is a synthetic OpenPose 2D skeleton on black, generated from a pose JSON. '
        'Use ONLY its joint layout and facing direction. Never draw the colored lines, sticks, '
        'black background, point markers or any robotic joints, metallic limbs or mannequin surfaces. '
        'IMAGE 3 is a detail sheet cropped exclusively from IMAGE 1 for face, hair and garment details. '
        'It is not a different person or a new outfit. '
        + warning_text +
        'A single adult woman, no diagrams, no text, no mechanical accessories, no duplicate limbs. '
        'Do not change the original character identity or add garment layers. '
        'Do not automatically substitute crossed legs or lotus sitting for the pose guide. '
        'Use a full-figure, head-to-toes composition with camera sufficiently far back for both widely separated knees, '
        'ankles, feet and toes to be entirely inside the frame. Never crop either foot or cut off the knees, hands, or head. '
        'Respect the 2D skeleton spacing rather than zooming into the torso. Preserve the original camisole AND the shorts, '
        'including hem, lace, color, straps, and fabric; do not turn the shorts into underwear or add new furniture. '
        'Preserve IMAGE 1 facial structure, eye shape and matte soft anime rendering; do not enlarge or redesign the head. '
        'Note: the guide is 2D; its joint depths and true ground contacts are unknown. '
        'User instruction in Japanese: 「' + raw_text.strip() + '」'
    )


def build_direct_graph(master: str, pose_guide: str, detail_sheet: str,
                       raw_text: str, request: dict[str, Any], *, pose_warnings: list[str] | None = None,
                       model: str = 'qwen_image_edit_2511_int8_convrot.safetensors',
                       clip: str = 'qwen_2.5_vl_7b_fp8_scaled.safetensors',
                       vae: str = 'qwen_image_vae.safetensors',
                       steps: int = 20, cfg: float = 4.0, seed: int = 975311) -> dict[str,Any]:
    if not all(isinstance(s, str) and s.strip() for s in (master,pose_guide,detail_sheet)):
        raise V8GraphError('REFERENCE_ROLE_MISSING')
    if not pose_guide.startswith('V81_POSE_ONLY_') or not pose_guide.endswith('.png'):
        raise V8GraphError('POSE_GUIDE_ROLE_INVALID: expected derived V81_POSE_ONLY_*.png')
    graph = build_graph(master, pose_guide, raw_text, request, face_name=detail_sheet,
                        model=model, clip=clip, vae=vae, steps=steps, cfg=cfg, seed=seed,
                        filename_prefix='LOCAL_RAG_V81_REFERENCE_ONLY')
    graph['7']['inputs']['prompt'] = v8_edit_prompt(raw_text, pose_warnings=pose_warnings)
    graph['8']['inputs']['prompt'] = ''
    ensure_graph(graph)
    validate_direct_graph(graph)
    return graph


def validate_direct_graph(graph: dict[str, Any]) -> None:
    try:
        validate_geometry_graph(graph,
            master_name=graph['4']['inputs']['image'],
            pose_guide_name=graph['5']['inputs']['image'],
            detail_name=graph['17']['inputs']['image'])
    except (KeyError, TypeError) as exc:
        raise V8GraphError('REFERENCE_GRAPH_INCOMPLETE') from exc
