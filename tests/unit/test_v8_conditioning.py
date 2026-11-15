from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments'/'active'))
from v8_conditioning import (assess_qwen_pose_control,enforce_pose_control,validate_geometry_graph,
                             ConditioningError,REFERENCE_ONLY,UNSUPPORTED)
from v8_direct_pose_edit import build_direct_graph
from v7_geometry import request_from_text

MODEL='qwen_image_edit_2511_int8_convrot.safetensors'
TEXT='成人女性が真正面を向き、座っている状態で足をM字に開いて微笑んでいる'
INFO={'TextEncodeQwenImageEditPlus':{'input':{'required':{'clip':{},'prompt':{}},
    'optional':{'vae':{},'image1':{},'image2':{},'image3':{}}}},
    'ControlNetApplyAdvanced':{'input':{'required':{'positive':{},'negative':{},'control_net':{}}}}}

class TestV81Conditioning(unittest.TestCase):
    def graph(self):
        return build_direct_graph('V81_MASTER_abc.png','V81_POSE_ONLY_0123456789abcdef.png',
                                  'V81_MASTER_DETAILS_xyz.png',TEXT,request_from_text(TEXT))
    def test_qwen_is_reference_only_not_hard(self):
        a=assess_qwen_pose_control(INFO,MODEL)
        self.assertEqual(a.status,REFERENCE_ONLY)
        self.assertFalse(a.hard_pose_lock)
        self.assertFalse(a.mannequin_rgb_permitted)
    def test_generic_controlnet_is_not_evidence(self):
        with self.assertRaises(ConditioningError) as ctx:
            enforce_pose_control(assess_qwen_pose_control(INFO,MODEL))
        self.assertEqual(ctx.exception.code,'POSE_CONTROL_NOT_HARD')
    def test_reference_only_explicit_optin(self):
        enforce_pose_control(assess_qwen_pose_control(INFO,MODEL),allow_reference_only=True)
    def test_unknown_model_rejected(self):
        a=assess_qwen_pose_control(INFO,'sd_xl_base_1.0.safetensors')
        self.assertEqual(a.status,UNSUPPORTED)
        with self.assertRaises(ConditioningError): enforce_pose_control(a,allow_reference_only=True)
    def test_missing_encoder_rejected(self):
        self.assertEqual(assess_qwen_pose_control({},MODEL).status,UNSUPPORTED)
    def test_missing_image2_rejected(self):
        bad={'TextEncodeQwenImageEditPlus':{'input':{'required':{'clip':{},'prompt':{}},'optional':{'vae':{},'image1':{},'image3':{}}}}}
        self.assertEqual(assess_qwen_pose_control(bad,MODEL).status,UNSUPPORTED)
    def test_graph_image2_is_pose_derived(self):
        graph=self.graph()
        self.assertEqual(graph['7']['inputs']['image2'],['5',0])
        self.assertTrue(graph['5']['inputs']['image'].startswith('V81_POSE_ONLY_'))
        validate_geometry_graph(graph,master_name=graph['4']['inputs']['image'],
                                pose_guide_name=graph['5']['inputs']['image'],detail_name=graph['17']['inputs']['image'])
    def test_mannequin_raw_disallowed(self):
        graph=self.graph()
        graph['5']['inputs']['image']='V8_MANNEQUIN_opaque.png'
        with self.assertRaises(ConditioningError):
            validate_geometry_graph(graph,master_name=graph['4']['inputs']['image'],
                                    pose_guide_name=graph['5']['inputs']['image'],detail_name=graph['17']['inputs']['image'])
    def test_unknown_loadimage_rejected(self):
        graph=self.graph();graph['91']={'class_type':'LoadImage','inputs':{'image':'unsafe.png'}}
        with self.assertRaises(ConditioningError):
            validate_geometry_graph(graph,master_name=graph['4']['inputs']['image'],
                                    pose_guide_name=graph['5']['inputs']['image'],detail_name=graph['17']['inputs']['image'])
    def test_no_sdxl_stage(self):
        graph=self.graph();graph['92']={'class_type':'CheckpointLoaderSimple','inputs':{'ckpt_name':'x'}}
        with self.assertRaises(ConditioningError):
            validate_geometry_graph(graph,master_name=graph['4']['inputs']['image'],
                                    pose_guide_name=graph['5']['inputs']['image'],detail_name=graph['17']['inputs']['image'])

if __name__=='__main__':unittest.main()
