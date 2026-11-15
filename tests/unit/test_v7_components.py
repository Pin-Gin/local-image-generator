import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ACTIVE=Path(__file__).resolve().parents[2]/'experiments'/'active'
if str(ACTIVE) not in sys.path: sys.path.insert(0,str(ACTIVE))

from v7_references import make_reference_bundle, ReferenceError, sha256
from v7_geometry import (load_legacy_graph, make_stage1_graph,
                         request_from_text, pose_phrase, GeometryError)
from v7_quality import review_sheet, QA_FIELDS
from v7_pipeline import make_stage2_graph, stage2_prompt, V7Error

SAMPLE=Path(__file__).resolve().parents[2]/'examples'/'v2_legacy_template.fixture.json'
TEXT='成人女性が真正面を向き、座っている状態で足をM字に開いて微笑んでいる'
REQ={'pose': {'id':'seated_m','view':'front'},'deltas': {'expression':'soft_smile'}}

class TestV7Components(unittest.TestCase):
    def test_master_outfit_face_bundle(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            source=root/'source.png'
            Image.new('RGB',(928,1650),(202,190,172)).save(source)
            data=make_reference_bundle(source,root/'refs')
            self.assertEqual(data['master_sha256'],sha256(source))
            self.assertTrue(Path(data['identity']['face_hair_crop']).is_file())
            self.assertTrue(Path(data['outfit']['reference_crop']).is_file())
            self.assertTrue(Path(data['reference_sheet']['path']).is_file())
            self.assertEqual(data['reference_image_training'],'NONE')
            self.assertFalse(data['outfit_hard_lock'])

    def test_bundle_layout_refuses_incompatible(self):
        with tempfile.TemporaryDirectory() as t:
            s=Path(t)/'square.png';Image.new('RGB',(1000,1000)).save(s)
            with self.assertRaises(ReferenceError):
                make_reference_bundle(s,Path(t)/'out')

    def test_stage1_is_real_controlnet(self):
        legacy,_,_=load_legacy_graph(SAMPLE)
        g=make_stage1_graph(legacy,'test_guide.png','seated_m')
        self.assertEqual(g['7']['inputs']['model'],['1',0])
        self.assertEqual(g['7']['inputs']['positive'],['23',0])
        self.assertEqual(g['23']['inputs']['image'],['20',0])
        self.assertEqual(g['20']['inputs']['image'],'test_guide.png')
        self.assertEqual(g['7']['inputs']['seed'],975311)
        self.assertNotIn('40',g)
        self.assertNotIn('41',g)
        self.assertNotIn('42',g)

    def test_stage1_explicit_floor_contact(self):
        self.assertIn('floor',pose_phrase('seated_m'))
        legacy,_,_=load_legacy_graph(SAMPLE)
        g=make_stage1_graph(legacy,'pose.png','seated_m')
        self.assertIn('sitting',g['3']['inputs']['text'])
        self.assertIn('cross-legged',g['6']['inputs']['text'])

    def test_stage2_references_three_roles(self):
        g=make_stage2_graph('geometry.png','master.png','face_and_outfit.png',TEXT,REQ,
                            model='qwen_image_edit_2511_int8_convrot.safetensors',
                            clip='qwen_2.5_vl_7b_fp8_scaled.safetensors',
                            vae='qwen_image_vae.safetensors',seed=9,steps=20,cfg=4.0)
        self.assertEqual(g['4']['inputs']['image'],'geometry.png')
        self.assertEqual(g['5']['inputs']['image'],'master.png')
        self.assertEqual(g['17']['inputs']['image'],'face_and_outfit.png')
        self.assertEqual(g['14']['inputs']['latent_image'],['13',0])
        prompt=g['7']['inputs']['prompt']
        self.assertIn('IMAGE 1 is the posed CANVAS',prompt)
        self.assertIn('IMAGE 2 is the ORIGINAL MASTER',prompt)
        self.assertIn('IMAGE 3 contains two close-up crops',prompt)
        self.assertIn(TEXT,prompt)
        self.assertNotIn('OpenPose skeleton layout guide',prompt)

    def test_no_hard_pose_claim_for_qwen_edit(self):
        p=stage2_prompt(TEXT,REQ)
        self.assertIn('Keep ONLY its geometric pose',p)
        self.assertNotIn('ControlNetApplyAdvanced',p)

    def test_review_image(self):
        with tempfile.TemporaryDirectory() as t:
            t=Path(t);a=t/'a.png';b=t/'b.png';out=t/'review.png'
            Image.new('RGB',(900,1600)).save(a);Image.new('RGB',(600,900)).save(b)
            review_sheet(a,b,out)
            self.assertTrue(out.exists())
            with Image.open(out) as image:
                self.assertEqual(image.size,(1200,1005))

    def test_invalid_pose_fails(self):
        with self.assertRaises(GeometryError):
            pose_phrase('arbitrary_unknown_pose')

    def test_qa_fields_are_separate(self):
        self.assertIn('outfit_same',QA_FIELDS)
        self.assertIn('face_same',QA_FIELDS)
        self.assertIn('pose_match',QA_FIELDS)
        self.assertIn('rendering_same',QA_FIELDS)

if __name__=='__main__': unittest.main()
