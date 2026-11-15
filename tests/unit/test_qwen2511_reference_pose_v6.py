from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / 'experiments' / 'active' / 'qwen2511_reference_pose_v6.py'
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location('qwen2511_reference_pose_v6', SCRIPT)
v6 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = v6
spec.loader.exec_module(v6)

TEXT = '成人女性が真正面を向き、座っている状態で足をM字に開いて微笑んでいる'

def fake_info(graph):
    output = {
        'UNETLoader': ['MODEL'], 'CLIPLoader': ['CLIP'], 'VAELoader': ['VAE'], 'LoadImage': ['IMAGE'],
        'FluxKontextImageScale': ['IMAGE'], 'TextEncodeQwenImageEditPlus': ['CONDITIONING'],
        'FluxKontextMultiReferenceLatentMethod': ['CONDITIONING'], 'ModelSamplingAuraFlow': ['MODEL'],
        'CFGNorm': ['MODEL'], 'VAEEncode': ['LATENT'], 'KSampler': ['LATENT'], 'VAEDecode': ['IMAGE'],
        'SaveImage': [],
    }
    info = {}
    for node in graph.values():
        t = node['class_type']
        if t not in info:
            names = {k for n in graph.values() if n['class_type'] == t for k in n['inputs']}
            info[t] = {
                'input': {'required': {name: ['*'] for name in names}},
                'input_order': {'required': list(names)},
                'output': output[t],
                'output_name': output[t],
            }
    for t, attr, val in [('UNETLoader', 'unet_name', v6.DEFAULT_MODEL), ('CLIPLoader','clip_name',v6.DEFAULT_CLIP),('VAELoader','vae_name',v6.DEFAULT_VAE)]:
        info[t]['input']['required'][attr] = [[val]]
    return info

class Tests(unittest.TestCase):
    def setUp(self):
        # Tests require the previously installed built-in pose module.
        self.request = v6.resolve_pose(TEXT)
        self.g = v6.build_graph('main.png', 'pose.png', TEXT, self.request)

    def test_text_has_complete_grammar(self):
        self.assertEqual(self.request['interpretation']['coverage'], 'COMPLETE_FOR_POC')
        self.assertEqual(self.request['pose']['id'], 'seated_m')

    def test_graph_native_nodes(self):
        self.assertEqual(len(self.g), 16)
        self.assertEqual(self.g['7']['class_type'], 'TextEncodeQwenImageEditPlus')
        self.assertEqual(self.g['14']['inputs']['positive'], ['9', 0])
        self.assertEqual(self.g['14']['inputs']['negative'], ['10', 0])
        self.assertEqual(self.g['14']['inputs']['latent_image'], ['13', 0])
        self.assertFalse({'IPAdapterAdvanced','ControlNetApplyAdvanced','CheckpointLoaderSimple'} & {v['class_type'] for v in self.g.values()})

    def test_pose_is_image2(self):
        self.assertEqual(self.g['7']['inputs']['image1'], ['6', 0])
        self.assertEqual(self.g['7']['inputs']['image2'], ['5', 0])
        self.assertIn(TEXT, self.g['7']['inputs']['prompt'])
        self.assertIn('ONLY an OpenPose skeleton', self.g['7']['inputs']['prompt'])

    def test_third_face_reference_is_same_master_crop(self):
        g = v6.build_graph('main.png','pose.png',TEXT,self.request,face_name='face.png')
        self.assertEqual(g['7']['inputs']['image3'], ['17', 0])
        self.assertEqual(g['8']['inputs']['image3'], ['17', 0])
        self.assertEqual(g['17']['class_type'], 'LoadImage')
        self.assertIn('SAME Image 1', g['7']['inputs']['prompt'])

    def test_bad_link_rejected(self):
        bad = json.loads(json.dumps(self.g))
        bad['14']['inputs']['positive'] = ['999', 0]
        with self.assertRaises(v6.V6Error):
            v6.ensure_graph(bad)

    def test_static_runtime_gate(self):
        v6.validate_runtime(self.g, fake_info(self.g))

    def test_missing_model(self):
        info = fake_info(self.g)
        info['UNETLoader']['input']['required']['unet_name'] = [['other.safetensors']]
        with self.assertRaisesRegex(v6.V6Error, 'qwen_image_edit_2511'):
            v6.validate_runtime(self.g, info)

    def test_missing_custom_node(self):
        info = fake_info(self.g)
        del info['TextEncodeQwenImageEditPlus']
        with self.assertRaisesRegex(v6.V6Error, 'TextEncodeQwenImageEditPlus'):
            v6.validate_runtime(self.g, info)

    def test_ui_graph_from_runtime_metadata(self):
        info = fake_info(self.g)
        ui = v6.ui_graph(self.g, info)
        self.assertEqual(len(ui['nodes']),len(self.g))
        self.assertEqual(ui['last_link_id'], len(ui['links']))
        self.assertTrue(any(x['type']=='TextEncodeQwenImageEditPlus' for x in ui['nodes']))
        for link in ui['links']:
            self.assertIn(link[1], {n['id'] for n in ui['nodes']})
            self.assertIn(link[3], {n['id'] for n in ui['nodes']})

    def test_reused_session_pose_only_m(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'compiled_workflow.json'
            p.write_text(json.dumps({'30':{'class_type':'LoadImage','inputs':{'image':'POC_MAIN_a.png'}},'20':{'class_type':'LoadImage','inputs':{'image':'POC_POSE_5c878552a3ff.png'}}}),encoding='utf-8')
            v6.require_same_pose(p,self.request)
            self.assertEqual(v6.get_previous_names(p), ('POC_MAIN_a.png','POC_POSE_5c878552a3ff.png'))

    def test_source_pose_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'compiled_workflow.json'
            p.write_text(json.dumps({'30':{'class_type':'LoadImage','inputs':{'image':'POC_MAIN_a.png'}},
                                     '20':{'class_type':'LoadImage','inputs':{'image':'POC_POSE_wrong.png'}}}),encoding='utf-8')
            with self.assertRaises(v6.V6Error):
                v6.require_same_pose(p,self.request)

    def test_visual_review_sheet_is_not_a_score(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            a=Path(td)/'a.png'; b=Path(td)/'b.png'; out=Path(td)/'sheet.png'
            Image.new('RGB',(900,1600),'white').save(a)
            Image.new('RGB',(768,1344),'black').save(b)
            v6.create_review_sheet(a,b,out)
            self.assertTrue(out.is_file())

    def test_no_silent_unsupported_pose(self):
        with self.assertRaises(v6.V6Error):
            v6.resolve_pose('成人女性が仰向けになる')

    def test_auto_cropped_head_documented_not_face_detector(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'source.png'; dst=Path(td)/'head.png'
            Image.new('RGB',(900,1600),'white').save(src)
            meta=v6.crop_head_from_master(src,dst)
            self.assertTrue(dst.is_file())
            self.assertIn('not_face_detection',meta['method'])
            self.assertEqual(meta['sha256'],v6.digest(dst))

    def test_raises_on_incompatible_photo_crop(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'source.png'; dst=Path(td)/'head.png'
            Image.new('RGB',(800,600),'white').save(src)
            with self.assertRaises(v6.V6Error):
                v6.crop_head_from_master(src,dst)

if __name__ == '__main__':
    unittest.main()
