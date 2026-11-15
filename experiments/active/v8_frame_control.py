"""v8.2: explicit image-space framing for external BODY_18 pose.

The foot-tip anchors are manually estimated 2D landmarks, NOT recovered 3D
coordinates, and never enter the BODY_18 pose as fake ankles. This module
reprojects the BODY_18 guide using a wider figure bounding box so the complete
head and both feet fit inside a canvas of the master image's aspect ratio.

ComfyUI/Qwen's image2 is REFERENCE-ONLY; neither this module nor the output JSON
claims that generated toes or pose are automatically verified.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
from v7_external_pose import JOINTS, BONES, COLORS


class FramingError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def match_master_canvas(master_image: Path, *, width: int = 768, multiple: int = 64,
                        min_height: int = 512, max_height: int = 2048) -> tuple[int, int]:
    """Choose an integer canvas matching the master aspect, preserving proportional scaling."""
    if not master_image.is_file():
        raise FramingError('MASTER_MISSING', str(master_image))
    with Image.open(master_image) as img:
        mw, mh = img.size
    if not isinstance(width, int) or width < 512 or width > 1536 or width % multiple:
        raise FramingError('POSE_CANVAS_INVALID', str(width))
    target = int(round((width * mh / mw) / multiple) * multiple)
    if not min_height <= target <= max_height:
        raise FramingError('MASTER_ASPECT_UNSUPPORTED', f'{mw}x{mh} -> {width}x{target}')
    return width, target


def load_frame_anchors(path: Path | None, *, source_sha256: str,
                       source_width: int, source_height: int) -> tuple[dict[str,dict[str,Any]],list[str]]:
    """Optional 2D anchors; no hallucinated toe positions if the sidecar is absent."""
    if path is None:
        return {}, ['FOOT_LANDMARKS_UNKNOWN: BODY_18 stops at ankles; toe visibility unverified']
    if not path.is_file():
        raise FramingError('FRAME_ANCHORS_MISSING', str(path))
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema_version') != 'v8.2.frame_anchors.v1':
        raise FramingError('FRAME_SCHEMA_INVALID', 'expected v8.2.frame_anchors.v1')
    if data.get('source_image_sha256') != source_sha256:
        raise FramingError('FRAME_SOURCE_HASH_MISMATCH', 'anchors do not belong to mannequin image')
    if data.get('source_dimensions') != {'width': source_width, 'height': source_height}:
        raise FramingError('FRAME_SOURCE_DIMENSIONS_MISMATCH', 'anchors dimensions do not match mannequin image')
    entries = data.get('anchors')
    if not isinstance(entries, dict) or set(entries) != {'head_top', 'right_toe', 'left_toe'}:
        raise FramingError('FRAME_ANCHORS_INVALID', 'expected head_top, right_toe, left_toe')
    anchors = {}
    for name, point in entries.items():
        if not isinstance(point, dict):
            raise FramingError('FRAME_ANCHORS_INVALID', name)
        x, y = point.get('x'), point.get('y')
        confidence = point.get('confidence')
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                   for v in (x, y, confidence)):
            raise FramingError('FRAME_ANCHORS_INVALID', f'{name}: non-numeric')
        if not (0 <= x < source_width and 0 <= y < source_height and 0 < confidence <= 1):
            raise FramingError('FRAME_ANCHORS_INVALID', f'{name}: out of bounds')
        if point.get('provenance') not in ('manual_image_estimate', 'user_annotation', '2d_detector_estimate'):
            raise FramingError('FRAME_PROVENANCE_MISSING', name)
        anchors[name] = point
    warnings = ['FOOT_ANCHORS_2D_UNVERIFIED: toe/head landmarks are 2D estimates, not 3D or validated contacts']
    if min(anchors['right_toe']['x'], anchors['left_toe']['x']) >= max(anchors['right_toe']['x'], anchors['left_toe']['x']):
        raise FramingError('FRAME_ANCHORS_INVALID', 'toes not distinct')
    return anchors, warnings


def reframe_external_guide(*, output_dir: Path, mannequin: Path,
                           master: Path, anchors_json: Path | None,
                           canvas_width: int = 768, canvas_height: int | None = None,
                           margin: float = 0.09) -> dict[str,Any]:
    """Create a master-aspect guide and traceable 2D overlay without raw mannequin pixels.

    Must be called *after* build_pose_package created external_pose.json.
    Returns the new guide path; callers must replace the old guide in image2.
    """
    if not 0.05 <= margin <= 0.20:
        raise FramingError('FRAME_MARGIN_INVALID', str(margin))
    doc_path = output_dir/'external_pose.json'
    doc = json.loads(doc_path.read_text(encoding='utf-8'))
    sw, sh = doc['source_dimensions']['width'], doc['source_dimensions']['height']
    with Image.open(mannequin) as m:
        if m.size != (sw, sh):
            raise FramingError('POSE_SOURCE_DIMENSIONS_MISMATCH', str(m.size))
    cw, ch = match_master_canvas(master, width=canvas_width)
    if canvas_height is not None:
        if abs((cw/canvas_height)/(cw/ch)-1) > .035:
            raise FramingError('FRAME_ASPECT_MISMATCH','override differs from master aspect')
        ch = canvas_height
    joints = doc['keypoints']
    required = ('neck','left_shoulder','right_shoulder','left_hip','right_hip',
                'left_knee','right_knee','left_ankle','right_ankle')
    if any(joints.get(j) is None for j in required):
        raise FramingError('FRAME_REQUIRED_JOINT_MISSING', ','.join(j for j in required if joints.get(j) is None))
    anchors, warnings = load_frame_anchors(anchors_json,
                                          source_sha256=digest(mannequin), source_width=sw, source_height=sh)
    values = [p for p in joints.values() if p is not None] + list(anchors.values())
    minx, maxx = min(p['x'] for p in values), max(p['x'] for p in values)
    miny, maxy = min(p['y'] for p in values), max(p['y'] for p in values)
    if maxx - minx < 1 or maxy - miny < 1:
        raise FramingError('FRAME_DEGENERATE', 'figure has no extent')
    scale = min((1-2*margin)*cw/(maxx-minx), (1-2*margin)*ch/(maxy-miny))
    ox = (cw - scale*(maxx-minx))/2-scale*minx
    oy = (ch - scale*(maxy-miny))/2-scale*miny
    tx = lambda p: {'x':round(p['x']*scale+ox,2),'y':round(p['y']*scale+oy,2),
                    'confidence':p.get('confidence'), 'observability':p.get('observability',p.get('provenance'))}
    proj = {k: tx(v) if v else None for k,v in joints.items()}
    aproj = {k: tx(v) for k,v in anchors.items()}
    min_margin = min([min(p['x'],cw-p['x'],p['y'],ch-p['y']) for p in list(proj.values())+list(aproj.values()) if p])
    if min_margin < min(cw,ch)*margin-1.0:
        raise FramingError('FRAME_CLIPPING', f'projected endpoint margin {min_margin:.2f}px')

    image = Image.new('RGB',(cw,ch),(0,0,0))
    draw = ImageDraw.Draw(image)
    line_w = max(3,round(min(cw,ch)*.006))
    for idx,(a,b) in enumerate(BONES):
        pa,pb = proj[JOINTS[a]],proj[JOINTS[b]]
        if pa and pb:
            draw.line([(pa['x'],pa['y']),(pb['x'],pb['y'])],
                      fill=COLORS[idx % len(COLORS)], width=line_w)
    for i,name in enumerate(JOINTS):
        p = proj[name]
        if p:
            r=line_w*1.15
            draw.ellipse((p['x']-r,p['y']-r,p['x']+r,p['y']+r),fill=COLORS[i],outline='white',width=1)
    guide = output_dir/'external_openpose_fullframe.png'
    image.save(guide)
    # Foot-tip goals only in an auxiliary QA image. No unknown joint slots invented.
    overlay = image.copy()
    od = ImageDraw.Draw(overlay)
    for tag,pt in aproj.items():
        x,y=pt['x'],pt['y']
        od.ellipse((x-9,y-9,x+9,y+9),outline=(255,255,255),width=3)
        od.text((x+12,y-12),tag,fill=(255,255,255))
    overlay_path = output_dir/'frame_landmarks_review.png'
    overlay.save(overlay_path)
    layout = {
        'schema_version':'v8.2.full_frame.v1', 'master_canvas':{'width':cw,'height':ch},
        'source_image_dimensions':{'width':sw,'height':sh},
        'pose_guide_path':str(guide),'pose_guide_sha256':digest(guide),
        'frame_review_path':str(overlay_path),'frame_review_sha256':digest(overlay_path),
        'frame_anchors':aproj,'projected_keypoints_2d':proj,
        'bbox_source':{'left':minx,'top':miny,'right':maxx,'bottom':maxy},
        'uniform_scale':round(scale,6), 'minimum_boundary_distance_px':round(min_margin,2),
        'skeleton_frame_margin':margin, 'master_aspect_ratio':round(cw/ch,5),
        'source_pose_aspect_ratio':round(sw/sh,5),
        'foot_toes_present_in_guide':False,
        'toe_targets_available_for_review':bool(anchors),
        'foot_visibility_in_generated_image':'NOT_EVALUATED',
        'pose_control_mode':'QWEN_IMAGE2_REFERENCE_ONLY',
        'body18_joint_positions_modified':False,
        'warnings':warnings
    }
    manifest_path = output_dir/'frame_alignment_v8_2.json'
    manifest_path.write_text(json.dumps(layout,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Do not rewrite the original source keypoints. Save the projected coordinate system separately.
    return layout
