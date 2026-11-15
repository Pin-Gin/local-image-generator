from __future__ import annotations
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments'/'active'))
from v8_pose_structure import build_pose_package,build_coarse_silhouette,build_ground_contact,PoseStructureError

IMAGE=ROOT/'examples'/'mannequin_m_seated.png'
POSE=ROOT/'examples'/'mannequin_m_seated.pose.json'

class TestV81PoseStructure(unittest.TestCase):
    def test_fixture_present(self):
        self.assertTrue(IMAGE.is_file());self.assertTrue(POSE.is_file())
    def test_package_builds_without_gpu(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)
            m,guide=build_pose_package(pose_image=IMAGE,pose_json=POSE,output_dir=out,
                                        width=896,height=960)
            self.assertTrue(guide.is_file());self.assertTrue((out/'pose_only_silhouette.png').exists())
            self.assertEqual(m['mannequin_rgb_forwarding'],False)
            self.assertEqual(m['silhouette_used_for_generation'],False)
            self.assertEqual(m['depth_status'],'UNKNOWN_FROM_SINGLE_2D_IMAGE')
            self.assertTrue(m['source_image_hash_verified'])
            with Image.open(guide) as im:self.assertEqual(im.size,(896,960))
            with Image.open(out/'pose_only_silhouette.png') as im:
                self.assertEqual(im.mode,'L')
                self.assertTrue(im.getbbox())
            self.assertEqual(m['pose_only_silhouette']['accuracy'],'COARSE_ENVELOPE_NOT_SEGMENTATION_OR_DEPTH')
            self.assertEqual(m['pose_only_openpose']['sha256'],hashlib.sha256(guide.read_bytes()).hexdigest())
    def test_contact_unknown_not_invented(self):
        with tempfile.TemporaryDirectory() as td:
            x=build_ground_contact({},Path(td)/'ground.json')
            self.assertTrue(all(item['state']=='UNKNOWN' for item in x['contact'].values()))
            self.assertEqual(x['automated_contact_verification'],'NOT_PERFORMED')
    def test_user_declared_contact_unverified(self):
        with tempfile.TemporaryDirectory() as td:
            x=build_ground_contact({'ground_contact':{'left_hand':'CONTACT'}},Path(td)/'ground.json')
            self.assertEqual(x['contact']['left_hand']['evidence'],'USER_DECLARED_UNVERIFIED')
    def test_declared_contacts_preserved_in_package(self):
        with tempfile.TemporaryDirectory() as td:
            modified=Path(td)/'with_contact.json'
            data=json.loads(POSE.read_text(encoding='utf-8'))
            data['ground_contact']={'left_hand':'CONTACT','pelvis':'CONTACT'}
            modified.write_text(json.dumps(data),encoding='utf-8')
            manifest,_=build_pose_package(pose_image=IMAGE,pose_json=modified,output_dir=Path(td)/'prepared')
            contact=manifest['ground_contact']['contact']
            self.assertEqual(contact['left_hand']['state'],'CONTACT')
            self.assertEqual(contact['left_hand']['evidence'],'USER_DECLARED_UNVERIFIED')
            self.assertEqual(contact['left_foot']['state'],'UNKNOWN')

    def test_invalid_ground_contact_fails(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PoseStructureError):
                build_ground_contact({'ground_contact':{'pelvis':'SURE'}},Path(td)/'x.json')
    def test_json_hash_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            bad=Path(td)/'bad.json'
            d=json.loads(POSE.read_text(encoding='utf-8'))
            d['source_image_sha256']='0'*64
            bad.write_text(json.dumps(d),encoding='utf-8')
            with self.assertRaises(PoseStructureError) as ctx:
                build_pose_package(pose_image=IMAGE,pose_json=bad,output_dir=Path(td)/'out')
            self.assertEqual(ctx.exception.code,'POSE_SOURCE_HASH_MISMATCH')
    def test_missing_core_joint_fails(self):
        with tempfile.TemporaryDirectory() as td:
            bad=Path(td)/'bad.json'
            d=json.loads(POSE.read_text(encoding='utf-8'))
            d['keypoints']['left_knee']=None
            bad.write_text(json.dumps(d),encoding='utf-8')
            with self.assertRaises(PoseStructureError) as ctx:
                build_pose_package(pose_image=IMAGE,pose_json=bad,output_dir=Path(td)/'out')
            self.assertEqual(ctx.exception.code,'POSE_CORE_JOINTS_MISSING')
    def test_not_mannequin_pixels_in_pose_guide(self):
        with tempfile.TemporaryDirectory() as td:
            m,guide=build_pose_package(pose_image=IMAGE,pose_json=POSE,output_dir=Path(td))
            with Image.open(guide) as im:
                # Synthetic guide starts from black; gray mannequin RGB must not be used as image2.
                self.assertEqual(im.convert('RGB').getpixel((0,0)),(0,0,0))
            self.assertNotEqual(guide.read_bytes(), IMAGE.read_bytes())

if __name__=='__main__':unittest.main()
