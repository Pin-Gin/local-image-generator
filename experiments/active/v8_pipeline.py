"""v8.1: separation of appearance and geometry in an experimental Qwen backend.

Mannequin RGB is used ONLY by geometry extraction / optional DWPose; the
final image editing workflow sees a skeleton reconstructed from 2D JSON.
No unverified hard pose-controller is claimed to be supported.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
for d in (ROOT/'src', ROOT/'experiments'/'active'):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

from v7_references import make_reference_bundle, sha256
from v7_geometry import request_from_text
from v7_quality import review_sheet
from v8_pose_structure import build_pose_package, PoseStructureError
from v8_conditioning import (assess_qwen_pose_control, enforce_pose_control,
                             ConditioningError, REFERENCE_ONLY)
from v8_direct_pose_edit import build_direct_graph, validate_direct_graph
from v8_frame_control import reframe_external_guide, match_master_canvas, FramingError, digest as frame_digest
from qwen2511_reference_pose_v6 import fetch_object_info, validate_runtime, ui_graph


class V8Error(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def previous_master_name(source: Path) -> str:
    data = json.loads(source.read_text(encoding='utf-8'))
    try:
        node = data['30']
        if node['class_type'] != 'LoadImage':
            raise KeyError('30 must be LoadImage')
        name = node['inputs']['image']
        if not isinstance(name, str) or not name.strip():
            raise ValueError('name missing')
        return name
    except (KeyError, TypeError, ValueError) as e:
        raise V8Error('SOURCE_INCOMPATIBLE','Legacy source graph must contain master LoadImage node 30') from e


def verify_source_master(local: Path, remote_name: str) -> None:
    if not remote_name.startswith('POC_MAIN_'):
        raise V8Error('MASTER_SOURCE_UNKNOWN','Legacy master lacks content-addressed POC_MAIN_ filename; use --master')
    prefix = remote_name[len('POC_MAIN_'):].split('.',1)[0]
    if len(prefix) < 8 or not sha256(local).startswith(prefix):
        raise V8Error('MASTER_SOURCE_MISMATCH','Downloaded master does not match the saved hash')


def make_cli_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description='v8.1 geometry/appearance separation; no mannequin RGB in Qwen graph')
    s = p.add_mutually_exclusive_group(required=True)
    s.add_argument('--source',type=Path,help='legacy compiled_workflow.json (master stored in Comfy input)')
    s.add_argument('--master',type=Path,help='original master image')
    p.add_argument('--pose-image',required=True,type=Path,help='mannequin RGB used for local geometry extraction only')
    p.add_argument('--pose-json',type=Path,help='BODY18 2D pose; strongly recommended for mannequins')
    p.add_argument('--text',required=True)
    p.add_argument('--preflight',action='store_true')
    p.add_argument('--run',action='store_true')
    p.add_argument('--prepare-pose',action='store_true',help='geometry diagnostics only; no Qwen graph')
    p.add_argument('--make-ui',action='store_true')
    p.add_argument('--approve-unreviewed-pose',action='store_true',help='explicit acknowledgment of 2D geometry warnings')
    p.add_argument('--allow-reference-only',action='store_true',help='explicit EXPERIMENT without hard pose constraint')
    p.add_argument('--comfy-url',default='http://127.0.0.1:8188')
    p.add_argument('--model',default='qwen_image_edit_2511_int8_convrot.safetensors')
    p.add_argument('--clip',default='qwen_2.5_vl_7b_fp8_scaled.safetensors')
    p.add_argument('--vae',default='qwen_image_vae.safetensors')
    p.add_argument('--seed',type=int,default=975311)
    p.add_argument('--steps',type=int,default=20)
    p.add_argument('--cfg',type=float,default=4.0)
    p.add_argument('--pose-width',type=int,default=768,help='framing guide width; 768 default')
    p.add_argument('--pose-height',type=int,default=None,help='optional height override, rejected if it conflicts with master aspect')
    p.add_argument('--frame-anchors',type=Path,help='optional SHA-bound head/toe 2D landmarks for framing')
    return p


def main(argv:list[str]|None=None)->int:
    a = make_cli_parser().parse_args(argv)
    output = ROOT/'outputs'/'experiments'/'v8_1_structure'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output.mkdir(parents=True,exist_ok=False)
    report: dict[str, Any] = {
        'schema_version':'v8.1','status':'STARTED','raw_text':a.text,
        'architecture':{
            'appearance_source':'master_only', 'geometry_source':'external_pose_BODY18',
            'mannequin_rgb_forwarding':False, 'silhouette_used_for_generation':False,
            'Qwen_image2':'pose_only_OpenPose', 'Qwen_image3':'master_derived_face_outfit_board',
            'sdxl_stage1':'DISABLED','hard_pose_lock':False,'hard_identity_lock':False,'hard_outfit_lock':False,
            'framing':'MASTER_ASPECT_2D_KEYPOINTS'},
        'quality':{'identity':'NOT_PERFORMED','outfit':'NOT_PERFORMED',
                   'pose':'NOT_PERFORMED','robotic_artifacts':'NOT_PERFORMED','rendering':'NOT_PERFORMED'},
        'author_review':'NOT_PERFORMED','safety_qa':'NOT_PERFORMED','reference_training':'NONE',
        'framing_qa':{'canvas_alignment':'NOT_EVALUATED','feet_visible':'NOT_EVALUATED','pose_exact':'NOT_EVALUATED'}
    }
    try:
        if not 512<=a.pose_width<=1536 or a.pose_width%64 or (a.pose_height is not None and (a.pose_height%64 or not 512<=a.pose_height<=2048)):
            raise V8Error('POSE_CANVAS_INVALID','pose width/height must be divisible by 64')
        request = request_from_text(a.text)
        report['parsed_request'] = request
        if a.pose_json and not a.pose_json.is_file():
            raise V8Error('POSE_JSON_MISSING',str(a.pose_json))
        if not a.pose_image.is_file():
            raise V8Error('POSE_IMAGE_MISSING',str(a.pose_image))
        if a.frame_anchors and not a.frame_anchors.is_file():
            raise V8Error('FRAME_ANCHORS_MISSING',str(a.frame_anchors))
        if a.prepare_pose:
            # No Comfy download or master image needed for this diagnostic-only path.
            # No assertion that the source/master aspect is aligned.
            height = a.pose_height or 1344
            manifest,guide = build_pose_package(pose_image=a.pose_image.resolve(),
                pose_json=a.pose_json.resolve() if a.pose_json else None,
                output_dir=output/'geometry',comfy_url=a.comfy_url,
                width=a.pose_width,height=height)
            report['geometry']=manifest
            report['pose_review_required']=manifest['review_status']!='APPROVED' or bool(manifest['warnings'])
            if a.run or a.make_ui:
                raise V8Error('POSE_PREPARATION_ONLY','--prepare-pose cannot be combined with --run/--make-ui')
            report['framing_qa']['canvas_alignment']='NOT_EVALUATED_NO_MASTER'
            report['status']='POSE_PREPARED_REVIEW_REQUIRED' if report['pose_review_required'] else 'POSE_PREPARED'
            print('[V82:'+report['status']+']')
            print('[V82:OUTPUT] '+str(output))
            return 0
        if a.master:
            master_path = a.master.resolve()
            if not master_path.is_file():
                raise V8Error('MASTER_FILE_MISSING',str(master_path))
        else:
            if not a.source.is_file():
                raise V8Error('SOURCE_FILE_MISSING',str(a.source))
            remote_master = previous_master_name(a.source)
            report['source_graph_sha256']=sha256(a.source)
            if a.preflight or a.run or a.make_ui:
                from comfyui_client import download_image
                master_path=output/'downloaded_master.png'
                download_image(a.comfy_url,remote_master,'','input',master_path,timeout_seconds=60)
                verify_source_master(master_path,remote_master)
            else:
                raise V8Error('MASTER_NOT_LOCAL','use --master for offline compile; --source requires --preflight or --run')
        cw,ch=match_master_canvas(master_path,width=a.pose_width)
        if a.pose_height is not None:
            from PIL import Image
            with Image.open(master_path) as im:
                mw,mh=im.size
            requested_ratio=a.pose_width/a.pose_height
            master_ratio=mw/mh
            if abs(requested_ratio/master_ratio-1)>0.035:
                raise V8Error('FRAME_ASPECT_MISMATCH',f'requested {a.pose_width}x{a.pose_height} differs from master {mw}x{mh}')
            ch=a.pose_height
        manifest,guide=build_pose_package(pose_image=a.pose_image.resolve(),
            pose_json=a.pose_json.resolve() if a.pose_json else None,
            output_dir=output/'geometry',comfy_url=a.comfy_url,width=cw,height=ch)
        alignment=reframe_external_guide(output_dir=output/'geometry',
            mannequin=a.pose_image.resolve(),master=master_path,
            anchors_json=a.frame_anchors.resolve() if a.frame_anchors else None,canvas_width=cw,canvas_height=ch)
        # Preserve both versions: original BODY18-derived image and recomposed full-frame image.
        manifest['pose_only_openpose_original']=manifest['pose_only_openpose']
        guide=Path(alignment['pose_guide_path'])
        manifest['pose_only_openpose']={'path':str(guide),'sha256':sha256(guide),'width':cw,'height':ch}
        manifest['frame_alignment']=alignment
        manifest['warnings']=list(dict.fromkeys(manifest['warnings']+alignment['warnings']))
        report['geometry']=manifest
        report['pose_review_required']=manifest['review_status']!='APPROVED' or bool(manifest['warnings'])
        report['framing_qa']['canvas_alignment']='PASS_REFERENCE_GUIDE_ONLY'
        report['framing_qa']['feet_visible']='NOT_EVALUATED_GENERATION_NOT_COMPLETE'
        report['master_sha256'] = sha256(master_path)
        bundle = make_reference_bundle(master_path, output/'reference_bundle')
        board_path = Path(bundle['reference_sheet']['path'])
        report['appearance']={'master_sha256':sha256(master_path),
                              'reference_bundle':bundle,'detail_sheet_sha256':sha256(board_path),
                              'appearance_provenance':'MASTER_ONLY'}
        master_name='V81_MASTER_'+sha256(master_path)[:16]+'.png'
        pose_name='V81_POSE_ONLY_'+sha256(guide)[:16]+'.png'
        board_name='V81_MASTER_DETAILS_'+sha256(board_path)[:16]+'.png'
        graph=build_direct_graph(master_name, pose_name, board_name, a.text, request,
            pose_warnings=manifest['warnings'],model=a.model,clip=a.clip,vae=a.vae,
            seed=a.seed,steps=a.steps,cfg=a.cfg)
        validate_direct_graph(graph)
        graph_file=output/'v8_1_api.json'
        save_json(graph_file,graph)
        report['graph_path']=str(graph_file)
        report['reference_roles']={'image1':'MASTER','image2':'POSE_ONLY_OPENPOSE_2D_REFERENCE_ONLY_FULL_FRAME',
                                   'image3':'MASTER_DERIVED_DETAILS'}
        report['status']='COMPILED_UNVERIFIED'
        if a.preflight or a.run or a.make_ui:
            info=fetch_object_info(a.comfy_url)
            validate_runtime(graph,info)
            assessment=assess_qwen_pose_control(info,a.model)
            report['pose_conditioning']=assessment.to_dict()
            enforce_pose_control(assessment, allow_reference_only=a.allow_reference_only)
            report['runtime_preflight']='PASS_REFERENCE_ONLY' if assessment.status==REFERENCE_ONLY else 'PASS'
            if a.make_ui:
                save_json(output/'v8_1_ui.json',ui_graph(graph,info))
                report['ui_import_qa']='NOT_PERFORMED'
        if a.run:
            if report['pose_review_required'] and not a.approve_unreviewed_pose:
                raise V8Error('POSE_REVIEW_REQUIRED','Review 2D joints and warnings, then explicitly use --approve-unreviewed-pose')
            from comfyui_client import upload_input_image, run_workflow_and_download
            # Every final Comfy image is the master or a DERIVED geometric/appearance image.
            master_remote=upload_input_image(a.comfy_url,master_path,remote_name=master_name,timeout_seconds=60)
            pose_remote=upload_input_image(a.comfy_url,guide,remote_name=pose_name,timeout_seconds=60)
            board_remote=upload_input_image(a.comfy_url,board_path,remote_name=board_name,timeout_seconds=60)
            graph['4']['inputs']['image']=master_remote
            graph['5']['inputs']['image']=pose_remote
            graph['17']['inputs']['image']=board_remote
            validate_direct_graph(graph)
            save_json(graph_file,graph)
            if a.make_ui:
                save_json(output/'v8_1_ui.json',ui_graph(graph,info))
            result=run_workflow_and_download(a.comfy_url,graph,output/'images',
                    request_timeout_seconds=60,generation_timeout_seconds=1800)
            report['image']={'path':str(result.output_path),
                             'sha256':sha256(result.output_path),'prompt_id':result.prompt_id}
            review_sheet(master_path,result.output_path,output/'comparison.png')
            report['comparison_path']=str(output/'comparison.png')
            from PIL import Image
            with Image.open(master_path) as m, Image.open(result.output_path) as generated:
                mr=m.width/m.height; gr=generated.width/generated.height
                delta=abs(gr/mr-1)
                report['framing_qa']['generated_dimensions']={'width':generated.width,'height':generated.height}
                report['framing_qa']['output_aspect_error_relative']=round(delta,5)
                report['framing_qa']['canvas_alignment']='PASS' if delta<=0.035 else 'FAIL_OUTPUT_ASPECT_CHANGED'
                report['framing_qa']['feet_visible']='NOT_EVALUATED_AUTHOR_VISUAL_REVIEW_REQUIRED'
                report['framing_qa']['pose_exact']='NOT_EVALUATED_AUTHOR_VISUAL_REVIEW_REQUIRED'
            report['status']='GENERATED_UNVERIFIED_REFERENCE_ONLY'
        print('[V82:'+report['status']+']')
        print('[V82:OUTPUT] '+str(output))
        return 0
    except Exception as exc:
        code=getattr(exc,'code',getattr(exc,'category',type(exc).__name__))
        report.update(status='FAIL',error_type=code,message=str(exc))
        print('[V82:FAIL:'+str(code)+'] '+str(exc),file=sys.stderr)
        return 2
    finally:
        save_json(output/'diagnostic.json',report)

if __name__=='__main__':
    raise SystemExit(main())
