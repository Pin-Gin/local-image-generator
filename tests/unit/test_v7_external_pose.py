"""v7 external mannequin image / pose JSON data-contract tests.

Requires Pillow only; ComfyUI GPU cannot be verified in this test environment.
"""
from __future__ import annotations

import copy
import hashlib
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
ACTIVE=ROOT/'experiments'/'active'
if str(ACTIVE) not in sys.path:sys.path.insert(0,str(ACTIVE))

import v7_external_pose as pose

SAMPLE=ROOT/'examples'/'mannequin_m_seated.pose.json'
IMAGE=ROOT/'examples'/'mannequin_m_seated.png'

class TestExternalPose(unittest.TestCase):
    def test_image_sha_matches_sample_json(self):
        self.assertEqual(pose.sha256(IMAGE),json.loads(SAMPLE.read_text(encoding='utf-8'))['source_image_sha256'])

    def test_sample_loads_and_preserves_warning(self):
        with Image.open(IMAGE) as im:w,h=im.size
        d=pose.parse_pose_json(json.loads(SAMPLE.read_text(encoding='utf-8')),
            source_width=w,source_height=h,source_sha256=pose.sha256(IMAGE))
        self.assertIn('ANKLES_OUTSIDE_KNEES',d['warnings'][0])
        self.assertEqual(d['depth_status'],'UNKNOWN_2D_IMAGE_ONLY')
        self.assertEqual(d['review_status'],'NEEDS_HUMAN_REVIEW')

    def test_renders_and_overlay(self):
        with tempfile.TemporaryDirectory() as d:
            doc,out=pose.prepare_external_pose(pose_image=IMAGE,pose_json=SAMPLE,
                output_dir=Path(d),comfy_url='http://unused')
            self.assertTrue(out.is_file())
            self.assertTrue((Path(d)/'keypoint_overlay.png').exists())
            with Image.open(out) as im:self.assertEqual(im.size,(896,960))
            self.assertEqual(doc['source_type'],'estimated_from_user_supplied_2d_mannequin')
            self.assertTrue((Path(d)/'external_pose.json').exists())

    def test_wrong_image_sha_rejected(self):
        d=json.loads(SAMPLE.read_text(encoding='utf-8'))
        with self.assertRaises(pose.PoseImportError) as err:
            pose.parse_pose_json(d,source_width=1218,source_height=1292,source_sha256='0'*64)
        self.assertEqual(err.exception.code,'POSE_SOURCE_HASH_MISMATCH')

    def test_wrong_dimensions_rejected(self):
        d=json.loads(SAMPLE.read_text(encoding='utf-8'))
        with self.assertRaises(pose.PoseImportError):
            pose.parse_pose_json(d,source_width=1000,source_height=800)

    def test_missing_knee_rejected(self):
        d=json.loads(SAMPLE.read_text(encoding='utf-8'))
        d['keypoints']['right_knee']=None
        with self.assertRaises(pose.PoseImportError) as err:pose.parse_pose_json(d)
        self.assertEqual(err.exception.code,'POSE_CORE_JOINTS_MISSING')

    def test_coordinates_outside_canvas_rejected(self):
        d=json.loads(SAMPLE.read_text(encoding='utf-8'))
        d['keypoints']['right_knee']['x']=-5
        with self.assertRaises(pose.PoseImportError):pose.parse_pose_json(d)

    def test_native_openpose_18_and_flat_input(self):
        d=json.loads(SAMPLE.read_text(encoding='utf-8'))
        coords=d['keypoints']
        flat=[]
        for key in pose.JOINTS:
            p=coords[key]
            flat.extend([p['x'],p['y'],p['confidence']] if p else [0,0,0])
        raw={'people':[{'pose_keypoints_2d':flat}],'canvas_width':1218,'canvas_height':1292}
        doc=pose.parse_pose_json([raw])
        self.assertEqual(doc['source_type'],'dwpose_estimated')
        self.assertAlmostEqual(doc['keypoints']['right_knee']['x'],coords['right_knee']['x'])

    def test_native_multiple_people_rejected(self):
        with self.assertRaises(pose.PoseImportError) as err:
            pose.parse_pose_json({'people':[{},{}],'canvas_width':1218,'canvas_height':1292})
        self.assertEqual(err.exception.code,'POSE_PERSON_COUNT_INVALID')

    def test_native_coco17_correct_mapping(self):
        d=json.loads(SAMPLE.read_text(encoding='utf-8'))['keypoints']
        kps=[]
        for name in pose.COCO17:
            p=d.get(name)
            kps.append([p['x'],p['y'],p['confidence']] if p else [0,0,0])
        raw={'people':[{'pose_keypoints_2d':kps}],'canvas_width':1218,'canvas_height':1292}
        doc=pose.parse_pose_json(raw)
        self.assertEqual(doc['keypoints']['right_shoulder']['x'],d['right_shoulder']['x'])
        self.assertEqual(doc['keypoints']['right_ankle']['y'],d['right_ankle']['y'])
        self.assertIsNotNone(doc['keypoints']['neck'])
        self.assertEqual(doc['keypoints']['neck']['observability'],'inferred_midpoint')

    def test_preprocessor_graph_uses_real_dwpose_node(self):
        example={'DWPreprocessor':{'input':{'required':{
          'image':['IMAGE'], 'detect_hand':[['enable','disable']],
          'detect_body':[['enable','disable']], 'detect_face':[['enable','disable']],
          'resolution':['INT',{'default':1024}],
          'bbox_detector':[['None','yolox_l.onnx']],
          'pose_estimator':[['dw-ll_ucoco_384_bs5.torchscript.pt']],
          'scale_stick_for_xinsr_cn':[['disable','enable']]}}}}
        ins=pose._dwpose_args(example,'test.png',1024)
        self.assertEqual(ins['image'],['1',0])
        self.assertEqual(ins['bbox_detector'],'yolox_l.onnx')
        self.assertEqual(ins['pose_estimator'],'dw-ll_ucoco_384_bs5.torchscript.pt')

    def test_inference_called_for_image_only(self):
        doc=pose.parse_pose_json(json.loads(SAMPLE.read_text(encoding='utf-8')))
        with tempfile.TemporaryDirectory() as d,patch.object(pose,'infer_pose_with_comfy',return_value=doc) as est:
            out,_=pose.prepare_external_pose(pose_image=IMAGE,pose_json=None,
                output_dir=Path(d),comfy_url='http://localhost:8188')
            est.assert_called_once()
            self.assertIn('warnings',out)

    def test_v7_pipeline_prepares_external_without_comfy(self):
        import v7_pipeline as v7
        legacy=ROOT/'examples'/'v2_legacy_template.fixture.json'
        text='成人女性が真正面を向き、座っている状態で足をM字に開いて微笑んでいる'
        with tempfile.TemporaryDirectory() as d, patch.object(v7,'ROOT',Path(d)):
            status=v7.main(['--source',str(legacy),'--text',text,
                            '--pose-image',str(IMAGE),'--pose-json',str(SAMPLE),
                            '--prepare-pose'])
            self.assertEqual(status,0)
            results=list(Path(d).glob('outputs/experiments/v7_hybrid/*/diagnostic.json'))
            self.assertEqual(len(results),1)
            record=json.loads(results[0].read_text(encoding='utf-8'))
            self.assertEqual(record['status'],'POSE_PREPARED_REVIEW_REQUIRED')
            self.assertEqual(record['external_pose']['canvas'],{'width':896,'height':960})
            self.assertTrue(Path(record['external_pose']['rendered_openpose_path']).is_file())

    def test_v7_stage1_graph_uses_external_guide_and_canvas(self):
        import v7_pipeline as v7
        legacy=ROOT/'examples'/'v2_legacy_template.fixture.json'
        text='成人女性が真正面を向き、座っている状態で足をM字に開いて微笑んでいる'
        with tempfile.TemporaryDirectory() as d, patch.object(v7,'ROOT',Path(d)):
            status=v7.main(['--source',str(legacy),'--text',text,
                            '--pose-image',str(IMAGE),'--pose-json',str(SAMPLE),
                            '--stage','pose'])
            self.assertEqual(status,0)
            files=list(Path(d).glob('outputs/experiments/v7_hybrid/*/stage1_geometry_api.json'))
            self.assertEqual(len(files),1)
            graph=json.loads(files[0].read_text(encoding='utf-8'))
            self.assertEqual(graph['2']['inputs']['width'],896)
            self.assertEqual(graph['2']['inputs']['height'],960)
            self.assertIn('V7_EXTERNAL_POSE_',graph['20']['inputs']['image'])
            self.assertEqual(graph['23']['inputs']['image'],['20',0])
            self.assertEqual(graph['7']['inputs']['positive'],['23',0])

    def test_stage2_external_pose_has_priority_over_generic_leg_phrase(self):
        import v7_pipeline as v7
        parsed={'pose':{'id':'seated_m','view':'front'},'deltas':{'expression':'soft_smile'}}
        prompt=v7.stage2_prompt('成人女性が真正面を向き、座っている状態で足をM字に開いて微笑んでいる',parsed,external_pose=True)
        self.assertIn('exact joint relationships seen in IMAGE 1',prompt)
        self.assertIn('do not reinterpret the external skeleton',prompt)

if __name__=='__main__':unittest.main()
