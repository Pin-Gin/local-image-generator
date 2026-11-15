from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments'/'active'))
sys.path.insert(0,str(ROOT/'src'))

from v8_direct_pose_edit import build_direct_graph, validate_direct_graph, v8_edit_prompt, V8GraphError
from v8_pipeline import previous_master_name,verify_source_master,main
from v7_geometry import request_from_text

TEXT='成人女性が真正面を向き、座っている状態で足をM字に開いて微笑んでいる'
POSE='V81_POSE_ONLY_0123456789abcdef.png'

class TestV81Direct(unittest.TestCase):
    def setUp(self):self.req=request_from_text(TEXT)
    def graph(self):return build_direct_graph('master.png',POSE,'details.png',TEXT,self.req)

    def test_identity_is_master_base(self):
        g=self.graph()
        self.assertEqual(g['4']['inputs']['image'],'master.png')
        self.assertEqual(g['7']['inputs']['image1'],['6',0])
        self.assertEqual(g['6']['inputs']['image'],['4',0])
        self.assertEqual(g['14']['inputs']['latent_image'],['13',0])
        self.assertEqual(g['13']['inputs']['pixels'],['6',0])

    def test_pose_only_not_mannequin_image2(self):
        g=self.graph()
        self.assertEqual(g['5']['inputs']['image'],POSE)
        self.assertEqual(g['7']['inputs']['image2'],['5',0])
        self.assertNotIn('mannequin.png',json.dumps(g))

    def test_identity_outfit_board_is_image3(self):
        g=self.graph()
        self.assertEqual(g['17']['inputs']['image'],'details.png')
        self.assertEqual(g['7']['inputs']['image3'],['17',0])

    def test_no_sdxl_generation(self):
        g=self.graph()
        self.assertNotIn('CheckpointLoaderSimple',{node['class_type'] for node in g.values()})
        self.assertNotIn('ControlNetApplyAdvanced',{node['class_type'] for node in g.values()})
        self.assertEqual(sum(n['class_type']=='KSampler' for n in g.values()),1)

    def test_negative_condition_has_all_references(self):
        g=self.graph()
        self.assertEqual(g['8']['inputs']['image1'],['6',0])
        self.assertEqual(g['8']['inputs']['image2'],['5',0])
        self.assertEqual(g['8']['inputs']['image3'],['17',0])

    def test_pose_warnings_preserved_in_prompt(self):
        prompt=v8_edit_prompt(TEXT,pose_warnings=['ANKLES_OUTSIDE_KNEES: differs from earlier specification'])
        self.assertIn('ankles outside the knees',prompt)
        self.assertIn(TEXT,prompt)
        self.assertIn('camisole',prompt)
        self.assertIn('OpenPose',prompt)

    def test_raw_mannequin_is_rejected(self):
        with self.assertRaises(V8GraphError):
            build_direct_graph('master.png','mannequin.png','details.png',TEXT,self.req)

    def test_workflow_source_requires_loadimage(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'wf.json'
            path.write_text(json.dumps({'30':{'class_type':'LoadImage','inputs':{'image':'POC_MAIN_12345678.png'}}}))
            self.assertEqual(previous_master_name(path),'POC_MAIN_12345678.png')

    def test_source_hash_protection(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'master.png';p.write_bytes(b'sample master')
            import hashlib
            digest=hashlib.sha256(b'sample master').hexdigest()
            verify_source_master(p,'POC_MAIN_'+digest[:12]+'.png')
            with self.assertRaises(Exception):verify_source_master(p,'POC_MAIN_deadbeefdead.png')

    def test_compilation_with_real_mannequin_fixture(self):
        mannequin=ROOT/'examples'/'mannequin_m_seated.png'
        pose_json=ROOT/'examples'/'mannequin_m_seated.pose.json'
        if not (mannequin.exists() and pose_json.exists()):
            self.skipTest('fixture not installed')
        with tempfile.TemporaryDirectory() as td:
            from PIL import Image
            sample=Path(td)/'master.png';Image.new('RGB',(928,1648),(210,200,195)).save(sample)
            rc=main(['--master',str(sample),'--pose-image',str(mannequin),'--pose-json',str(pose_json),'--text',TEXT])
            self.assertEqual(rc,0)
            outs=list((ROOT/'outputs'/'experiments'/'v8_1_structure').glob('*/diagnostic.json'))
            self.assertTrue(outs)
            newest=max(outs,key=lambda p:p.stat().st_mtime)
            d=json.loads(newest.read_text(encoding='utf-8'))
            self.assertEqual(d['status'],'COMPILED_UNVERIFIED')
            self.assertEqual(d['architecture']['sdxl_stage1'],'DISABLED')
            self.assertFalse(d['architecture']['mannequin_rgb_forwarding'])
            self.assertTrue(d['geometry']['source_image_hash_verified'])
            self.assertIn('ANKLES_OUTSIDE_KNEES',','.join(d['geometry']['warnings']))
            g=json.loads(Path(d['graph_path']).read_text(encoding='utf-8'))
            validate_direct_graph(g)
            self.assertTrue(g['5']['inputs']['image'].startswith('V81_POSE_ONLY_'))
            self.assertNotIn('V8_MANNEQUIN_',json.dumps(g))
            # Reference-only preflight must fail closed unless opted in.
            fake={'TextEncodeQwenImageEditPlus':{'input':{'required':{'clip':{},'prompt':{}},
                  'optional':{'vae':{},'image1':{},'image2':{},'image3':{}}}}}
            with patch('v8_pipeline.fetch_object_info',return_value=fake),patch('v8_pipeline.validate_runtime',return_value=None):
                rc2=main(['--master',str(sample),'--pose-image',str(mannequin),'--pose-json',str(pose_json),'--text',TEXT,'--preflight'])
                self.assertEqual(rc2,2)

if __name__=='__main__':unittest.main()
