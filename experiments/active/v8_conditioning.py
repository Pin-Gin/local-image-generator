"""v8.1: evidence-based pose-conditioning compatibility gate for Qwen Edit 2511.

IMPORTANT: A valid TextEncodeQwenImageEditPlus.image2 port is a semantic image
reference, NOT a ControlNet/hard pose constraint. Do not infer compatibility
from the existence of generic ControlNetApplyAdvanced or similarly named nodes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

SUPPORTED = 'POSE_CONTROL_SUPPORTED'
REFERENCE_ONLY = 'POSE_CONTROL_REFERENCE_ONLY'
UNSUPPORTED = 'POSE_CONDITIONING_UNSUPPORTED'


class ConditioningError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class ConditioningAssessment:
    status: str
    model: str
    source_node: str
    evidence: str
    hard_pose_lock: bool
    mannequin_rgb_permitted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _input_names(node: Mapping[str, Any]) -> set[str]:
    spec = node.get('input', {})
    return set(spec.get('required', {})) | set(spec.get('optional', {}))


def assess_qwen_pose_control(info: Mapping[str, Any], model_name: str) -> ConditioningAssessment:
    """Evaluate live ComfyUI /object_info; do not guess a hard controller.

    No verified hard Qwen-Image-Edit-2511 pose-controller signature is registered
    in v8.1. If a compatible adapter becomes available, it must be reviewed
    and registered explicitly with evidence, not discovered by fuzzy node names.
    """
    if not isinstance(model_name, str) or 'qwen_image_edit_2511' not in model_name.lower():
        return ConditioningAssessment(UNSUPPORTED, str(model_name), '',
                                      'Target backend is not the evaluated Qwen-Image-Edit-2511 family.', False)
    enc = info.get('TextEncodeQwenImageEditPlus')
    if not isinstance(enc, dict):
        return ConditioningAssessment(UNSUPPORTED, model_name, '',
                                      'TextEncodeQwenImageEditPlus missing from live ComfyUI.', False)
    names = _input_names(enc)
    if not {'clip', 'prompt', 'image1', 'image2', 'image3', 'vae'} <= names:
        return ConditioningAssessment(UNSUPPORTED, model_name, 'TextEncodeQwenImageEditPlus',
                                      'Required multi-reference image ports unavailable.', False)
    return ConditioningAssessment(
        REFERENCE_ONLY, model_name, 'TextEncodeQwenImageEditPlus.image2',
        'IMAGE2 is encoded as image/reference latent. It does not force joint coordinates. '
        'No model-compatible hard pose ControlNet verified for this deployment.', False)


def enforce_pose_control(assessment: ConditioningAssessment, *, allow_reference_only: bool = False) -> None:
    if assessment.status == SUPPORTED and assessment.hard_pose_lock:
        return
    if assessment.status == REFERENCE_ONLY and allow_reference_only:
        return
    if assessment.status == REFERENCE_ONLY:
        raise ConditioningError('POSE_CONTROL_NOT_HARD',
            'Qwen 2511 supports only semantic image reference in this workflow. '
            'Strict pose control is unavailable. Explicit --allow-reference-only is required for a diagnostic experiment.')
    raise ConditioningError(UNSUPPORTED, assessment.evidence)


def validate_geometry_graph(graph: dict[str, Any], *, master_name: str, pose_guide_name: str,
                            detail_name: str) -> None:
    """Fail closed if the final Comfy graph can read a mannequin RGB source.

    The producer must construct pose_guide_name from an OpenPose-only render.
    Graph validation verifies its role and explicit lineage; it cannot prove
    image pixels at an arbitrary remote Comfy filename without its source SHA.
    """
    if not isinstance(pose_guide_name, str) or not pose_guide_name.startswith('V81_POSE_ONLY_') or not pose_guide_name.endswith('.png'):
        raise ConditioningError('POSE_GUIDE_ROLE_INVALID', 'Image2 must be a generated V81_POSE_ONLY_...png asset')
    if not all(isinstance(x, str) and x for x in (master_name, pose_guide_name, detail_name)):
        raise ConditioningError('REFERENCE_ROLE_MISSING', 'All image roles must be named')
    if len({master_name, pose_guide_name, detail_name}) != 3:
        raise ConditioningError('REFERENCE_COLLISION', 'Image roles must be distinct')
    forbidden = {'CheckpointLoaderSimple', 'ControlNetApplyAdvanced', 'ControlNetLoader', 'EmptyLatentImage'}
    for node in graph.values():
        if node['class_type'] in forbidden:
            raise ConditioningError('LEGACY_SDXL_STAGE_PRESENT', node['class_type'])
    expected = {'4': master_name, '5': pose_guide_name, '17': detail_name}
    loads = {nid: node for nid, node in graph.items() if node['class_type'] == 'LoadImage'}
    if set(loads) != set(expected):
        raise ConditioningError('UNEXPECTED_IMAGE_SOURCE', f'LoadImage node roles are {sorted(loads)}')
    for nid, name in expected.items():
        if graph[nid]['inputs'].get('image') != name:
            raise ConditioningError('REFERENCE_ROLE_MISMATCH', f'node {nid} not expected source')
    for nid in ('7', '8'):
        node = graph.get(nid, {})
        if node.get('class_type') != 'TextEncodeQwenImageEditPlus':
            raise ConditioningError('QWEN_ENCODER_MISSING', nid)
        inputs = node.get('inputs', {})
        if [inputs.get('image1'), inputs.get('image2'), inputs.get('image3')] != [['6', 0], ['5', 0], ['17', 0]]:
            raise ConditioningError('QWEN_REFERENCE_LINK_INVALID', nid)
    if graph.get('6', {}).get('inputs', {}).get('image') != ['4', 0]:
        raise ConditioningError('MASTER_BASE_LINK_INVALID', 'master not connected to base scaler')
    if graph.get('13', {}).get('inputs', {}).get('pixels') != ['6', 0]:
        raise ConditioningError('MASTER_LATENT_INVALID', 'encoded master not used')
    if graph.get('14', {}).get('inputs', {}).get('latent_image') != ['13', 0]:
        raise ConditioningError('MASTER_LATENT_INVALID', 'sampler does not use the master')
