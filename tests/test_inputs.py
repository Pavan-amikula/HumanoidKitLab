import json
import tempfile
from pathlib import Path
import unittest
import numpy as np
from PIL import Image
from app import export_bop
from humanoidkit.rgbd import PinholeCamera,replay
from humanoidkit.world import World
from humanoidkit.vision import Camera
from humanoidkit.server import Session


class ExternalInputTests(unittest.TestCase):
    def temporary(self):
        Path("runs/test-temp").mkdir(parents=True,exist_ok=True)
        return tempfile.TemporaryDirectory(dir="runs/test-temp")

    def test_rgbd_file_replay_recovers_synthetic_parts(self):
        rgb,depth=Camera().render(World(4101))
        with self.temporary() as directory:
            root=Path(directory)
            Image.fromarray(rgb).save(root/"frame.png")
            np.save(root/"depth.npy",depth)
            (root/"camera.json").write_text(json.dumps({"projection":"orthographic","depth_scale_to_metres":1}),encoding="utf-8")
            detections=replay(root/"frame.png",root/"depth.npy",root/"camera.json")
            self.assertEqual(len(detections),5)
            self.assertEqual(sum(d["kind"]=="bolt" for d in detections),2)

    def test_pinhole_unprojection_uses_extrinsic_transform(self):
        transform=np.eye(4)
        transform[:3,3]=[1,2,3]
        camera=PinholeCamera({"width":640,"height":480,"fx":500,"fy":500,"cx":320,"cy":240,
                              "camera_to_world":transform.tolist()})
        np.testing.assert_allclose(camera.unproject(320,240,2),[1,2,5])
        np.testing.assert_allclose(camera.unproject(570,240,2),[2,2,5])

    def test_invalid_rotation_is_rejected(self):
        with self.assertRaises(ValueError):
            PinholeCamera({"width":640,"height":480,"fx":500,"fy":500,"cx":320,"cy":240,
                           "camera_to_world":np.diag([-1,1,1,1]).tolist()})

    def test_bop_export_preserves_pose_units_and_object_identity(self):
        with self.temporary() as directory:
            root=Path(directory)
            gt={"0":[{"obj_id":7,"cam_R_m2c":np.eye(3).ravel().tolist(),"cam_t_m2c":[100,200,800]}]}
            info={"0":[{"bbox_visib":[10,20,30,40],"visib_fract":.75}]}
            camera={"0":{"cam_K":[500,0,320,0,500,240,0,0,1],"depth_scale":.1}}
            for name,data in [("scene_gt",gt),("scene_gt_info",info),("scene_camera",camera)]:
                (root/f"{name}.json").write_text(json.dumps(data),encoding="utf-8")
            export_bop(root,root/"export.json")
            record=json.loads((root/"export.json").read_text(encoding="utf-8"))["records"][0]
            self.assertEqual(record["object_id"],7)
            self.assertEqual(record["translation_model_to_camera_mm"],[100,200,800])
            self.assertEqual(record["bbox_xywh"],[10,20,30,40])


class DashboardSessionTests(unittest.TestCase):
    def test_pause_step_run_stop_and_new_trial(self):
        s=Session()
        s.control({"action":"reset","method":"classical","scenario":"normal","seed":4101})
        s.control({"action":"run"})
        self.assertTrue(s.playing)
        s.control({"action":"pause"})
        self.assertFalse(s.playing)
        s.control({"action":"step"})
        self.assertGreater(len(s.engine.events),0)
        s.control({"action":"stop"})
        self.assertTrue(s.engine.finished)
        self.assertEqual(s.engine.state,"STOPPED")
        with self.assertRaises(ValueError):
            s.control({"action":"run"})
        s.control({"action":"reset","method":"classical","scenario":"missing","seed":4101})
        self.assertEqual(s.engine.state,"READY")
        self.assertFalse(s.engine.finished)


if __name__=="__main__":
    unittest.main()
