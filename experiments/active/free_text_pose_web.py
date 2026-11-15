"""LOCALHOST-ONLY diagnostic UI for free_text_pose_poc.py. No training.

Not production. Only the optional Generate button runs local ComfyUI.
"""
from __future__ import annotations

import argparse
import base64
import binascii
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
import re
import secrets
import traceback
from urllib.parse import urlsplit

from PIL import Image
import free_text_pose_poc as poc

ROOT = Path(__file__).resolve().parents[2]
SESSIONS = ROOT / 'outputs' / 'experiments' / 'text_pose_web'
MAX_BODY = 18 * 1024 * 1024
MAX_IMAGE = 12 * 1024 * 1024

HTML = '''<!doctype html><html lang="ja"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>local-image-generator | ONE MASTER PoC</title>
<style>
:root{font-family:system-ui,"Yu Gothic",sans-serif;background:#111520;color:#ebedf2}
*{box-sizing:border-box}main{max-width:1000px;margin:2rem auto;padding:1rem}
h1{font-size:1.55rem}p{color:#b0bac9}section{background:#202737;border:1px solid #364055;padding:1.5rem;border-radius:16px;margin:1rem 0}
textarea,input{width:100%;background:#141925;color:#fff;border:1px solid #606b7a;padding:.85rem;border-radius:9px}
textarea{height:100px;resize:vertical}button{background:#5b8ffb;color:#fff;padding:.85rem 1.4rem;border:0;border-radius:9px;font-weight:600;cursor:pointer}
button[disabled]{opacity:.5}.two{display:grid;grid-template-columns:1fr 1fr;gap:1rem}img{max-width:100%;max-height:600px;object-fit:contain}
pre{white-space:pre-wrap;overflow-wrap:anywhere;color:#c3cee1}label{display:block;margin:1rem 0 .35rem}
@media(max-width:700px){.two{grid-template-columns:1fr}}
</style>
<main><h1>Master × Japanese prompt <small>(Phase 2 PoC)</small></h1>
<p>最低入力はマスター1枚＋日本語1文です。品質・安全判定は未実装。対応ポーズ以外は置換せずエラーにします。</p>
<section><label>マスター画像（ローカルのみ）</label><input type="file" id="master" accept="image/png,image/jpeg,image/webp">
<label>日本語指示</label><textarea id="prompt">成人女性が真正面を向き、座っている状態で足をM字に開いて微笑んでいる</textarea>
<div style="display:flex;gap:.8rem;flex-wrap:wrap;margin-top:1rem">
<button id="preview">骨格だけ検証</button><button id="generate">ComfyUIで実際に生成</button></div>
<p>ComfyUIで生成を押すと、既存SDXL/IP-Adapter/ControlNetを使用します。実機での生成成功や同一人物性は未検証です。</p></section>
<div class="two"><section><h2>内部ポーズ画像</h2><img id="pose" alt="Generated OpenPose guide"></section>
<section><h2>画像モデル出力</h2><img id="output" alt="ComfyUI output"></section></div>
<section><h2>診断結果</h2><pre id="result">未実行</pre></section></main>
<script>
async function go(mode){
 const file=document.getElementById('master').files[0];
 const result=document.getElementById('result');
 if(!file){result.textContent='マスター画像を選択してください';return;}
 if(file.size>12*1024*1024){result.textContent='画像は12MiB以下にしてください';return;}
 const buttons=['preview','generate'].map(x=>document.getElementById(x));buttons.forEach(x=>x.disabled=true);
 result.textContent='処理中...';
 try{
   const data=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=()=>reject(r.error);r.readAsDataURL(file)});
   const response=await fetch('/api/'+mode,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image_data_url:data,text:document.getElementById('prompt').value})});
   const doc=await response.json();result.textContent=JSON.stringify(doc,null,2);
   if(doc.session_id){document.getElementById('pose').src='/api/image/'+doc.session_id+'/pose';
      document.getElementById('output').src=doc.generation?'/api/image/'+doc.session_id+'/output':''}
 }catch(e){result.textContent=String(e)}finally{buttons.forEach(x=>x.disabled=false)}
}
document.getElementById('preview').onclick=()=>go('preview');
document.getElementById('generate').onclick=()=>go('generate');
</script></html>'''


def make_session(text: str, image_data_url: str, generate: bool = False) -> dict:
    if not image_data_url.startswith('data:image/') or ';base64,' not in image_data_url:
        raise poc.PocError('INPUT_ERROR','画像のdata URLが不正です')
    meta, payload=image_data_url.split(';base64,',1)
    if meta not in ('data:image/png','data:image/jpeg','data:image/webp'):
        raise poc.PocError('INPUT_ERROR','PNG/JPEG/WebPのいずれかを指定してください')
    try:
        binary=base64.b64decode(payload,validate=True)
    except (binascii.Error,ValueError) as exc:
        raise poc.PocError('INPUT_ERROR','画像のbase64が不正です') from exc
    if not binary or len(binary)>MAX_IMAGE:
        raise poc.PocError('INPUT_ERROR','画像が空または12MiBを超えています')
    try:
        with Image.open(BytesIO(binary)) as check:
            if check.format.lower() != meta.removeprefix('data:image/').replace('jpeg','jpeg'):
                raise poc.PocError('INPUT_ERROR','宣言形式と実データ形式が一致しません')
            width,height=check.size
            if not 32<=width<=5000 or not 32<=height<=5000 or width*height>20_000_000:
                raise poc.PocError('INPUT_ERROR','画像サイズが診断上限を超えています')
            check.verify()
    except (OSError,ValueError) as exc:
        raise poc.PocError('INPUT_ERROR','画像を読み込めません') from exc
    request=poc.classify_request(text)
    if generate and request['interpretation']['coverage']!='COMPLETE_FOR_POC':
        raise poc.PocError('UNRESOLVED_SEMANTICS','未対応の指定を黙って無視しないため、生成を停止しました')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
    session_id=stamp+'_'+secrets.token_hex(8)
    out=SESSIONS/session_id
    out.mkdir(parents=True,exist_ok=False)
    ext={'data:image/png':'.png','data:image/jpeg':'.jpg','data:image/webp':'.webp'}[meta]
    master=out/('master'+ext)
    master.write_bytes(binary)
    pose=out/'pose.png'
    poc.render_pose(request['pose']['id'],pose)
    output={'session_id':session_id,'status':'POSE_GUIDE_CREATED',
            'request':request,'master_sha256':poc.hash_file(master),
            'pose_sha256':poc.hash_file(pose),
            'safety_qa':'NOT_PERFORMED','identity_qa':'NOT_PERFORMED',
            'rendering_qa':'NOT_PERFORMED'}
    if generate:
        result=poc.generate(ROOT,master,pose,request,out,975311)
        output['generation']=result
        output['status']='GENERATED_UNVERIFIED'
    (out/'manifest.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return output


class Handler(BaseHTTPRequestHandler):
    def respond(self, status: int, value: dict) -> None:
        payload=json.dumps(value,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(payload)))
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        path=urlsplit(self.path).path
        if path=='/':
            raw=HTML.encode('utf-8')
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        matched=re.fullmatch(r'/api/image/(\d{8}T\d{6}_[0-9a-f]{16})/(pose|output)',path)
        if not matched:
            self.send_error(HTTPStatus.NOT_FOUND);return
        session_id,kind=matched.groups()
        root=(SESSIONS/session_id).resolve()
        if not root.is_relative_to(SESSIONS.resolve()):
            self.send_error(HTTPStatus.FORBIDDEN);return
        if kind=='pose':
            target=root/'pose.png'
        else:
            manifest=root/'manifest.json'
            if not manifest.is_file():
                self.send_error(HTTPStatus.NOT_FOUND);return
            data=json.loads(manifest.read_text(encoding='utf-8'))
            result=data.get('generation')
            if not isinstance(result,dict):
                self.send_error(HTTPStatus.NOT_FOUND);return
            target=Path(result['output_path']).resolve()
            if not target.is_relative_to(root):
                self.send_error(HTTPStatus.FORBIDDEN);return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND);return
        raw=target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type','image/png' if target.suffix.lower()=='.png' else 'image/jpeg')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:
        path=urlsplit(self.path).path
        if path not in ('/api/preview','/api/generate'):
            self.send_error(HTTPStatus.NOT_FOUND);return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>MAX_BODY:
                raise poc.PocError('INPUT_ERROR','リクエストが空または18MiBを超えています')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict) or not isinstance(data.get('text'),str) or not isinstance(data.get('image_data_url'),str):
                raise poc.PocError('INPUT_ERROR','image_data_urlとtextが必要です')
            result=make_session(data['text'],data['image_data_url'],generate=path=='/api/generate')
            self.respond(HTTPStatus.OK,result)
        except poc.PocError as exc:
            self.respond(HTTPStatus.UNPROCESSABLE_ENTITY,{'status':'FAIL','error_type':exc.code,'message':str(exc)})
        except Exception as exc:
            self.respond(HTTPStatus.INTERNAL_SERVER_ERROR,{'status':'FAIL','error_type':'RUNTIME_ERROR','message':str(exc)})


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8766)
    args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'[TEXT-POSE-WEB:READY] http://127.0.0.1:{args.port}')
    print('Press Ctrl+C to stop')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__':main()
