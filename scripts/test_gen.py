import json
import os
import unittest

from mvvm_gen import graphs, timing

PLAN = os.path.join(os.path.dirname(__file__), "mvvm_gen", "plans", "i-ran-pilot.json")


class TimingTests(unittest.TestCase):
    def test_shot_frames_stay_on_the_bar_grid(self):
        frames = timing.shot_frames([2] * 16, 137)
        self.assertEqual(sum(frames), round(32 * timing.bar_seconds(137) * timing.FPS))
        self.assertTrue(all(abs(f - 2 * timing.bar_seconds(137) * 24) <= 1 for f in frames))

    def test_h3_length_snaps_to_model_grid(self):
        for seconds in (1.0, 3.5, 5.17, 7.3):
            n = graphs.h3_length(seconds)
            self.assertEqual((n - 5) % 17, 0)
            self.assertGreaterEqual(n, max(124, seconds * 24))

    def test_downbeat_phase_finds_a_synthetic_pulse(self):
        rate, bpm = 200, 120
        env = [0] * (rate * 20)
        for k in range(40):
            env[int((0.13 + k * 0.5) * rate)] = 1000
        self.assertAlmostEqual(timing.downbeat_phase(env, rate, bpm), 0.13, delta=0.011)


class GraphTests(unittest.TestCase):
    def test_qwen_edit_wires_every_reference(self):
        g = graphs.qwen21_image("x", ["a.png", "b.png"], 1344, 768, 1, "p")
        enc = g["encode"]["inputs"]
        self.assertEqual(enc["images.image_1"], ["ref1", 0])
        self.assertEqual(enc["images.image_2"], ["ref2", 0])
        self.assertIn("qwen_image_2.1", g["unet"]["inputs"]["unet_name"])

    def test_every_link_points_at_an_existing_node(self):
        for g in (graphs.qwen21_image("x", ["a"], 1000, 700, 1, "p"), graphs.h3_i2v("f.png", "x", 1, "p")):
            for node in g.values():
                for value in node["inputs"].values():
                    if isinstance(value, list) and len(value) == 2 and isinstance(value[1], int):
                        self.assertIn(value[0], g)

    def test_pilot_plan_references_are_consistent(self):
        with open(PLAN, encoding="utf-8") as fh:
            plan = json.load(fh)
        for shot in plan["shots"]:
            self.assertIn(shot["location"], plan["locations"])
            for cid in shot["characters"]:
                self.assertIn(cid, plan["characters"])


if __name__ == "__main__":
    unittest.main()
