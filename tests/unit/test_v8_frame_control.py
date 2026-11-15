"""v8.2 frame mapping / no appearance regression tests. All offline."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments'/'active'))
sys.path.insert(0,str(ROOT/'src'))
from v8_frame_control import (FramingError, match_master_canvas, load_frame_anchors, reframe_external_guide)
from v8_pose_structure import build_pose_package
from v8_direct_pose_edit import build_direct_graph, v8_edit_prompt
from v7_geometry import request_from_text
from v8_pipeline import main

MANNEQUIN=ROOT/'examples'/'mannequin_m_seated.png'
POSE=ROOT/'examples'/'mannequin_m_seated.pose.json'
FRAME=ROOT/'examples'/'mannequin_m_seated.frame.json'
TEXT='成人女性が真正面を向き、座っている状態で足をM字に開いて微笑んでいる'


class TestV82Frame(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.d=Path(self.temp.name)
        self.master=self.d/'master.png'
        Image.new('RGB',(941,1672),(204,192,180)).save(self.master)

    def test_master_aspect_canvas(self):
        self.assertEqual(match_master_canvas(self.master),(768,1344))
        self.assertLess(abs((768/1344)/(941/1672)-1),0.035)

    def test_external_toe_annotations_are_not_3d(self):
        import hashlib
        anchor, warn=load_frame_anchors(FRAME,
            source_sha256=hashlib.sha256(MANNEQUIN.read_bytes()).hexdigest(),
            source_width=1218,source_height=1292)
        self.assertEqual(set(anchor),{'head_top','right_toe','left_toe'})
        self.assertTrue(any('UNVERIFIED' in w for w in warn))

    def test_wrong_mannequin_hash_fails(self):
        with self.assertRaises(FramingError) as ctx:
            load_frame_anchors(FRAME,source_sha256='0'*64,source_width=1218,source_height=1292)
        self.assertEqual(ctx.exception.code,'FRAME_SOURCE_HASH_MISMATCH')

    def make_package(self,anchor=True):
        out=self.d/'geometry'
        manifest,guide=build_pose_package(pose_image=MANNEQUIN,pose_json=POSE,
                                          output_dir=out,width=768,height=1344)
        result=reframe_external_guide(output_dir=out,mannequin=MANNEQUIN,master=self.master,
                    anchors_json=FRAME if anchor else None)
        return result

    def test_projected_guide_is_full_frame(self):
        r=self.make_package()
        with Image.open(r['pose_guide_path']) as image:
            self.assertEqual(image.size,(768,1344))
            self.assertEqual(image.getpixel((0,0)),(0,0,0))
        self.assertGreater(r['minimum_boundary_distance_px'],45)
        self.assertTrue(r['toe_targets_available_for_review'])
        self.assertFalse(r['foot_toes_present_in_guide'])
        self.assertEqual(r['foot_visibility_in_generated_image'],'NOT_EVALUATED')
        self.assertEqual(r['pose_control_mode'],'QWEN_IMAGE2_REFERENCE_ONLY')

    def test_original_body18_joints_are_unmodified(self):
        r=self.make_package()
        src=json.loads(POSE.read_text(encoding='utf-8'))['keypoints']
        written=json.loads((self.d/'geometry'/'external_pose.json').read_text(encoding='utf-8'))['keypoints']
        self.assertEqual(src['left_ankle']['x'],written['left_ankle']['x'])
        self.assertEqual(src['right_knee']['y'],written['right_knee']['y'])
        self.assertFalse(r['body18_joint_positions_modified'])
        rproj=r['projected_keypoints_2d']
        self.assertGreater(rproj['left_knee']['x'],rproj['right_knee']['x'])
        self.assertLess(rproj['right_ankle']['x'],rproj['right_knee']['x'])

    def test_missing_toe_landmarks_is_explicit(self):
        r=self.make_package(anchor=False)
        self.assertFalse(r['toe_targets_available_for_review'])
        self.assertTrue(any('FOOT_LANDMARKS_UNKNOWN' in w for w in r['warnings']))

    def test_source_appearance_graph_remains_unchanged(self):
        req=request_from_text(TEXT)
        g=build_direct_graph('master.png','V81_POSE_ONLY_abcdef1234567890.png',
                             'details.png',TEXT,req)
        self.assertEqual(g['4']['inputs']['image'],'master.png')
        self.assertEqual(g['17']['inputs']['image'],'details.png')
        self.assertEqual(g['7']['inputs']['image1'],['6',0])
        self.assertEqual(g['7']['inputs']['image3'],['17',0])
        self.assertEqual(g['14']['inputs']['seed'],975311)
        self.assertIn('both widely separated knees',g['7']['inputs']['prompt'])
        self.assertIn('original camisole AND the shorts',g['7']['inputs']['prompt'])

    def test_pipeline_compiles_with_full_frame_landmarks(self):
        rc=main(['--master',str(self.master),'--pose-image',str(MANNEQUIN),
                 '--pose-json',str(POSE),'--frame-anchors',str(FRAME),'--text',TEXT])
        self.assertEqual(rc,0)
        newest=max((ROOT/'outputs'/'experiments'/'v8_1_structure').glob('*/diagnostic.json'),
                   key=lambda p:p.stat().st_mtime)
        rep=json.loads(newest.read_text(encoding='utf-8'))
        self.assertEqual(rep['framing_qa']['canvas_alignment'],'PASS_REFERENCE_GUIDE_ONLY')
        self.assertEqual(rep['geometry']['pose_only_openpose']['width'],768)
        self.assertEqual(rep['geometry']['pose_only_openpose']['height'],1344)
        self.assertEqual(rep['geometry']['frame_alignment']['toe_targets_available_for_review'],True)
        self.assertEqual(rep['quality']['identity'],'NOT_PERFORMED')
        self.assertEqual(rep['quality']['rendering'],'NOT_PERFORMED')
        self.assertEqual(rep['appearance']['appearance_provenance'],'MASTER_ONLY')

    def test_explicit_incompatible_canvas_fails(self):
        rc=main(['--master',str(self.master),'--pose-image',str(MANNEQUIN),
                 '--pose-json',str(POSE),'--pose-height','960','--text',TEXT])
        self.assertEqual(rc,2)

if __name__=='__main__':unittest.main()
