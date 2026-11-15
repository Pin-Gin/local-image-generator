"""External mannequin IMAGE / Pose JSON -> validated BODY_18 -> OpenPose RGB.

A 2D image never establishes true 3D joint positions. Unobserved joints remain
unobserved; this module does not invent depth or an anatomically valid 3D rig.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

JOINTS = (
    'nose', 'neck', 'right_shoulder', 'right_elbow', 'right_wrist',
    'left_shoulder', 'left_elbow', 'left_wrist', 'right_hip',
    'right_knee', 'right_ankle', 'left_hip', 'left_knee', 'left_ankle',
    'right_eye', 'left_eye', 'right_ear', 'left_ear',
)
# 17-point COCO is different from OpenPose BODY_18. Names mapped explicitly.
COCO17 = ('nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
          'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
          'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
          'left_knee', 'right_knee', 'left_ankle', 'right_ankle')
BONES = ((1, 2), (2, 3), (3, 4), (1, 5), (5, 6), (6, 7),
         (1, 8), (8, 9), (9, 10), (1, 11), (11, 12), (12, 13),
         (1, 0), (0, 14), (14, 16), (0, 15), (15, 17))
COLORS = ((255, 0, 0), (255, 85, 0), (255, 170, 0), (255, 255, 0),
          (170, 255, 0), (85, 255, 0), (0, 255, 0), (0, 255, 85),
          (0, 255, 170), (0, 255, 255), (0, 170, 255), (0, 85, 255),
          (0, 0, 255), (85, 0, 255), (170, 0, 255), (255, 0, 255),
          (255, 0, 170), (255, 0, 85))
CORE = ('neck','right_shoulder','left_shoulder','right_elbow','left_elbow',
        'right_wrist','left_wrist','right_hip','left_hip',
        'right_knee','left_knee','right_ankle','left_ankle')


class PoseImportError(ValueError):
    def __init__(self, code: str, message: str):
        self.code=code
        super().__init__(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _valid_point(obj: Any, w: int, h: int, coordinate_space: str) -> dict[str,Any]|None:
    if obj is None:
        return None
    if isinstance(obj, dict):
        x,y,c = obj.get('x'),obj.get('y'),obj.get('confidence',1.0)
        observability=obj.get('observability','estimated')
    elif isinstance(obj,(list,tuple)) and len(obj)>=3:
        x,y,c=obj[:3]
        observability='estimated'
    else:
        raise PoseImportError('POSE_POINT_INVALID','keypoint must be [x,y,confidence], object, or null')
    if not all(isinstance(v,(float,int)) and math.isfinite(v) for v in (x,y,c)):
        raise PoseImportError('POSE_POINT_INVALID','non-finite or non-numeric point')
    if not 0<=c<=1:
        raise PoseImportError('POSE_CONFIDENCE_INVALID',f'confidence={c} outside [0,1]')
    if c==0:
        return None
    if coordinate_space=='normalized':
        if not (0<=x<=1 and 0<=y<=1):
            raise PoseImportError('POSE_POINT_OUT_OF_BOUNDS','normalized coordinates must be within [0,1]')
        x,y=x*w,y*h
    elif coordinate_space=='pixels':
        if not (0<=x<w and 0<=y<h):
            raise PoseImportError('POSE_POINT_OUT_OF_BOUNDS',f'pixel ({x},{y}) outside ({w},{h})')
    else:
        raise PoseImportError('POSE_COORDINATE_SPACE_INVALID',coordinate_space)
    return {'x':round(float(x),2),'y':round(float(y),2),
            'confidence':round(float(c),4),'observability':str(observability)}


def _unpack_native(value: Any, width: int,height: int) -> dict[str,Any]:
    if isinstance(value,list):
        if len(value)!=1:
            raise PoseImportError('POSE_PERSON_COUNT_INVALID','expected one frame/person')
        value=value[0]
    if not isinstance(value,dict) or 'people' not in value:
        raise PoseImportError('POSE_NATIVE_FORMAT_INVALID','expected {people:[...]}')
    people=value['people']
    if not isinstance(people,list) or len(people)!=1:
        raise PoseImportError('POSE_PERSON_COUNT_INVALID',f'expected one person, got {len(people) if isinstance(people,list) else "invalid"}')
    raw=people[0].get('pose_keypoints_2d',None)
    if not isinstance(raw,list):
        raise PoseImportError('POSE_NATIVE_FORMAT_INVALID','missing pose_keypoints_2d')
    if raw and not isinstance(raw[0],(list,tuple)):
        if len(raw)%3!=0:
            raise PoseImportError('POSE_NATIVE_FORMAT_INVALID','flattened points must have triples')
        raw=[raw[i:i+3] for i in range(0,len(raw),3)]
    if len(raw)==18:
        pairs={name:raw[i] for i,name in enumerate(JOINTS)}
    elif len(raw)==17:
        pairs={name:raw[i] for i,name in enumerate(COCO17)}
        # only neck midpoint if BOTH shoulders detected; explicitly mark estimated
        a,b=pairs.get('left_shoulder'),pairs.get('right_shoulder')
        if a and b and a[2]>0 and b[2]>0:
            pairs['neck']={'x':(a[0]+b[0])/2,'y':(a[1]+b[1])/2,
                           'confidence':min(a[2],b[2])*0.8,'observability':'inferred_midpoint'}
        else:
            pairs['neck']=None
    else:
        raise PoseImportError('POSE_NATIVE_JOINT_COUNT',f'expected 17 COCO or 18 BODY_18, got {len(raw)}')
    src_w=value.get('canvas_width',width)
    src_h=value.get('canvas_height',height)
    if not isinstance(src_w,int) or not isinstance(src_h,int) or src_w<=0 or src_h<=0:
        raise PoseImportError('POSE_CANVAS_INVALID','native canvas dimensions invalid')
    # Pose exporters may produce normalized coordinates, but do not guess if unsure.
    samples=[v for v in pairs.values() if v is not None and (v.get('confidence',0)>0 if isinstance(v,dict) else v[2]>0)]
    norm= bool(samples) and all((isinstance(v,dict) and 0<=v['x']<=1 and 0<=v['y']<=1 or
       isinstance(v,(list,tuple)) and 0<=v[0]<=1 and 0<=v[1]<=1) for v in samples)
    coords={}
    for name in JOINTS:
        point=pairs.get(name)
        if point is None: coords[name]=None;continue
        if isinstance(point,dict):
            point=point.copy()
        coords[name]=_valid_point(point,src_w,src_h,'normalized' if norm else 'pixels')
        if coords[name]:
            coords[name]['x']=round(coords[name]['x']*width/src_w,2)
            coords[name]['y']=round(coords[name]['y']*height/src_h,2)
    return coords


def parse_pose_json(payload:Any, *,source_width:int|None=None,source_height:int|None=None,
                    source_sha256:str|None=None) -> dict[str,Any]:
    if isinstance(payload,dict) and payload.get('schema_version')=='v7.pose2d.v1':
        dims=payload.get('source_dimensions',{})
        w,h=dims.get('width'),dims.get('height')
        if not isinstance(w,int) or not isinstance(h,int) or not (0<w<=16384 and 0<h<=16384):
            raise PoseImportError('POSE_DIMENSIONS_INVALID','source_dimensions width/height are required')
        if source_width is not None and (w,h)!=(source_width,source_height):
            raise PoseImportError('POSE_SOURCE_DIMENSIONS_MISMATCH','pose JSON dimensions differ from image')
        digest=payload.get('source_image_sha256')
        if digest and source_sha256 and digest.lower()!=source_sha256.lower():
            raise PoseImportError('POSE_SOURCE_HASH_MISMATCH','pose JSON refers to a different mannequin image')
        raw=payload.get('keypoints')
        if not isinstance(raw,dict) or set(raw)-set(JOINTS):
            raise PoseImportError('POSE_KEYPOINT_FORMAT_INVALID','keypoints must use BODY_18 joint names')
        coords={key:_valid_point(raw.get(key),w,h,payload.get('coordinate_space','pixels')) for key in JOINTS}
        status=payload.get('review_status','NEEDS_HUMAN_REVIEW')
        source_type=payload.get('source_type','user_supplied')
    else:
        w,h=source_width,source_height
        if isinstance(payload,dict):
            w=w or payload.get('canvas_width')
            h=h or payload.get('canvas_height')
        if isinstance(payload,list) and len(payload)==1 and isinstance(payload[0],dict):
            w=w or payload[0].get('canvas_width');h=h or payload[0].get('canvas_height')
        if not isinstance(w,int) or not isinstance(h,int) or w<=0 or h<=0:
            raise PoseImportError('POSE_DIMENSIONS_INVALID','native OpenPose needs canvas_width/height')
        coords=_unpack_native(payload,w,h)
        source_type='dwpose_estimated'
        status='NEEDS_HUMAN_REVIEW'

    missing=[name for name in CORE if coords[name] is None or coords[name]['confidence']<0.2]
    if missing:
        raise PoseImportError('POSE_CORE_JOINTS_MISSING',','.join(missing))
    warnings=[]
    if isinstance(payload,dict) and payload.get('schema_version')=='v7.pose2d.v1':
        if not payload.get('source_image_sha256') and source_sha256:
            warnings.append('SOURCE_HASH_NOT_DECLARED: image+JSON association unverified')
        if payload.get('source_image_sha256') and not source_sha256:
            warnings.append('SOURCE_HASH_NOT_VERIFIED_WITH_IMAGE: image not supplied')
    if coords['right_ankle']['x']<coords['right_knee']['x'] and coords['left_ankle']['x']>coords['left_knee']['x']:
        warnings.append('ANKLES_OUTSIDE_KNEES: this mannequin differs from the earlier feet-inward M-seat specification')
    if coords['right_knee']['x']>=coords['left_knee']['x']:
        warnings.append('KNEE_LEFT_RIGHT_ORDER_INVALID')
    if coords['right_ankle']['x']>=coords['left_ankle']['x']:
        warnings.append('ANKLES_CROSSED_OR_LEFT_RIGHT_ORDER_INVALID')
    return {'schema_version':'v7.pose2d.v1','source_type':source_type,
            'source_dimensions':{'width':w,'height':h},
            'coordinate_space':'pixels','keypoints':coords,
            'depth_status':'UNKNOWN_2D_IMAGE_ONLY','review_status':status,
            'warnings':warnings,'source_image_sha256':source_sha256 or (payload.get('source_image_sha256') if isinstance(payload,dict) else None),
            'source_image_hash_verified':bool(source_sha256 and isinstance(payload,dict) and payload.get('source_image_sha256')==source_sha256),
            'source_3d_rig':'NOT_AVAILABLE'}


def project(points:dict[str,Any],width:int,height:int,*,canvas_width:int,canvas_height:int,
            margin_ratio:float=0.055)->dict[str,Any]:
    if width<=0 or height<=0 or canvas_width<256 or canvas_height<256:
        raise PoseImportError('POSE_CANVAS_INVALID','canvas dimensions invalid')
    valid=[p for p in points.values() if p is not None]
    xs=[p['x'] for p in valid];ys=[p['y'] for p in valid]
    # Use the occupied figure, not the full margins of original reference.
    minx,maxx=min(xs),max(xs);miny,maxy=min(ys),max(ys)
    span_x=max(1.0,maxx-minx);span_y=max(1.0,maxy-miny)
    avail_w=canvas_width*(1-2*margin_ratio)
    avail_h=canvas_height*(1-2*margin_ratio)
    scale=min(avail_w/span_x,avail_h/span_y)
    offset_x=(canvas_width-scale*span_x)/2-scale*minx
    offset_y=(canvas_height-scale*span_y)/2-scale*miny
    out={}
    for name,p in points.items():
        out[name]=None if p is None else dict(p,x=round(scale*p['x']+offset_x,2),y=round(scale*p['y']+offset_y,2))
    return out


def render_openpose(doc:dict[str,Any],destination:Path,*,width:int=896,height:int=960)->dict[str,Any]:
    points=doc['keypoints']
    p=project(points,doc['source_dimensions']['width'],doc['source_dimensions']['height'],
              canvas_width=width,canvas_height=height)
    im=Image.new('RGB',(width,height),'black')
    draw=ImageDraw.Draw(im)
    stroke=max(3,round(min(width,height)*0.006))
    for i,(a,b) in enumerate(BONES):
        left,right=p[JOINTS[a]],p[JOINTS[b]]
        if left and right:
            draw.line([(left['x'],left['y']),(right['x'],right['y'])],fill=COLORS[i%len(COLORS)],width=stroke)
    for i,name in enumerate(JOINTS):
        point=p[name]
        if point is None: continue
        x,y=point['x'],point['y']; r=stroke*1.15
        draw.ellipse([x-r,y-r,x+r,y+r], fill=COLORS[i], outline='white',width=1)
    destination.parent.mkdir(parents=True,exist_ok=True)
    im.save(destination)
    return {'path':str(destination),'width':width,'height':height,'projected_keypoints':p}


def render_overlay(doc:dict[str,Any],image_path:Path,destination:Path)->None:
    with Image.open(image_path) as src:
        im=src.convert('RGB')
    draw=ImageDraw.Draw(im)
    for i,name in enumerate(JOINTS):
        p=doc['keypoints'][name]
        if p is None:continue
        x,y=p['x'],p['y']
        draw.ellipse((x-7,y-7,x+7,y+7),fill=COLORS[i],outline='black',width=2)
        if name in CORE:
            draw.text((x+10,y-10),name,fill='black',stroke_width=2,stroke_fill='white')
    destination.parent.mkdir(parents=True,exist_ok=True)
    im.save(destination)


def _dwpose_args(object_info:dict[str,Any],uploaded:str,resolution:int)->dict[str,Any]:
    meta=object_info.get('DWPreprocessor')
    if not isinstance(meta,dict):
        raise PoseImportError('DWPOSE_NODE_MISSING','ComfyUI_controlnet_aux DWPreprocessor unavailable')
    req=meta.get('input',{}).get('required',{})
    inputs={'image':['1',0]}
    desired={'detect_hand':'disable','detect_body':'enable','detect_face':'disable',
             'resolution':resolution,'scale_stick_for_xinsr_cn':'disable',
             'bbox_detector':'yolox_l.onnx',
             'pose_estimator':'dw-ll_ucoco_384_bs5.torchscript.pt'}
    for key,spec in req.items():
        if key=='image':continue
        choices=spec[0] if isinstance(spec,(list,tuple)) and spec else None
        if key in desired:
            value=desired[key]
            if key=='resolution' and isinstance(choices,list):
                value=spec[1].get('default',resolution) if len(spec)>1 and isinstance(spec[1],dict) else resolution
            if isinstance(choices,list) and value not in choices:
                value=choices[0]
            inputs[key]=value
        elif isinstance(choices,list) and choices:
            inputs[key]=choices[0]
        elif len(spec)>1 and isinstance(spec[1],dict) and 'default' in spec[1]:
            inputs[key]=spec[1]['default']
        else:
            raise PoseImportError('DWPOSE_INPUT_UNRESOLVED',key)
    return inputs


def infer_pose_with_comfy(image_path:Path,*,url:str='http://127.0.0.1:8188',resolution:int=1024)->dict[str,Any]:
    """DWPose returns JSON in the /history UI payload. This is GPU-dependent.

    The classifier can fail on artificial mannequins. Never make up missing joints.
    """
    import urllib.request
    from comfyui_client import upload_input_image, submit_prompt, poll_history
    with urllib.request.urlopen(url.rstrip('/')+'/object_info',timeout=15) as response:
        info=json.load(response)
    uploaded=upload_input_image(url,image_path,
                     remote_name='V7_MANNEQUIN_'+sha256(image_path)[:16]+'.png',timeout_seconds=60)
    graph={
        '1':{'class_type':'LoadImage','inputs':{'image':uploaded}},
        '2':{'class_type':'DWPreprocessor','inputs':_dwpose_args(info,uploaded,resolution)},
        '3':{'class_type':'SaveImage','inputs':{'images':['2',0],
                             'filename_prefix':'LOCAL_RAG_V7_DWPOSE_DIAGNOSTIC'}},
    }
    prompt_id=submit_prompt(url,graph,timeout_seconds=35)
    history=poll_history(url,prompt_id,timeout_seconds=450)
    node=history.get('outputs',{}).get('2',{})
    js=node.get('openpose_json')
    if not js and isinstance(node.get('ui'),dict):
        js=node['ui'].get('openpose_json')
    if not js:
        # Comfy can omit UI metadata from /history depending on version.
        raise PoseImportError('DWPOSE_JSON_UNAVAILABLE',
              'DWPreprocessor did not return openpose_json in history; export Pose JSON manually')
    try:
        raw=json.loads(js[0] if isinstance(js,list) else js)
    except (TypeError,IndexError,ValueError) as e:
        raise PoseImportError('DWPOSE_JSON_INVALID','OpenPose metadata cannot be decoded') from e
    with Image.open(image_path) as img:
        w,h=img.size
    parsed=parse_pose_json(raw,source_width=w,source_height=h,
                           source_sha256=sha256(image_path))
    parsed['inference']={'engine':'ComfyUI DWPreprocessor','prompt_id':prompt_id,
                         'raw_shape':'openpose_json','gpu_runtime_verified':True}
    return parsed


def prepare_external_pose(*,pose_image:Path|None,pose_json:Path|None,output_dir:Path,
                          comfy_url:str,width:int=896,height:int=960)->tuple[dict[str,Any],Path]:
    output_dir.mkdir(parents=True,exist_ok=True)
    if pose_image is None and pose_json is None:
        raise PoseImportError('POSE_REFERENCE_MISSING','provide pose image or pose JSON')
    digest=None;dims=None
    if pose_image is not None:
        if not pose_image.is_file():
            raise PoseImportError('POSE_IMAGE_MISSING',str(pose_image))
        with Image.open(pose_image) as im:
            dims=im.size
        digest=sha256(pose_image)
    if pose_json is not None:
        if not pose_json.is_file():
            raise PoseImportError('POSE_JSON_MISSING',str(pose_json))
        data=json.loads(pose_json.read_text(encoding='utf-8'))
        doc=parse_pose_json(data,source_width=dims[0] if dims else None,
                            source_height=dims[1] if dims else None,source_sha256=digest)
        doc['source_type']=data.get('source_type','external_json') if isinstance(data,dict) else 'external_json'
    else:
        doc=infer_pose_with_comfy(pose_image,url=comfy_url)
    pose_path=output_dir/'external_openpose.png'
    render=render_openpose(doc,pose_path,width=width,height=height)
    if pose_image is not None:
        render_overlay(doc,pose_image,output_dir/'keypoint_overlay.png')
    export_doc={**doc,'render_canvas':{'width':width,'height':height},
                'rendered_keypoints_2d':render['projected_keypoints']}
    (output_dir/'external_pose.json').write_text(json.dumps(export_doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return export_doc,pose_path
