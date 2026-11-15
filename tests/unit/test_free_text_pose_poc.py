from __future__ import annotations
import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[2] / 'experiments/active/free_text_pose_poc.py'
spec = importlib.util.spec_from_file_location('free_text_pose_poc', MODULE)
poc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(poc)

class TestTextPosePoc(unittest.TestCase):
    def test_new_pose_changes_and_keeps_master_authority(self):
        got = poc.classify_request('成人女性が正面を向き、両手を左右に広げて立つ')
        self.assertEqual(got['pose']['id'],'arms_out')
        self.assertTrue(got['identity']['master_authority'])
        self.assertEqual(got['identity']['body_heads_target'],7.3)
        self.assertEqual(got['safety']['status'],'NOT_EVALUATED')
        self.assertEqual(got['interpretation']['coverage'],'COMPLETE_FOR_POC')

    def test_frontal_seated_m_pose_and_smile(self):
        sentence = '成人女性が真正面を向き、座っている状態で足をM字に開いて微笑んでいる'
        got = poc.classify_request(sentence)
        self.assertEqual(got['pose']['id'], 'seated_m')
        self.assertEqual(got['pose']['view'], 'front')
        self.assertEqual(got['pose']['geometry']['support_surface'], 'UNSPECIFIED')
        self.assertEqual(got['deltas']['expression'], 'soft_smile')
        self.assertEqual(got['interpretation']['coverage'], 'COMPLETE_FOR_POC')
        self.assertIsNone(got['deltas']['clothing'])
        self.assertIsNone(got['deltas']['scene'])
        self.assertEqual(got['safety']['status'], 'NOT_EVALUATED')
        prompt = poc.content_prompt(got)
        self.assertIn('knees flexed', prompt)
        self.assertIn('gentle natural smile', prompt)

    def test_frontal_seated_m_guide_is_generated(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)/'m_sit.png'
            poc.render_pose('seated_m', dest)
            from PIL import Image
            with Image.open(dest) as img:
                self.assertEqual(img.size, (768, 1344))
                self.assertIsNotNone(img.getbbox())

    def test_seated_m_with_unrecognized_wardrobe_stays_partial(self):
        sentence = '成人女性が真正面を向き、座っている状態で足をM字に開いて微笑んでいる。赤いジャケット'
        got = poc.classify_request(sentence)
        self.assertEqual(got['pose']['id'], 'seated_m')
        self.assertEqual(got['interpretation']['coverage'], 'PARTIAL')

    def test_natural_shower_scene_is_parsed_not_misclassified(self):
        got = poc.classify_request('成人女性が立つ。シャワー室の場面')
        self.assertEqual(got['deltas']['scene'],'bathroom_shower')
        self.assertEqual(got['safety']['status'],'NOT_EVALUATED')
        self.assertEqual(got['interpretation']['coverage'],'PARTIAL')

    def test_unsupported_pose_is_error_not_silent_replacement(self):
        with self.assertRaises(poc.PocError) as c:
            poc.classify_request('成人女性が四つん這いになる')
        self.assertEqual(c.exception.code,'POSE_UNSUPPORTED')

    def test_unsupported_camera_is_error(self):
        with self.assertRaises(poc.PocError) as c:
            poc.classify_request('背面から立ち姿')
        self.assertEqual(c.exception.code,'CAMERA_UNSUPPORTED')

    def test_guide_is_generated(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)/'test.png'
            poc.render_pose('arms_out',dest)
            from PIL import Image
            with Image.open(dest) as img:
                self.assertEqual(img.size,(768,1344))
                self.assertIsNotNone(img.getbbox())
                self.assertEqual(img.getpixel((0,0)),(0,0,0))

if __name__ == '__main__':
    unittest.main()
