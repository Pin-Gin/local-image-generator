"""V7 staged generation: hard(er) OpenPose geometry -> Qwen identity/outfit/style transfer.

The stages use separate model families; Qwen Edit 2511 is NOT asserted compatible
with Qwen Image (text2img) ControlNet LoRAs. Neither hard identity nor clothing
locks are available from one master. Outputs always require human acceptance.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT / 'src', ROOT / 'experiments' / 'active'):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from v7_references import make_reference_bundle, sha256
from v7_geometry import request_from_text, pose_phrase, make_stage1_graph, load_legacy_graph
from v7_quality import review_sheet, local_ollama_review
from v7_ui_export import ui_graph
from v7_external_pose import prepare_external_pose, PoseImportError, sha256 as pose_file_sha256

DEFAULT_OLD_GRAPH = ROOT / 'outputs/experiments/text_pose_web/20261115T055422_a000cbe4a055e0ad/compiled_workflow.json'
POSE_SHA_V1 = '5c878552a3ff18b220886a8c27f1e4e3c1e8df0cfa23e0a2c7a7f74ad49185fd'


class V7Error(RuntimeError):
    def __init__(self, category: str, message: str):
        self.category=category
        super().__init__(message)


def _model_module():
    try:
        from qwen2511_reference_pose_v6 import (build_graph, ensure_graph, validate_runtime,
                                                  ui_graph, fetch_object_info)
    except ImportError as ex:
        raise V7Error('DEPENDENCY_MISSING','v6 Qwen module must be present; it is already installed in the user project') from ex
    return build_graph, ensure_graph, validate_runtime, ui_graph, fetch_object_info


def _comfy():
    from comfyui_client import (fetch_system_stats, upload_input_image, download_image,
                                run_workflow_and_download)
    return fetch_system_stats, upload_input_image, download_image, run_workflow_and_download


def _safe_metadata(info: dict[str,Any], graph:dict[str,Any], model_checks:tuple[tuple[str,str],...]) -> None:
    for nid,node in graph.items():
        typ=node['class_type']
        meta=info.get(typ)
        if not isinstance(meta,dict):
            raise V7Error('COMFYUI_NODE_MISSING',f'{nid}: {typ}')
        inputs=meta.get('input',{})
        allowed=set(inputs.get('required',{})) | set(inputs.get('optional',{})) | set(inputs.get('hidden',{}))
        for k in node['inputs']:
            if k not in allowed:
                raise V7Error('COMFYUI_INPUT_MISSING',f'{nid}: {typ}.{k}')
    for nid, key in model_checks:
        node=graph[nid]
        typ=node['class_type']
        options=info[typ].get('input',{}).get('required',{}).get(key,[[]])[0]
        val=node['inputs'][key]
        if isinstance(options,list) and val not in options:
            raise V7Error('COMFYUI_MODEL_MISSING',f'{val} ({typ})')


def stage2_prompt(raw: str, request: dict[str, Any], *, external_pose: bool=False) -> str:
    from qwen2511_reference_pose_v6 import pose_prompt
    pose=(
        'the exact joint relationships seen in IMAGE 1: preserve the knee, ankle, wrist and pelvis positions, do not cross feet, do not reinterpret the external skeleton using a generic sitting pose'
        if external_pose else pose_prompt(request)
    )
    expression=('gentle natural smile' if request.get('deltas',{}).get('expression')=='soft_smile'
                else 'the original facial expression')
    return (
        'You are editing THREE image references with distinct roles. '
        'IMAGE 1 is the posed CANVAS. Keep ONLY its geometric pose, position of limbs, '
        'contact with floor, full-body crop and camera. Treat image 1 face, hair, clothing, '
        'color and drawing style as disposable placeholders. '
        'IMAGE 2 is the ORIGINAL MASTER. Copy the unique adult woman identity and exact '
        'short bob hair, eye shape, facial proportions, body proportions, original sleeveless '
        'camisole with lace trim and bow, matching short shorts, fabric construction and '
        'matte soft anime realism drawing style FROM IMAGE 2. Do not change attire. '
        'IMAGE 3 contains two close-up crops cut from IMAGE 2: the LEFT panel is FACE/HAIR '
        'and the RIGHT panel is ORIGINAL OUTFIT. These are reference details only, '
        'not a second person and not objects to paste into the scene. '
        'Generate ONE scene. Geometric target from image 1: '+pose+'. '
        'Expression: '+expression+'. Keep the master room, curtain, rug, drawer and flowers. '
        'Do not add a chair, bed, long sleeves, high-neck bodysuit or new accessories. '
        'Keep all visible body parts anatomically coherent. '
        'Do not include any text, skeleton bones, guide sticks, reference panels or collages. '
        'The original Japanese instruction must remain satisfied: 「'+raw.strip()+'」'
    )


def make_stage2_graph(canvas_name: str, master_name: str, board_name: str,
                      raw: str, request: dict[str, Any], *, model: str, clip: str,
                      vae: str, seed: int, steps: int, cfg: float,
                      external_pose: bool=False) -> dict[str,Any]:
    build_graph, ensure_graph, *_ = _model_module()
    # image1: structural canvas; image2: master; image3: identity+outfit sheet
    g=build_graph(canvas_name, master_name, raw, request, face_name=board_name,
                  model=model,clip=clip,vae=vae,seed=seed,steps=steps,cfg=cfg,
                  filename_prefix='LOCAL_RAG_V7_STAGE2_IDENTITY_OUTFIT')
    g['7']['inputs']['prompt']=stage2_prompt(raw,request,external_pose=external_pose)
    g['8']['inputs']['prompt']=''
    ensure_graph(g)
    if g['7']['inputs']['image1']!=['6',0] or g['7']['inputs']['image2']!=['5',0] or g['7']['inputs']['image3']!=['17',0]:
        raise V7Error('GRAPH_INVALID','stage 2 reference roles not connected')
    return g


def save_json(path:Path,data:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description='v7 staged pose geometry and identity/outfit preservation experiment')
    master_input=p.add_mutually_exclusive_group(required=True)
    master_input.add_argument('--source',type=Path,help='existing v1/v2 compiled_workflow.json')
    master_input.add_argument('--master',type=Path,help='single original master photo')
    p.add_argument('--text',required=True)
    p.add_argument('--pose-image',type=Path,help='external mannequin reference; DWPose auto-inference when no --pose-json')
    p.add_argument('--pose-json',type=Path,help='validated BODY_18/OpenPose 2D pose JSON (preferred when provided)')
    p.add_argument('--pose-width',type=int,default=896,help='external OpenPose canvas width (multiple of 64)')
    p.add_argument('--pose-height',type=int,default=960,help='external OpenPose canvas height (multiple of 64)')
    p.add_argument('--prepare-pose',action='store_true',help='extract/validate and save external pose, no image generation')
    p.add_argument('--template',type=Path,default=DEFAULT_OLD_GRAPH,help='legacy SDXL geometry graph')
    p.add_argument('--run',action='store_true',help='run both model stages once')
    p.add_argument('--stage',choices=['pose','full'],default='full',help='run pose stage only, or full pipeline')
    p.add_argument('--preflight',action='store_true',help='check installed nodes/models, no GPU run')
    p.add_argument('--make-ui',action='store_true',help='export UI JSON using actual ComfyUI metadata')
    p.add_argument('--qa-ollama',action='store_true',help='optional local VLM advisory; does not confer PASS')
    p.add_argument('--comfy-url',default='http://127.0.0.1:8188')
    p.add_argument('--ollama-url',default='http://127.0.0.1:11435')
    p.add_argument('--seed',type=int,default=975311)
    p.add_argument('--strength',type=float,default=1.2)
    p.add_argument('--model',default='qwen_image_edit_2511_int8_convrot.safetensors')
    p.add_argument('--clip',default='qwen_2.5_vl_7b_fp8_scaled.safetensors')
    p.add_argument('--vae',default='qwen_image_vae.safetensors')
    p.add_argument('--steps',type=int,default=20)
    p.add_argument('--cfg',type=float,default=4.0)
    a=p.parse_args(argv)
    external_pose=bool(a.pose_image or a.pose_json)
    if a.prepare_pose and not external_pose:
        p.error('--prepare-pose requires --pose-image or --pose-json')
    if external_pose and (a.pose_width%64 or a.pose_height%64 or
                         not 512<=a.pose_width<=1536 or not 512<=a.pose_height<=1536):
        p.error('external pose canvas must be 512..1536 pixels and divisible by 64')

    out=ROOT/'outputs/experiments/v7_hybrid' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True,exist_ok=False)
    report:dict[str,Any]={
        'schema_version':1,'status':'STARTED','version':'v7-hybrid-experimental',
        'architecture':{'geometry':'SDXL+OpenPose ControlNet','identity':'Qwen-Image-Edit-2511 multi-reference',
                        'outfit':'original garment reference sheet and explicit preservation contract',
                        'style':'original master and prompt','hard_pose_stage2':False,
                        'identity_hard_lock':False,'outfit_hard_lock':False},
        'user_text':a.text,'safety_qa':'NOT_PERFORMED',
        'external_pose_requested':external_pose,
        'external_pose_priority':'POSE_JSON_FIRST_THEN_DWPOSE' if external_pose else 'LEGACY_FIXED_TEMPLATE',
        'identity_qa':'NOT_PERFORMED','outfit_qa':'NOT_PERFORMED',
        'rendering_qa':'NOT_PERFORMED','pose_qa':'NOT_PERFORMED',
        'author_acceptance':'NOT_PERFORMED',
        'reference_image_training':'NONE',
    }
    try:
        request=request_from_text(a.text)
        report['parsed_request']=request
        legacy, saved_master, saved_pose=load_legacy_graph(a.source or a.template)
        report['source_graph_sha256']=sha256(a.source or a.template)
        root_master:Path|None=None
        pose_path:Path|None=None
        master_name=saved_master
        pose_name=saved_pose
        if a.master:
            root_master=a.master.resolve()
            if not root_master.is_file():
                raise V7Error('MASTER_MISSING',str(root_master))
            master_name='V7_MASTER_'+sha256(root_master)[:16]+root_master.suffix.lower()
            if not external_pose:
                from free_text_pose_poc import render_pose
                pose_path=out/'pose_guide.png'
                render_pose(request['pose']['id'],pose_path)
                pose_name='V7_POSE_'+sha256(pose_path)[:16]+'.png'
                report['pose_sha256']=sha256(pose_path)
            report['master_sha256']=sha256(root_master)
        else:
            if not external_pose and (request['pose']['id']!='seated_m' or saved_pose!='POC_POSE_5c878552a3ff.png'):
                raise V7Error('POSE_SOURCE_UNVERIFIED','old session is only authenticated for seated_m. use --master for other poses')
            report['source_asset_status']='NOT_VERIFIED_UNTIL_COMFY_DOWNLOAD'

        # External pose takes precedence over legacy fixed pose canvas, with source hash recorded.
        if external_pose:
            try:
                pose_doc,pose_path=prepare_external_pose(
                    pose_image=a.pose_image.resolve() if a.pose_image else None,
                    pose_json=a.pose_json.resolve() if a.pose_json else None,
                    output_dir=out/'external_pose',comfy_url=a.comfy_url,
                    width=a.pose_width,height=a.pose_height)
            except PoseImportError as e:
                raise V7Error(e.code,str(e)) from e
            pose_name='V7_EXTERNAL_POSE_'+sha256(pose_path)[:16]+'.png'
            report['pose_sha256']=sha256(pose_path)
            report['external_pose']={
                'source_type':pose_doc['source_type'],
                'source_image_sha256':pose_doc.get('source_image_sha256'),
                'pose_json_path':str(out/'external_pose'/'external_pose.json'),
                'rendered_openpose_path':str(pose_path),
                'canvas':{'width':a.pose_width,'height':a.pose_height},
                'warnings':pose_doc['warnings'],
                'depth_status':pose_doc['depth_status'],
                'review_status':pose_doc['review_status'],
                'source_image_hash_verified':pose_doc['source_image_hash_verified']}
            if a.prepare_pose:
                report['status']='POSE_PREPARED_REVIEW_REQUIRED'
                print('[V7:'+report['status']+']')
                print('[V7:POSE_JSON] '+str(out/'external_pose'/'external_pose.json'))
                print('[V7:POSE_GUIDE] '+str(pose_path))
                print('[V7:OUTPUT] '+str(out))
                return 0

        # Source mode needs Comfy input files to prepare the garment/face sheet.
        if a.preflight or a.make_ui or a.run:
            _,_,download_image,_=_comfy()
            if not a.master:
                root_master=out/'downloaded_master.png'
                download_image(a.comfy_url, master_name,'','input',root_master,timeout_seconds=50)
                if not external_pose:
                    pose_path=out/'downloaded_pose.png'
                    download_image(a.comfy_url, pose_name,'','input',pose_path,timeout_seconds=50)
                    if sha256(pose_path)!=POSE_SHA_V1:
                        raise V7Error('POSE_SOURCE_MISMATCH','stored ComfyUI pose bytes do not match the previous verified session')
                # Saved master filename is content-addressed; reject silent replacement.
                expected_prefix=saved_master.removeprefix('POC_MAIN_').split('.')[0]
                if not sha256(root_master).startswith(expected_prefix):
                    raise V7Error('MASTER_SOURCE_MISMATCH','ComfyUI master image has been replaced since the original session')
                report.update(master_sha256=sha256(root_master),
                              source_asset_status='VERIFIED_MASTER_BYTES')
                if pose_path is not None: report['pose_sha256']=sha256(pose_path)

        if root_master is not None:
            report['local_master_for_comparison']=str(root_master)

        board_name='V7_REFERENCE_SHEET_PENDING.png'
        board_path:Path|None=None
        if root_master is not None:
            bundle=make_reference_bundle(root_master,out/'reference_bundle')
            report['reference_bundle']=bundle
            board_path=Path(bundle['reference_sheet']['path'])
            board_name='V7_DETAILS_'+sha256(board_path)[:16]+'.png'

        stage1=make_stage1_graph(legacy,pose_name,request['pose']['id'],seed=a.seed,
                                 control_strength=a.strength)
        if external_pose:
            stage1['2']['inputs'].update({'width':a.pose_width,'height':a.pose_height})
            # Geometry authority comes from external keypoints; retain text only as descriptive.
            stage1['3']['inputs']['text']=(
                'single adult woman, full figure, reproduce the pose from the input OpenPose guide exactly, '
                'correct relative knee, ankle, wrist and hip positions, floor-supported posture, '
                'anatomically coherent joints, neutral simple clothing, do not cross legs unless guide crosses them')
            report['geometry_source']='EXTERNAL_POSE_JSON'
        save_json(out/'stage1_geometry_api.json',stage1)
        # This is the *anticipated* Stage2 graph. At runtime the pose-canvas name
        # is replaced with the actual stage1 output uploaded to ComfyUI.
        stage2=make_stage2_graph('V7_PENDING_STAGE1_CANVAS.png',master_name,board_name,a.text,request,
                                  model=a.model,clip=a.clip,vae=a.vae,seed=a.seed,
                                  steps=a.steps,cfg=a.cfg,external_pose=external_pose)
        save_json(out/'stage2_identity_outfit_api.json',stage2)
        report['compiled_graphs']={'geometry':str(out/'stage1_geometry_api.json'),
                                   'identity_outfit':str(out/'stage2_identity_outfit_api.json')}
        report['reference_sheet_status']='READY' if board_path else 'REQUIRES_COMFY_SOURCE_DOWNLOAD'
        report['status']='COMPILED_ONLY'

        if a.preflight or a.make_ui or a.run:
            _,_,_,_,fetch_object_info=_model_module()
            info=fetch_object_info(a.comfy_url)
            _safe_metadata(info,stage1,(('1','ckpt_name'),('22','control_net_name')))
            if a.stage=='full':
                _safe_metadata(info,stage2,(('1','unet_name'),('2','clip_name'),('3','vae_name')))
            report['preflight']='PASS'
            if a.make_ui:
                save_json(out/'stage1_geometry_ui.json',ui_graph(stage1,info))
                if a.stage=='full':
                    save_json(out/'stage2_identity_outfit_ui.json',ui_graph(stage2,info))
                report['ui_import_test']='NOT_PERFORMED'

        if a.run:
            if root_master is None or board_path is None or pose_path is None:
                raise V7Error('REFERENCE_NOT_READY','master/pose reference preparation failed')
            fetch_stats,upload,_,run_workflow=_comfy()
            fetch_stats(a.comfy_url)
            if a.master:
                master_name=upload(a.comfy_url,root_master,remote_name=master_name,timeout_seconds=60)
            if external_pose or a.master:
                pose_name=upload(a.comfy_url,pose_path,remote_name=pose_name,timeout_seconds=60)
            stage1['20']['inputs']['image']=pose_name
            save_json(out/'stage1_geometry_api.json',stage1)
            if a.make_ui:
                save_json(out/'stage1_geometry_ui.json',ui_graph(stage1,info))
            geometry=run_workflow(a.comfy_url,stage1,out/'images/stage1_geometry',
                                  request_timeout_seconds=60,generation_timeout_seconds=900)
            report['geometry_result']={'prompt_id':geometry.prompt_id,
                'path':str(geometry.output_path),'sha256':sha256(geometry.output_path),
                'pose_qc':'NOT_VERIFIED'}
            if a.stage=='pose':
                report['status']='GEOMETRY_GENERATED_UNVERIFIED'
            else:
                canvas_name='V7_POSE_CANVAS_'+sha256(geometry.output_path)[:16]+'.png'
                canvas_name=upload(a.comfy_url,geometry.output_path,remote_name=canvas_name,timeout_seconds=60)
                board_name=upload(a.comfy_url,board_path,remote_name=board_name,timeout_seconds=60)
                stage2['4']['inputs']['image']=canvas_name
                stage2['5']['inputs']['image']=master_name
                stage2['17']['inputs']['image']=board_name
                save_json(out/'stage2_identity_outfit_api.json',stage2)
                if a.make_ui:
                    save_json(out/'stage2_identity_outfit_ui.json',ui_graph(stage2,info))
                result=run_workflow(a.comfy_url,stage2,out/'images/stage2_result',
                                     request_timeout_seconds=60,generation_timeout_seconds=1800)
                review_sheet(root_master,result.output_path,out/'comparison.png')
                report['stage2_result']={'prompt_id':result.prompt_id,
                        'path':str(result.output_path),'sha256':sha256(result.output_path)}
                report['status']='GENERATED_UNVERIFIED'
                report['comparison']=str(out/'comparison.png')
                if a.qa_ollama:
                    verdict=local_ollama_review(root_master,result.output_path,a.text,url=a.ollama_url)
                    report['ollama_advisory']=verdict
                    save_json(out/'qa_advisory.json',verdict)
                    qa_mapping={'identity_qa':('face_same','hair_same'),
                                'outfit_qa':('outfit_same',),
                                'rendering_qa':('rendering_same',),
                                'pose_qa':('pose_match',)}
                    if isinstance(verdict.get('fields'),dict):
                        for qa_key,keys in qa_mapping.items():
                            report[qa_key]='ADVISORY_FAIL' if not all(verdict['fields'][key] for key in keys) else 'ADVISORY_ONLY'
                    if verdict['status']=='AUTOMATED_ADVISORY_FAIL':
                        report['status']='REJECTED_AUTOMATED_ADVISORY'
            # No success verdict without author review.
        print('[V7:'+report['status']+']')
        print('[V7:OUTPUT] '+str(out))
        return 0
    except Exception as ex:
        typ=getattr(ex,'category',type(ex).__name__)
        report.update(status='FAIL',error_type=typ,message=str(ex))
        print('[V7:FAIL:'+str(typ)+'] '+str(ex),file=sys.stderr)
        return 2
    finally:
        save_json(out/'diagnostic.json',report)


if __name__=='__main__':
    raise SystemExit(main())
