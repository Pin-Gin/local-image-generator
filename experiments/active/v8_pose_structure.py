"""v8.1 geometry-only import.

Mannequin RGB is used only for keypoint inference / SHA matching and optional
2D overlay. All images intended for final generation are *redrawn from Pose
JSON* (black background, colored joints/lines or coarse white silhouette).
A single 2D image is NOT a 3D rig, a depth map or verified ground contact.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
from v7_external_pose import prepare_external_pose, PoseImportError


class PoseStructureError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _coords(doc: dict[str, Any]) -> dict[str, dict[str, Any] | None]:
    points = doc.get('rendered_keypoints_2d')
    if not isinstance(points, dict):
        raise PoseStructureError('PROJECTED_KEYPOINTS_MISSING', 'No projected BODY_18 points')
    return points


def build_coarse_silhouette(doc: dict[str, Any], target: Path, *, width: int, height: int) -> dict[str, Any]:
    """Approximate keypoint envelope, not anatomical shape or RGB segmentation."""
    if width <= 0 or height <= 0 or width > 4096 or height > 4096:
        raise PoseStructureError('SILHOUETTE_DIMENSIONS_INVALID', f'{width}x{height}')
    pts = _coords(doc)
    core = ['neck', 'left_shoulder', 'right_shoulder', 'left_hip', 'right_hip',
            'left_knee', 'right_knee', 'left_ankle', 'right_ankle',
            'left_elbow', 'right_elbow', 'left_wrist', 'right_wrist']
    if any(pts.get(name) is None for name in core):
        raise PoseStructureError('SILHOUETTE_REQUIRED_JOINT_MISSING',
                                 ','.join(n for n in core if pts.get(n) is None))
    x = lambda name: float(pts[name]['x'])
    y = lambda name: float(pts[name]['y'])
    shoulder_width = math.dist((x('right_shoulder'), y('right_shoulder')),
                               (x('left_shoulder'), y('left_shoulder')))
    if not 0.02 * width < shoulder_width < width * 0.9:
        raise PoseStructureError('SILHOUETTE_SHOULDER_GEOMETRY_INVALID', str(shoulder_width))
    img = Image.new('L', (width, height), 0)
    d = ImageDraw.Draw(img)
    torso = [(x(i), y(i)) for i in ('right_shoulder', 'left_shoulder', 'left_hip', 'right_hip')]
    d.polygon(torso, fill=255)
    segments = (
        ('right_shoulder', 'right_elbow', .26), ('right_elbow', 'right_wrist', .20),
        ('left_shoulder', 'left_elbow', .26), ('left_elbow', 'left_wrist', .20),
        ('right_hip', 'right_knee', .44), ('right_knee', 'right_ankle', .29),
        ('left_hip', 'left_knee', .44), ('left_knee', 'left_ankle', .29),
    )
    for a, b, f in segments:
        radius = max(7, int(shoulder_width * f))
        d.line([(x(a), y(a)), (x(b), y(b))], fill=255, width=radius * 2)
        for name in (a, b):
            cx, cy = x(name), y(name)
            d.ellipse((cx-radius, cy-radius, cx+radius, cy+radius), fill=255)
    # Only a coarse head bounding oval. No facial/anatomical geometry invented.
    neck_y = y('neck')
    head_top = y('nose') - shoulder_width * .45 if pts.get('nose') else neck_y - shoulder_width*.85
    cx = x('neck')
    rad_x = shoulder_width * .34
    d.ellipse((cx-rad_x, head_top, cx+rad_x, neck_y), fill=255)
    target.parent.mkdir(parents=True, exist_ok=True)
    img.save(target)
    return {'path': str(target), 'sha256': sha256(target), 'source': 'BODY_18_PROJECTED_KEYPOINTS',
            'accuracy': 'COARSE_ENVELOPE_NOT_SEGMENTATION_OR_DEPTH', 'width': width, 'height': height}


def build_ground_contact(doc: dict[str, Any], destination: Path) -> dict[str, Any]:
    # 2D keypoints alone cannot assert physical contact (needs geometry/depth).
    declared = doc.get('ground_contact') if isinstance(doc.get('ground_contact'), dict) else {}
    sections: dict[str, Any] = {}
    for part in ('left_hand', 'right_hand', 'pelvis', 'left_foot', 'right_foot'):
        v = declared.get(part, 'UNKNOWN')
        if v not in ('UNKNOWN', 'CONTACT', 'NO_CONTACT'):
            raise PoseStructureError('GROUND_CONTACT_VALUE_INVALID', f'{part}: {v!r}')
        sections[part] = {'state': v, 'evidence': 'USER_DECLARED_UNVERIFIED' if part in declared else 'UNKNOWN_FROM_2D'}
    out = {'schema_version': '8.1', 'contact': sections,
           'depth_status': 'UNKNOWN_FROM_SINGLE_2D_IMAGE', 'rig_data': 'NOT_AVAILABLE',
           'automated_contact_verification': 'NOT_PERFORMED'}
    destination.write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return out


def build_pose_package(*, pose_image: Path, pose_json: Path | None, output_dir: Path,
                       comfy_url: str = 'http://127.0.0.1:8188',
                       width: int = 896, height: int = 960) -> tuple[dict[str, Any], Path]:
    """Prepare geometry-only image and metadata. RGB NEVER returned as final reference."""
    if not pose_image.is_file():
        raise PoseStructureError('POSE_IMAGE_MISSING', str(pose_image))
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        doc, openpose_path = prepare_external_pose(pose_image=pose_image, pose_json=pose_json,
            output_dir=output_dir, comfy_url=comfy_url, width=width, height=height)
    except PoseImportError as err:
        raise PoseStructureError(err.code, str(err)) from err
    # validate image dimensions and drawn BODY18 dependency.
    with Image.open(openpose_path) as im:
        if im.size != (width, height):
            raise PoseStructureError('OPENPOSE_CANVAS_MISMATCH', str(im.size))
        rgb = im.convert('RGB')
        if not rgb.getbbox():
            raise PoseStructureError('OPENPOSE_EMPTY', 'No keypoints drawn')
    silhouette = build_coarse_silhouette(doc, output_dir/'pose_only_silhouette.png', width=width, height=height)
    # Preserve explicit user-declared contacts separately from inferred keypoints.
    # v7 normalizes pose keypoints and intentionally does not carry arbitrary metadata.
    contacts_source: dict[str, Any] = {}
    if pose_json is not None:
        original_payload = json.loads(pose_json.read_text(encoding='utf-8'))
        if isinstance(original_payload, dict) and isinstance(original_payload.get('ground_contact'), dict):
            contacts_source['ground_contact'] = original_payload['ground_contact']
    contacts = build_ground_contact(contacts_source, output_dir/'ground_contact.json')
    digest = sha256(openpose_path)
    manifest = {
        'schema_version': '8.1',
        'source_type': doc.get('source_type'),
        'source_mannequin_sha256': sha256(pose_image),
        'source_image_hash_verified': doc.get('source_image_hash_verified'),
        'pose_json_origin': str(pose_json) if pose_json else 'DWPose_estimation',
        'pose_2d_path': str(output_dir/'external_pose.json'),
        'pose_only_openpose': {'path': str(openpose_path), 'sha256': digest, 'width': width, 'height': height},
        'pose_only_silhouette': silhouette,
        'ground_contact_path': str(output_dir/'ground_contact.json'),
        'ground_contact': contacts,
        'depth_status': 'UNKNOWN_FROM_SINGLE_2D_IMAGE',
        'review_status': doc['review_status'],
        'warnings': doc['warnings'],
        'mannequin_rgb_forwarding': False,
        'silhouette_used_for_generation': False,
        'geometry_conditioning': 'UNVERIFIED_UNTIL_RUNTIME_PREFLIGHT',
    }
    path = output_dir/'pose_package_v8_1.json'
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest, openpose_path
