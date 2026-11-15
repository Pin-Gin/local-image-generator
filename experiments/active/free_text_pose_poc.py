"""Phase 2 PoC: one reference image + Japanese text -> OpenPose guide -> ComfyUI.

This diagnostic deliberately does not modify the production engine. It can
compile one supported pose without local LLM inference or additional pose images.
Only the `--generate` flag invokes the existing ComfyUI generation pipeline.
This is not a general-pose solver or a validated quality assurance system.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
POSE_MODEL = "SDXL/controlnet-openpose-sdxl-1.0/diffusion_pytorch_model.safetensors"

# Coordinate frame: normalized X,Y within the full PNG canvas.
# OpenPose COCO-18: nose,neck,R shoulder/elbow/wrist,L shoulder/elbow/wrist,
# R hip/knee/ankle,L hip/knee/ankle,R eye,L eye,R ear,L ear.
# The template is a *2D guide*, not a calibrated 3D rig or proof of 7.3 heads.
COCO_18 = {
    "arms_out": [
        (.50,.105),(.50,.235),(.405,.259),(.265,.256),(.125,.252),
        (.595,.259),(.735,.256),(.875,.252),(.462,.52),(.451,.735),
        (.449,.918),(.538,.52),(.549,.735),(.551,.918),
        (.477,.103),(.523,.103),(.460,.115),(.540,.115),
    ],
    "seated_m": [
        (.500,.180),(.500,.295),(.380,.330),(.345,.470),(.390,.590),
        (.620,.330),(.655,.470),(.610,.590),(.452,.675),(.195,.655),
        (.350,.845),(.548,.675),(.805,.655),(.650,.845),
        (.473,.179),(.527,.179),(.447,.185),(.553,.185),
    ],
    "arms_down": [
        (.50,.105),(.50,.235),(.405,.259),(.393,.397),(.405,.521),
        (.595,.259),(.607,.397),(.595,.521),(.462,.52),(.451,.735),
        (.449,.918),(.538,.52),(.549,.735),(.551,.918),
        (.477,.103),(.523,.103),(.460,.115),(.540,.115),
    ],
}
BONES = [(1,2),(2,3),(3,4),(1,5),(5,6),(6,7),(1,8),(8,9),(9,10),
         (1,11),(11,12),(12,13),(1,0),(0,14),(14,16),(0,15),(15,17),
         (8,11)]
COLORS = [(255,0,0),(255,85,0),(255,170,0),(255,255,0),(170,255,0),
          (85,255,0),(0,255,0),(0,255,85),(0,255,170),(0,255,255),
          (0,170,255),(0,85,255),(0,0,255),(85,0,255),(170,0,255),
          (255,0,255),(255,0,170)]

class PocError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as inp:
        for block in iter(lambda: inp.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def classify_request(text: str) -> dict[str, Any]:
    """Lossless text retention; narrow, explicitly supported pose vocabulary.

    Scenes and attire are extracted separately from safety decisions. The
    demonstration makes NO claim to have performed a safety review.
    """
    if not isinstance(text, str) or not text.strip():
        raise PocError('PARSE_ERROR', '日本語指示文が空です')
    raw = text.strip()
    # Pose extraction precedes safety classification. This is an anatomy-only
    # interpretation, not approval to generate every possible scene.
    if re.search(r'(背面|後ろ姿|横顔|後方から|横から|斜め後)', raw):
        raise PocError('CAMERA_UNSUPPORTED', '正面以外のカメラは、この最小実証には未実装です')
    m_legs = bool(re.search(r'(?:[MmＭｍ]字|エム字)', raw))
    seated = bool(re.search(r'(?:座|坐)', raw))
    is_m_sit = m_legs and seated
    is_standing = bool(re.search(r'立(っ|つ|ち|た|て|姿)|直立', raw))
    # Explicit unimplemented poses must not silently become a supported pose.
    unsupported = [
        '四つん這い','四つ這い','うつ伏せ','体育座り','あぐら','しゃが',
        '足を組','片膝','寝そべ','仰向け','振り返','ストレッチ',
    ]
    if any(word in raw for word in unsupported):
        raise PocError('POSE_UNSUPPORTED', '指定ポーズの3D/2D空間化は、この最小実証には未実装です')
    if is_m_sit and is_standing:
        raise PocError('POSE_CONFLICT', '座位と立位が同時に指定されています')
    is_arms_out = bool(re.search(r'(両腕|両手|腕|手).{0,12}(左右|横|水平).{0,8}(広げ|伸ば)', raw)) or bool(
        re.search(r'(両腕|両手|腕|手).{0,12}(広げ|伸ば).{0,8}(左右|横|水平)', raw))
    if is_m_sit:
        pose_id = 'seated_m'
    elif seated or m_legs:
        raise PocError('POSE_UNSUPPORTED', '座位はM字状に開く指定のある姿勢のみ実装済みです')
    elif is_arms_out and is_standing:
        pose_id = 'arms_out'
    elif is_standing:
        pose_id = 'arms_down'
    else:
        raise PocError('POSE_UNSUPPORTED', '対応ポーズは立位2種と、正面座位のM字状の脚姿勢です')
    scene = None
    for key, value in [('シャワー','bathroom_shower'),('プール','poolside'),
                       ('室内','interior'),('公園','park')]:
        if key in raw:
            scene = value
            break
    clothing = None
    for key, value in [('水着','swimsuit'),('ワンピース','one_piece_dress'),
                       ('ジャージ','tracksuit')]:
        if key in raw:
            clothing = value
            break
    # Only explicitly tested sentences are allowed through --generate. Extracted
    # fields outside this grammar remain PARTIAL, not quietly discarded.
    clean = re.sub(r'[\s。．！!、，,]+', '', raw)
    standing_grammar = bool(re.fullmatch(
        r'(?:成人女性|女性)(?:が|は)?(?:正面を向き)?'
        r'(?:両手を左右に広げて立つ|両腕を横に伸ばして立つ|立つ)', clean
    ))
    m_seated_grammar = bool(re.fullmatch(
        r'(?:成人女性|女性)(?:が|は)?(?:真正面|正面)を向き'
        r'(?:座っている状態で|座った状態で|座って|座り)'
        r'(?:足を)?(?:M字|ｍ字|Ｍ字|エム字)に開いて'
        r'(?:微笑んでいる|微笑む|笑っている)', clean
    ))
    complete_for_poc = standing_grammar or m_seated_grammar
    expression = 'soft_smile' if re.search(r'(微笑|ほほえ|笑顔|笑って)', raw) else None
    pose_geometry = (
        {'posture': 'seated', 'legs': 'knees_bent_outward_feet_inward',
         'support_surface': 'UNSPECIFIED', 'depth': 'UNRESOLVED_2D_ONLY'}
        if pose_id == 'seated_m'
        else {'posture': 'standing', 'legs': 'straight', 'support_surface': 'feet'}
    )
    # The scene, seat support, outfit and face style are never silently modified.
    return {
        'schema_version': 1,
        'raw_text': raw,
        'identity': {'master_authority': True, 'body_heads_target': 7.3},
        'pose': {'id': pose_id, 'view': 'front', 'method': 'coco18_template_v0', 'geometry': pose_geometry},
        'deltas': {'clothing': clothing, 'scene': scene, 'expression': expression},
        'safety': {'status': 'NOT_EVALUATED', 'note': '情報抽出は安全判定ではない'},
        'interpretation': {'coverage': 'COMPLETE_FOR_POC' if complete_for_poc else 'PARTIAL', 'unresolved_text_retained': True},
    }


def render_pose(pose_id: str, output_path: Path, width: int = 768, height: int = 1344) -> None:
    if pose_id not in COCO_18:
        raise PocError('POSE_UNSUPPORTED', pose_id)
    image = Image.new('RGB', (width, height), (0,0,0))
    draw = ImageDraw.Draw(image)
    points = [(round(x*width),round(y*height)) for x,y in COCO_18[pose_id]]
    thickness = max(3, width//120)
    for i, (a,b) in enumerate(BONES):
        draw.line([points[a],points[b]], fill=COLORS[i % len(COLORS)], width=thickness)
    radius = max(3, width//140)
    for i, (x,y) in enumerate(points):
        color = COLORS[i % len(COLORS)]
        draw.ellipse((x-radius,y-radius,x+radius,y+radius), fill=color)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def content_prompt(request: dict[str,Any]) -> str:
    pose_id = request['pose']['id']
    pose_en = {
        'arms_out': 'standing with both arms extended horizontally',
        'arms_down': 'standing with arms relaxed',
        'seated_m': (
            'sitting upright facing front, knees flexed and opened outward symmetrically, '
            'both feet positioned inward relative to the knees, M-shaped bent-leg seated posture'
        ),
    }[pose_id]
    parts = [
        'single adult woman, full body', pose_en, 'front view',
        'same subject identity, face, hairstyle, hair color and body proportions as reference image',
        'natural anatomical proportions, preserve reference clothing unless explicitly changed',
        'soft matte anime realism, delicate semi-real anime shading, natural soft light',
    ]
    if request['deltas'].get('expression') == 'soft_smile':
        parts.append('gentle natural smile')
    attire = request['deltas']['clothing']
    scene = request['deltas']['scene']
    if attire:
        parts.append({'swimsuit':'wearing swimsuit','one_piece_dress':'wearing one-piece dress',
                      'tracksuit':'wearing tracksuit'}[attire])
    if scene:
        parts.append({'bathroom_shower':'bathroom shower environment',
                      'poolside':'poolside environment','interior':'indoor room',
                      'park':'public park'}[scene])
    return ', '.join(parts)


def generate(root: Path, master: Path, pose_path: Path, request: dict[str,Any], out: Path, seed: int) -> dict[str,Any]:
    sys.path.insert(0, str(root / 'src'))
    from comfyui_client import run_workflow_and_download, upload_input_image
    from free_compiler import compile_free_generation
    from free_generation_plan import build_free_generation_engine_plan
    from model_catalog import resolve_project_checkpoint

    config = json.loads((root/'config/app.example.json').read_text(encoding='utf-8'))
    profile = json.loads((root/'profiles/free_sdxl_v1.json').read_text(encoding='utf-8'))
    rendering = json.loads((root/'shared/rendering/matte_dimensional_anime.json').read_text(encoding='utf-8'))
    base_url = config['comfyui']['base_url']

    # Diagnostic override only: the master is Matte Soft Anime Realism,
    # not the repository's generic Matte Dimensional Anime profile.
    rendering = copy.deepcopy(rendering)
    rendering['prompt']['positive'] = (
        'matte soft anime realism, smooth delicate illustrated skin, '
        'subtle natural volume, airy soft lighting, gently modeled anime face, '
        'soft clean hair strands, restrained contours, not photorealistic'
    )
    rendering['prompt']['negative'] = (
        'photoreal, live action, plastic CGI, PBR, harsh hard-edged shadows, '
        'heavy comic outlines, flat anime cel-shading'
    )
    rendering['lora']['enabled'] = False
    workflow = copy.deepcopy(profile['workflow'])
    workflow.update({'checkpoint': resolve_project_checkpoint(root, rendering['generation']['checkpoint']),
                     'steps': 28, 'cfg': rendering['generation']['cfg'],
                     'sampler_name': rendering['generation']['sampler_name'],
                     'scheduler': rendering['generation']['scheduler'], 'denoise':1.0})

    timeout = max(30, float(config['comfyui'].get('timeout_seconds',5)))
    gen_timeout = float(config['comfyui'].get('generation_timeout_seconds',180))
    master_remote = upload_input_image(base_url, master,
        remote_name='POC_MAIN_'+hash_file(master)[:12]+master.suffix.lower(),timeout_seconds=timeout)
    pose_remote = upload_input_image(base_url, pose_path,
        remote_name='POC_POSE_'+hash_file(pose_path)[:12]+'.png',timeout_seconds=timeout)
    # Existing engine contract only supports backend='dwpose'. Generate the
    # graph with the existing validator, then perform a *diagnostic-only* graph
    # patch: direct OpenPose RGB image -> ControlNet, bypassing DWPose detection.
    pose_control = {
        'enabled': True, 'backend':'dwpose',
        'source': {'local_path':str(pose_path), 'input_name':pose_remote, 'sha256':hash_file(pose_path)},
        'preprocessor': {'detect_hand':False, 'detect_body':True, 'detect_face':False,
                         'resolution':1024, 'bbox_detector':'yolox_l.onnx',
                         'pose_estimator':'dw-ll_ucoco_384_bs5.torchscript.pt',
                         'scale_stick_for_xinsr_cn':True},
        'controlnet': {'model':POSE_MODEL,'strength':1.20,
                       'start_percent':0.0,'end_percent':1.0},
    }
    plan = build_free_generation_engine_plan(
        content_positive=content_prompt(request),
        content_negative='different person, altered hairstyle, altered face, incorrect anatomy, extra limbs',
        workflow=workflow, shared_rendering=rendering,
        lineart_profile=None, lineart_enabled=False,
        pose_control=pose_control,
    )
    compiled=compile_free_generation(root,plan,out/'cache',seed=seed,
                                     filename_prefix='LOCAL_RAG_TEXT_POSE_POC')
    graph=copy.deepcopy(compiled.compiled_workflow)
    assert graph['23']['inputs']['image'] == ['21',0], 'GRAPH_COMPATIBILITY_ERROR: pose graph changed'
    graph['23']['inputs']['image']=['20',0]
    del graph['21']
    graph['2']['inputs'].update({'width':768,'height':1344,'batch_size':1})
    model_ref=graph['7']['inputs']['model']
    graph['30']={'class_type':'LoadImage','inputs':{'image':master_remote}}
    graph['40']={'class_type':'IPAdapterUnifiedLoader',
                 'inputs':{'model':model_ref,'preset':'PLUS (high strength)'}}
    graph['41']={'class_type':'IPAdapterAdvanced',
        'inputs':{'model':['40',0],'ipadapter':['40',1], 'image':['30',0],
                  'weight':0.75,'weight_type':'linear','combine_embeds':'concat',
                  'start_at':0.30,'end_at':1.0,
                  'embeds_scaling':'K+mean(V) w/ C penalty'}}
    graph['7']['inputs']['model']=['41',0]
    # v2 identity architecture: keep full reference but apply an independently
    # cropped, spatially masked head reference. Never silently fall back.
    from identity_ref_v2 import make_references, compose_graph, require_nodes_available
    require_nodes_available(base_url)
    reference = make_references(master, request['pose']['id'], out/'identity_v2', width=768, height=1344)
    head_path = Path(reference['head_reference_path'])
    mask_path = Path(reference['target_head_mask_path'])
    head_remote = upload_input_image(base_url, head_path,
        remote_name='POC_HEAD_'+hash_file(head_path)[:12]+'.png', timeout_seconds=timeout)
    mask_remote = upload_input_image(base_url, mask_path,
        remote_name='POC_HEAD_MASK_'+hash_file(mask_path)[:12]+'.png', timeout_seconds=timeout)
    graph = compose_graph(graph, head_remote=head_remote, mask_remote=mask_remote)
    (out/'identity_v2'/'reference_meta.json').write_text(
        json.dumps(reference, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (out/'compiled_workflow.json').write_text(json.dumps(graph,indent=2,ensure_ascii=False),encoding='utf-8')
    result=run_workflow_and_download(base_url=base_url,workflow=graph,
        output_dir=out/'images',request_timeout_seconds=timeout,
        generation_timeout_seconds=gen_timeout)
    return {'status':'GENERATED_UNVERIFIED','output_path':str(result.output_path),
            'sha256':hash_file(result.output_path),'prompt_id':result.prompt_id,
            'quality_qa':'NOT_PERFORMED','identity_qa':'NOT_PERFORMED',
            'rendering_qa':'NOT_PERFORMED', 'identity_conditioning':'master-and-head-mask-v2',
            'reference':reference, 'pose_backend':'direct_openpose_rgb_controlnet'}


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description='One master + Japanese text PoC (diagnostic)')
    parser.add_argument('--master',type=Path,required=True)
    parser.add_argument('--text',required=True)
    parser.add_argument('--generate',action='store_true',help='invoke local ComfyUI; default is dry run')
    parser.add_argument('--seed',type=int,default=975311)
    parser.add_argument('--out-root',type=Path,default=ROOT/'outputs/experiments/text_pose_poc')
    args=parser.parse_args(argv)
    out=None
    try:
        if not args.master.is_file() or args.master.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise PocError('INPUT_ERROR','参照マスター画像が存在しないか形式が不正です')
        if args.seed < 0:
            raise PocError('INPUT_ERROR','seed must be non-negative')
        req=classify_request(args.text)
        if args.generate and req['interpretation']['coverage'] != 'COMPLETE_FOR_POC':
            raise PocError('UNRESOLVED_SEMANTICS',
                           'この実証の文法外の指定が含まれるため、黙って無視せず生成を停止しました')
        timestamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        out=args.out_root.resolve()/timestamp
        out.mkdir(parents=True,exist_ok=False)
        pose_file=out/'openpose_guide.png'
        render_pose(req['pose']['id'],pose_file)
        record={
            'schema_version':1,'phase':'poc','master_path':str(args.master.resolve()),
            'master_sha256':hash_file(args.master),'request':req,
            'pose_image':str(pose_file),'pose_image_sha256':hash_file(pose_file),
            'master_image_7_3_heads':'USER_SPECIFIED_NOT_VISUALLY_VERIFIED',
            'target_style':'Matte Soft Anime Realism',
            'stage':'DRY_RUN_COMPLETE','model_license_review':'NOT_COMPLETED',
            'execution_environment':'NOT_CHECKED', 'visual_qa':'NOT_PERFORMED',
        }
        if args.generate:
            record['generation']=generate(ROOT,args.master.resolve(),pose_file,req,out,args.seed)
            record['stage']='GENERATED_UNVERIFIED'
        (out/'manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('[TEXT-POSE-POC:'+record['stage']+']')
        print('[TEXT-POSE-POC:OUTPUT] '+str(out))
        return 0
    except PocError as exc:
        print(json.dumps({'status':'FAIL','error_type':exc.code,'message':str(exc)},ensure_ascii=False),file=sys.stderr)
        return 2
    except Exception as exc:
        # Never replace the failed pose/identity/renderer with a different input.
        if out:
            (out/'failure.json').write_text(json.dumps({'status':'FAIL','error_type':'RUNTIME_ERROR',
                'message':str(exc)},ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'status':'FAIL','error_type':'RUNTIME_ERROR','message':str(exc)},ensure_ascii=False),file=sys.stderr)
        return 3

if __name__=='__main__':
    raise SystemExit(main())
