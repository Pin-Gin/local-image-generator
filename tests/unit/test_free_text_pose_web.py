from __future__ import annotations
import base64
from io import BytesIO
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SCRIPT=ROOT/'experiments/active'
sys.path.insert(0,str(SCRIPT))
spec=importlib.util.spec_from_file_location('free_text_pose_web',SCRIPT/'free_text_pose_web.py')
web=importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)

class TestWebPoc(unittest.TestCase):
    def png_data(self):
        b=BytesIO()
        Image.new('RGB',(64,128),(255,255,255)).save(b,format='PNG')
        return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode('ascii')

    def test_one_image_and_japanese_text_creates_session(self):
        with tempfile.TemporaryDirectory() as t, patch.object(web,'SESSIONS',Path(t)):
            r=web.make_session('成人女性が正面を向き、両手を左右に広げて立つ',self.png_data())
            self.assertEqual(r['status'],'POSE_GUIDE_CREATED')
            self.assertEqual(r['identity_qa'],'NOT_PERFORMED')
            self.assertTrue((Path(t)/r['session_id']/'pose.png').is_file())

    def test_m_seated_prompt_creates_guide_and_records_expression(self):
        with tempfile.TemporaryDirectory() as t, patch.object(web,'SESSIONS',Path(t)):
            sentence = '成人女性が真正面を向き、座っている状態で足をM字に開いて微笑んでいる'
            result = web.make_session(sentence, self.png_data())
            self.assertEqual(result['status'], 'POSE_GUIDE_CREATED')
            self.assertEqual(result['request']['pose']['id'], 'seated_m')
            self.assertEqual(result['request']['deltas']['expression'], 'soft_smile')
            self.assertTrue((Path(t)/result['session_id']/'pose.png').exists())

    def test_unsupported_generation_is_rejected(self):
        with tempfile.TemporaryDirectory() as t, patch.object(web,'SESSIONS',Path(t)):
            with self.assertRaises(web.poc.PocError) as c:
                web.make_session('成人女性が立つ。赤いスカート',self.png_data(),generate=True)
            self.assertEqual(c.exception.code,'UNRESOLVED_SEMANTICS')

if __name__=='__main__':unittest.main()
