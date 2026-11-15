"""End-to-end orchestrator test with mock ComfyUI; no GPU or network used."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image

ACTIVE=Path(__file__).resolve().parents[2]/'experiments'/'active'
if str(ACTIVE) not in sys.path: sys.path.insert(0,str(ACTIVE))

import v7_pipeline as v7
from v7_geometry import load_legacy_graph, make_stage1_graph

FIXTURE=Path(__file__).resolve().parents[2]/'examples'/'v2_legacy_template.fixture.json'
TEXT='成人女性が真正面を向き、座っている状態で足をM字に開いて微笑んでいる'


def create_object_info():
    legacy,_,_=load_legacy_graph(FIXTURE)
    stage1=make_stage1_graph(legacy,'pose.png','seated_m')
    graph2=v7.make_stage2_graph('canvas.png','master.png','ref.png',TEXT,
        {'pose':{'id':'seated_m'},'deltas':{'expression':'soft_smile'}},
        model='qwen_image_edit_2511_int8_convrot.safetensors',
        clip='qwen_2.5_vl_7b_fp8_scaled.safetensors',
        vae='qwen_image_vae.safetensors',seed=975311,steps=20,cfg=4.)
    info={}
    for graph in (stage1,graph2):
        for node in graph.values():
            typ=node['class_type']
            ins=info.setdefault(typ, {'input':{'required':{},'optional':{},'hidden':{}},'output':['*']})['input']['required']
            for k,val in node['inputs'].items():
                ins[k]=['STRING']
    for graph in (stage1,graph2):
        for node in graph.values():
            for value in node['inputs'].values():
                if isinstance(value,list) and len(value)==2 and isinstance(value[0],str):
                    source=graph[value[0]]['class_type']
                    while len(info[source]['output'])<=value[1]:
                        info[source]['output'].append('*')
    for node in (stage1['1'],stage1['22'],graph2['1'],graph2['2'],graph2['3']):
        ty=node['class_type']
        for k in ('ckpt_name','control_net_name','unet_name','clip_name','vae_name'):
            if k in node['inputs']:
                info[ty]['input']['required'][k]=[[node['inputs'][k]]]
    return info


class TestV7MockRun(unittest.TestCase):
    def test_two_stages_execute_independently(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            master=root/'master.png'; Image.new('RGB',(928,1650),(201,190,180)).save(master)
            info=create_object_info()
            from qwen2511_reference_pose_v6 import build_graph, ensure_graph, validate_runtime, ui_graph
            def fake_module():
                return build_graph,ensure_graph,validate_runtime,ui_graph,lambda _:info
            def fake_upload(base_url, source,remote_name=None,timeout_seconds=None):
                return remote_name or Path(source).name
            calls=[]
            def fake_run(base_url, graph, output_dir, request_timeout_seconds=60,generation_timeout_seconds=900):
                calls.append({k:v['class_type'] for k,v in graph.items()})
                output_dir.mkdir(parents=True,exist_ok=True)
                target=output_dir/'sample.png'
                Image.new('RGB',(768,1344),(225,220,215)).save(target)
                return SimpleNamespace(prompt_id='mock_'+str(len(calls)),output_path=target)
            def fake_comfy():
                return lambda _:None, fake_upload, None, fake_run
            # Avoid reusing the project's absolute outputs path in unit tests.
            with patch.object(v7,'ROOT',root), patch.object(v7,'_model_module',fake_module),patch.object(v7,'_comfy',fake_comfy):
                status=v7.main(['--master',str(master),'--template',str(FIXTURE),'--text',TEXT,'--run','--make-ui'])
            self.assertEqual(status,0)
            self.assertEqual(len(calls),2)
            self.assertIn('ControlNetApplyAdvanced',calls[0].values())
            self.assertNotIn('ControlNetApplyAdvanced',calls[1].values())
            self.assertIn('TextEncodeQwenImageEditPlus',calls[1].values())
            outputs=list((root/'outputs'/'experiments'/'v7_hybrid').glob('*/diagnostic.json'))
            self.assertEqual(len(outputs),1)
            record=json.loads(outputs[0].read_text(encoding='utf-8'))
            self.assertEqual(record['status'],'GENERATED_UNVERIFIED')
            self.assertEqual(record['identity_qa'],'NOT_PERFORMED')
            self.assertTrue((outputs[0].parent/'comparison.png').is_file())
            self.assertTrue((outputs[0].parent/'stage2_identity_outfit_api.json').is_file())
            self.assertTrue((outputs[0].parent/'stage1_geometry_ui.json').is_file())
            self.assertTrue((outputs[0].parent/'stage2_identity_outfit_ui.json').is_file())

if __name__=='__main__':unittest.main()
