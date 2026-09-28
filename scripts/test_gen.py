import json
import os
import tempfile
import unittest

from mvvm_gen import graphs, pk_v11, review, timing

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

    def test_ref2v_wires_references_and_names_pictures(self):
        g = graphs.h3_ref2v(["a.png", "b.png"], "p", 1, "x")
        self.assertEqual(g["cond"]["inputs"]["ref_images.ref_image_1"], ["ref1", 0])
        self.assertIn("ref2va", g["unet"]["inputs"]["unet_name"])
        prompt = graphs.h3_ref2v_prompt([("Rafa.", [1, 2])], "s", "look", "shot", "sound")
        self.assertIn("<Subject 1> is the person in <Picture 1> and <Picture 2>", prompt)
        self.assertIn("retention_analysis:", prompt)
        self.assertNotIn("subject_definitions", graphs.h3_ref2v_prompt([], "s", "l", "sh", "so"))

    def test_pk_v11_modes_only_touch_his_bundle_and_switch(self):
        for workflow, images, switch in (("pk_v11_t2v", [], False), ("pk_v11_fl2v", ["a.png", "b.png"], False),
                                         ("pk_v11_ref2v", ["a.png", "b.png", "c.png"], True),
                                         ("pk_v11_fl2v_refs", ["f.png", None, "r1.png", "r2.png"], False)):
            g = pk_v11.build(workflow, "p", 7, "x", seconds=4.0, images=images)
            self.assertEqual(g[pk_v11.REF_SWITCH]["inputs"]["value"], switch)
            self.assertEqual(len(g[pk_v11.BUNDLE]["inputs"]), len([i for i in images if i]))
            self.assertEqual(g[pk_v11.TARGET]["inputs"]["width"], 1344)
            self.assertEqual(g["5310:5603"]["inputs"]["sparsity_ratio"], 0.7)  # his SLA setting, untouched
            self.assertEqual(g["5479:5471"]["inputs"]["steps"], 13)
            for node in g.values():
                for value in node["inputs"].values():
                    if isinstance(value, list) and len(value) == 2 and isinstance(value[1], int):
                        self.assertIn(value[0], g)
        with self.assertRaises(ValueError):
            pk_v11.build("pk_v11_fl2v", "p", 1, "x", images=["a", "b", "c"])

    def test_pilot_plan_references_are_consistent(self):
        with open(PLAN, encoding="utf-8") as fh:
            plan = json.load(fh)
        for lora in plan.get("clip_loras", []):
            self.assertIsInstance(lora, list)
            self.assertEqual(len(lora), 2)
        ids = [shot["id"] for shot in plan["shots"]]
        self.assertEqual(len(ids), len(set(ids)))
        for shot in plan["shots"]:
            self.assertIn(shot["location"], plan["locations"])
            for cid in shot["characters"]:
                self.assertIn(cid, plan["characters"])


class ReviewTests(unittest.TestCase):
    @staticmethod
    def d(a, b, choice):
        return {"a": a, "b": b, "choice": choice}

    def test_each_setup_compares_its_own_two_seeds(self):
        takes = [0, 1, 2, 3, 4, 5]
        self.assertEqual(review.bracket(takes, [], 2)["pair"], [0, 1])
        state = review.bracket(takes, [self.d(0, 1, "b")], 2)
        self.assertEqual((state["pair"], state["setup"]), ([2, 3], 1))  # the chosen take does not carry over
        state = review.bracket(takes, [self.d(0, 1, "b"), self.d(2, 3, "a")], 2)
        self.assertEqual(state["pair"], [4, 5])

    def test_cut_uses_the_first_setup_with_a_winner(self):
        log = [self.d(0, 1, "neither"), self.d(2, 3, "b"), self.d(4, 5, "a")]
        state = review.bracket([0, 1, 2, 3, 4, 5], log, 2)
        self.assertEqual((state["done"], state["winner"], state["rejected"]), (True, 3, [0, 1, 2, 5]))
        self.assertEqual([s["winner"] for s in state["setups"]], [None, 3, 4])

    def test_setup_with_one_rendered_take_is_kept_or_rejected_alone(self):
        state = review.bracket([0, 1, 2], [self.d(0, 1, "a")], 2)
        self.assertEqual(state["pair"], [2, None])
        with self.assertRaises(ValueError):
            review.bracket([0, 1, 2], [self.d(0, 1, "a"), self.d(2, None, "b")], 2)
        dropped = review.bracket([0, 1, 2], [self.d(0, 1, "neither"), self.d(2, None, "neither")], 2)
        self.assertEqual((dropped["done"], dropped["winner"]), (True, None))

    def test_redoing_one_setup_keeps_the_others(self):
        log = [self.d(0, 1, "a"), self.d(2, 3, "neither"), self.d(4, 5, "b")]
        state = review.bracket([0, 1, 2, 3, 4, 5], [log[0], log[2]], 2)
        self.assertEqual((state["pair"], state["setup"], state["done"]), ([2, 3], 1, False))
        self.assertEqual([s["winner"] for s in state["setups"]], [0, None, 5])
        redone = review.bracket([0, 1, 2, 3, 4, 5], [log[0], log[2], self.d(2, 3, "b")], 2)
        self.assertEqual((redone["done"], redone["winner"]), (True, 0))
        with tempfile.TemporaryDirectory() as root:
            store = review.Store(root)
            store.set_decisions("s01", log)
            store.redo("s01", 2, 1)
            self.assertEqual(store.decisions("s01"), [log[0], log[2]])

    def test_decision_for_a_stale_pair_is_rejected(self):
        with self.assertRaises(ValueError):
            review.bracket([0, 1, 2, 3], [self.d(1, 2, "a")], 2)
        with self.assertRaises(ValueError):
            review.bracket([0, 1], [self.d(0, 1, "a"), self.d(0, 1, "a")], 2)

    def test_store_reports_winner_only_when_decided(self):
        with tempfile.TemporaryDirectory() as root:
            store = review.Store(root)
            takes = [0, 1, 2, 3]
            self.assertEqual(store.winner("s01", takes, 2), (None, "not reviewed"))
            store.decide("s01", takes, 2, 0, 1, "neither", "  face drifts  ")
            self.assertEqual(store.winner("s01", takes, 2), (None, "review unfinished"))
            store.decide("s01", takes, 2, 2, 3, "b")
            reloaded = review.Store(root)
            self.assertEqual(reloaded.winner("s01", takes, 2), (3, "reviewed"))
            self.assertEqual(reloaded.decisions("s01")[0]["comment"], "face drifts")
            self.assertEqual(reloaded.winner("s01", takes + [4, 5], 2)[1], "review unfinished")
            with self.assertRaises(ValueError):
                store.decide("s01", takes, 2, 2, 3, "a")


if __name__ == "__main__":
    unittest.main()


