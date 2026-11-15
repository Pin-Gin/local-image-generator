"""Fail-closed QA records; optional local vision-model advisory (never self-PASS)."""
from __future__ import annotations
import base64
import json
import urllib.request
from pathlib import Path
from typing import Any
from PIL import Image, ImageOps, ImageDraw


QA_FIELDS = ('face_same', 'hair_same', 'outfit_same', 'rendering_same', 'pose_match')


def review_sheet(master: Path, candidate: Path, out: Path) -> None:
    a = Image.open(master).convert('RGB')
    b = Image.open(candidate).convert('RGB')
    width, height = 600, 950
    sheet = Image.new('RGB', (width*2, height+55), (237,237,237))
    for index, (im, title) in enumerate(((a, 'MASTER'), (b, 'V7 CANDIDATE — NOT VERIFIED'))):
        thumb = ImageOps.contain(im, (width-24, height-20))
        x = index*width + (width-thumb.width)//2
        y = 48 + (height-thumb.height)//2
        sheet.paste(thumb, (x,y))
        ImageDraw.Draw(sheet).text((index*width + 16,15), title, (20,20,20))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


def _as_thumb_b64(image: Path, max_dim: int = 1100) -> str:
    from io import BytesIO
    im = Image.open(image).convert('RGB')
    im.thumbnail((max_dim,max_dim), Image.Resampling.LANCZOS)
    buf = BytesIO()
    im.save(buf, format='JPEG', quality=85)
    return base64.b64encode(buf.getvalue()).decode('ascii')


def local_ollama_review(master: Path, candidate: Path, instruction: str,
                        *, url: str = 'http://127.0.0.1:11435', model: str = 'qwen3-vl:8b-instruct',
                        timeout: int = 180) -> dict[str, Any]:
    """Advisory visual inspection. Never grants acceptance without human review."""
    prompt = (
        'Two images in order: 1 MASTER character, 2 generated candidate. '
        'Compare strictly against master and user instruction. '
        'Return ONLY JSON object with booleans face_same, hair_same, outfit_same, '
        'rendering_same, pose_match and short string notes. '
        'A changed garment (e.g. long sleeves vs camisole) MUST be outfit_same=false. '
        'Do not infer an exact identity percentage. Do not excuse differences. '
        'Requested pose: '+instruction
    )
    data = {
        'model': model, 'stream': False, 'format': 'json',
        'messages': [{'role':'user','content':prompt,
                      'images': [_as_thumb_b64(master),_as_thumb_b64(candidate)]}],
        'options': {'temperature':0},
    }
    req=urllib.request.Request(url.rstrip('/')+'/api/chat',
                                data=json.dumps(data,ensure_ascii=False).encode('utf-8'),
                                headers={'Content-Type':'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            returned=json.load(res)
        answer=json.loads(returned['message']['content'])
        if not isinstance(answer,dict) or any(type(answer.get(k)) is not bool for k in QA_FIELDS):
            raise ValueError('VLM returned an invalid QA schema')
        return {'status': 'AUTOMATED_ADVISORY_FAIL' if not all(answer[k] for k in QA_FIELDS)
                else 'AUTHOR_REVIEW_REQUIRED', 'method':'ollama_vlm_unvalidated_judgment',
                'fields':{k:answer[k] for k in QA_FIELDS}, 'notes':str(answer.get('notes',''))[:1000],
                'author_acceptance':'NOT_PERFORMED', 'numeric_identity_85_percent':'NOT_MEASURABLE'}
    except Exception as ex:
        return {'status':'QA_UNAVAILABLE', 'error_type':type(ex).__name__,
                'message':str(ex)[:800], 'author_acceptance':'NOT_PERFORMED'}


def main(argv: list[str] | None = None) -> int:
    """Separate QA mode, so GPU-heavy ComfyUI generation can finish first."""
    import argparse
    p=argparse.ArgumentParser(description='V7 local VLM QA (advisory, never automatic PASS)')
    p.add_argument('--session',type=Path,required=True)
    p.add_argument('--ollama-url',default='http://127.0.0.1:11435')
    p.add_argument('--model',default='qwen3-vl:8b-instruct')
    args=p.parse_args(argv)
    report_path=args.session/'diagnostic.json'
    report=json.loads(report_path.read_text(encoding='utf-8'))
    if not report.get('stage2_result'):
        print('[V7:QA:FAIL] Stage2 output not available')
        return 2
    a=Path(report['local_master_for_comparison'])
    b=Path(report['stage2_result']['path'])
    result=local_ollama_review(a,b,report['user_text'],url=args.ollama_url,model=args.model)
    (args.session/'qa_advisory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report['ollama_advisory']=result
    fields=result.get('fields')
    if fields:
        mapping={'identity_qa':('face_same','hair_same'),'outfit_qa':('outfit_same',),
                 'rendering_qa':('rendering_same',),'pose_qa':('pose_match',)}
        for name,keys in mapping.items():
            report[name]='ADVISORY_FAIL' if not all(fields[k] for k in keys) else 'ADVISORY_ONLY'
    if result['status']=='AUTOMATED_ADVISORY_FAIL':
        report['status']='REJECTED_AUTOMATED_ADVISORY'
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('[V7:QA:'+result['status']+']')
    print('[V7:QA:OUTPUT] '+str(args.session/'qa_advisory.json'))
    return 0 if result['status']!='QA_UNAVAILABLE' else 2


if __name__=='__main__':
    raise SystemExit(main())
