import json
import math
from pathlib import Path
import tempfile
import unittest
import numpy as np
from PIL import Image
from humanoidkit.world import World,angle_error
from humanoidkit.planning import GridPlanner,NoPath
from humanoidkit.vision import Camera,detect
from humanoidkit.engine import Engine,TaskFailure
from humanoidkit.learning import demonstrations


class GeometryTests(unittest.TestCase):
    def test_astar_routes_around_inflated_obstacle(self):
        planner=GridPlanner([(-.2,-.3,.2,.3)])
        path=planner.plan((-1.,0.),(1.,0.))
        self.assertGreater(len(path),20)
        self.assertTrue(all(planner.segment_free(a,b) for a,b in zip(path,path[1:])))
        self.assertTrue(any(abs(p[1])>.5 for p in path))

    def test_blocked_route_is_not_reported_as_valid(self):
        with self.assertRaises(NoPath):
            GridPlanner([(-.1,-1.7,.1,1.7)]).plan((-1.,0.),(1.,0.))

    def test_inverse_and_forward_kinematics_agree(self):
        w=World()
        for target in ([w.base[0]+.5,w.base[1]-.1,.9],[w.base[0]-.4,w.base[1],1.1]):
            joints=w.ik(target)
            np.testing.assert_allclose(w.links(joints)[-1],target,atol=1e-8)
        with self.assertRaises(ValueError):
            w.ik(w.shoulder+[3.,0.,0.])

    def test_gripper_orientation_has_pi_symmetry(self):
        self.assertAlmostEqual(angle_error(.2+math.pi,.2),0.)


class PerceptionTests(unittest.TestCase):
    def test_pixel_detector_estimates_pose_from_images(self):
        camera=Camera()
        w=World(4101,"rotated")
        rgb,depth=camera.render(w)
        detections=detect(rgb,depth,camera)
        self.assertEqual(len(detections),len(w.parts))
        for part in w.parts:
            d=min([d for d in detections if d.kind==part.kind],key=lambda d:np.linalg.norm(d.position-part.position))
            self.assertLess(np.linalg.norm(d.position-part.position),.015)
            self.assertLess(abs(angle_error(part.yaw,d.yaw)),.14)

    def test_erasing_pixels_removes_objects_even_if_world_contains_them(self):
        camera=Camera()
        w=World()
        rgb,depth=camera.render(w)
        rgb[:]=(28,36,48)
        self.assertEqual(detect(rgb,depth,camera),[])
        self.assertEqual(len(w.parts),5)

    def test_miscalibrated_image_is_rejected(self):
        with self.assertRaises(ValueError):
            detect(np.zeros((4,4,3)),np.zeros((4,4)),Camera())

    def test_low_light_does_not_destroy_class_identification(self):
        c=Camera()
        w=World(4101,"lighting")
        rgb,depth=c.render(w)
        self.assertEqual(len(detect(rgb,depth,c)),5)


class WorkflowTests(unittest.TestCase):
    def test_complete_order_with_pixel_verification(self):
        e=Engine(4101)
        result=e.execute()
        self.assertTrue(result["success"],result)
        self.assertEqual(result["correct_slots"],4)
        self.assertEqual(result["grasp_attempts"],4)
        self.assertEqual(result["classical_fallbacks"],0)

    def test_missing_and_occluded_parts_fail_closed(self):
        for scenario in ("missing","occluded"):
            e=Engine(4101,scenario)
            result=e.execute()
            self.assertFalse(result["success"])
            self.assertEqual(result["grasp_attempts"],0)

    def test_blocked_path_never_announces_a_complete_kit(self):
        result=Engine(4101,"blocked").execute()
        self.assertFalse(result["success"])
        self.assertIn("path",result["reason"].lower())

    def test_grasp_failure_retries_and_recovers(self):
        result=Engine(4101,"grasp_failure").execute()
        self.assertTrue(result["success"],result)
        self.assertEqual(result["retries"],1)
        self.assertEqual(result["grasp_attempts"],5)

    def test_camera_detects_drop_after_release(self):
        result=Engine(4101,"drop").execute()
        self.assertFalse(result["success"])
        self.assertIn("camera verification",result["reason"].lower())

    def test_wrong_slot_orientation_is_not_accepted(self):
        e=Engine()
        p=e.world.parts[0]
        p.location="slot0"
        p.position=e.world.slots[0].copy()
        p.yaw=math.pi/2
        self.assertFalse(e.world.verify()[0])
        self.assertFalse(e.verify_slot_from_camera(0,"bolt"))

    def test_stop_prevents_further_motion(self):
        e=Engine()
        e.step()
        original=e.world.base.copy()
        e.stop_requested=True
        e.step()
        self.assertFalse(e.step())
        np.testing.assert_array_equal(original,e.world.base)
        self.assertEqual(e.state,"STOPPED")

    def test_trial_log_can_be_reloaded(self):
        e=Engine(4101,"missing")
        e.execute()
        Path("runs/test-temp").mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir="runs/test-temp") as folder:
            path=e.save(folder)
            log=json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(log["summary"]["status"],"FAILED")
            self.assertGreater(len(log["events"]),0)


class LearningTests(unittest.TestCase):
    def test_demonstrations_have_separate_episode_ids_and_finite_targets(self):
        x,y,ids=demonstrations(range(1000,1003))
        self.assertEqual(x.shape[1],7)
        self.assertEqual(y.shape[1:],(6,4))
        self.assertTrue(np.isfinite(x).all() and np.isfinite(y).all())
        self.assertEqual(set(ids),{1000,1001,1002})
        self.assertLessEqual(float(np.abs(y).max()),1.00001)

    @unittest.skipUnless(Path("artifacts/policy.pt").exists(),"Run bounded training first")
    def test_learned_controller_completes_held_out_layout_without_fallback(self):
        result=Engine(4201,"normal","learned").execute()
        self.assertTrue(result["success"],result)
        self.assertEqual(result["classical_fallbacks"],0)

    @unittest.skipUnless(Path("artifacts/policy.pt").exists(),"Run bounded training first")
    def test_unresponsive_learned_policy_fails_without_silent_fallback(self):
        e=Engine(method="learned")
        e.policy.action=lambda *args:np.zeros(4)
        target=e.world.hand+[.1,0,0]
        with self.assertRaises(TaskFailure):
            list(e.servo(target,0.))
        self.assertEqual(e.fallbacks,0)

    @unittest.skipUnless(Path("artifacts/policy.pt").exists(),"Run bounded training first")
    def test_hybrid_records_and_executes_classical_recovery(self):
        e=Engine(method="hybrid")
        e.policy.action=lambda *args:np.zeros(4)
        target=e.world.hand+[.1,0,0]
        events=list(e.servo(target,0.))
        self.assertEqual(e.fallbacks,1)
        self.assertTrue(any(x["state"]=="RECOVER" for x in events))
        self.assertLess(np.linalg.norm(e.world.hand-target),.012)

    @unittest.skipUnless(Path("artifacts/training_report.json").exists(),"Run bounded training first")
    def test_saved_dataset_splits_have_no_shared_episodes(self):
        splits=[np.load(f"artifacts/demonstrations_{name}.npz")["episode_ids"]
                for name in ("train","validation","test")]
        for i in range(3):
            for j in range(i):
                self.assertEqual(len(np.intersect1d(splits[i],splits[j])),0)


if __name__=="__main__":
    unittest.main()
