import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("lint_prompt.py")
spec = importlib.util.spec_from_file_location("dynamic_lint", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

BODY = "[Slow orbit] Medium shot. The dancer sways, then lifts her hands, jungle canopy, teal haze."


def cuts(boundaries, bodies=None):
    def timestamp(value):
        return f"{int(value // 60):02d}:{value % 60:06.3f}"
    return "\n".join(f"[{timestamp(a)} - {timestamp(b)}] {(bodies or [BODY] * len(boundaries))[i]}"
                     for i, (a, b) in enumerate(boundaries))


class CompilerLintTests(unittest.TestCase):
    def codes(self, text, **kwargs):
        return {f["code"] for f in module.lint(text, **kwargs)["findings"]}

    def test_irregular_cuts_and_schedule_match(self):
        prompt = cuts([(0, 3.5), (3.5, 5), (5, 9.5), (9.5, 15)])
        schedule = {str(n): BODY for n in (0, 84, 120, 228)}
        result = module.lint(prompt, schedule=schedule)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["cut_count"], 3)
        self.assertEqual(result["findings"], [])

    def test_frame_math_at_custom_fps_and_half_frame(self):
        self.assertEqual(module.frame_at(4.2, 24), 101)
        self.assertEqual(module.frame_at(2.5, 25), 63)
        self.assertEqual(module.frame_at(3.5, 30), 105)
        self.assertEqual(module.frame_at(2.5, 16), 40)

    def test_exact_frame_input_survives_millisecond_display(self):
        frames = (0, 45, 90, 210, 360)
        prompt = cuts([(a / 24, b / 24) for a, b in zip(frames, frames[1:])])
        self.assertEqual(module.lint(prompt)["start_frames"], list(frames[:-1]))

    def test_gap_overlap_and_clip_end_fail(self):
        for boundaries in ([(0, 5), (6, 15)], [(0, 6), (5, 15)], [(1, 15)]):
            self.assertIn("interval-continuity", self.codes(cuts(boundaries)))
        self.assertIn("duration-end", self.codes(cuts([(0, 14)])))
        self.assertIn("interval-range", self.codes(cuts([(0, 16)])))

    def test_cannot_hide_cut_inside_one_rendered_frame(self):
        self.assertIn("frame-collision", self.codes(cuts([(0, .01), (.01, 15)])))

    def test_invalid_and_nonfinite_inputs(self):
        for value in (0, -1, "NaN", "Infinity"):
            with self.assertRaises(ValueError):
                module.lint(cuts([(0, 15)]), fps=value)

    def test_schedule_wrong_frame_or_changed_text_fails(self):
        prompt = cuts([(0, 5), (5, 15)])
        self.assertIn("schedule-frames", self.codes(prompt, schedule={"0": BODY, "119": BODY}))
        self.assertIn("schedule-body", self.codes(prompt, schedule={"0": BODY, "120": "different"}))
        self.assertIn("schedule-format", self.codes(prompt, schedule={"-1": BODY}))

    def test_typo_repetition_and_profile_findings(self):
        body = "[Static wide shot] The woman wearing a silver top walks walks; the woman stops. The camera pans left as the clifff collapes, capturing the mood."
        codes = self.codes(cuts([(0, 15)], [body]), context={"subject_anchors": ["the woman"]})
        self.assertTrue({"spelling", "repeated-word", "repeated-subject", "appearance-prose",
                         "negative-prose", "camera-conflict", "wrap-up"} <= codes)

    def test_prior_action_and_framing_conflicts(self):
        body = "[Static close-up] After opening the door, the dancer shows her whole body, teal haze."
        codes = self.codes(cuts([(0, 5), (5, 15)], [BODY, body]))
        self.assertTrue({"prior-cut-replay", "framing-conflict"} <= codes)

    def test_completed_sit_is_flagged_but_seated_state_is_valid(self):
        first = "[Static wide shot] The woman sits down, teal haze."
        second = "[Slow orbit] Medium shot. The woman smiles as she sits down, teal haze."
        prompt = cuts([(0, 5), (5, 15)], [first, second])
        self.assertIn("action-replay", self.codes(prompt))
        seated = "[Slow orbit] Medium shot. The woman is seated, her hands resting on her knees, teal haze."
        self.assertNotIn("action-replay", self.codes(cuts([(0, 5), (5, 15)], [first, seated])))
        self.assertNotIn("action-replay", self.codes(cuts([(0, 5), (5, 15)], [first, second.replace("woman", "man")])))

    def test_native_fields_and_canonical_shot_timestamps(self):
        text = ("subject_definitions: <Subject 1> is the dancer in <Picture 1>.\n"
                "summary: [reference generation] A two-shot dance.\n"
                "retention_analysis: <Subject 1>: fully_preserved in [Shot 1] and [Shot 2].\n"
                f"detailed_description: [Shot 1] {BODY}\n[Shot 2] At 00:05.000, {BODY}\n"
                "overall_soundscape: Footsteps.\nnon_diegetic_music: N/A")
        result = module.lint_native(text)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["start_frames"], [0, 120])
        self.assertEqual(result["cut_count"], 1)
        self.assertFalse(module.lint_native(text.replace("At 00:05.000,", "00:05.000"))["ok"])
        self.assertFalse(module.lint_native(text + "\nsummary: Duplicate")["ok"])

    def test_native_single_shot_base_and_uncut_contradiction(self):
        text = f"integrated_multimodal_description: [Shot 1] {BODY}\noverall_soundscape: Wind.\nnon_diegetic_music: N/A"
        self.assertTrue(module.lint_native(text)["ok"])
        multi = text.replace("[Shot 1]", "One continuous shot. [Shot 1]").replace(
            "\noverall_soundscape", f" [Shot 2] At 00:05.000, {BODY}\noverall_soundscape")
        self.assertIn("cut-contradiction", {f["code"] for f in module.lint_native(multi)["findings"]})

    def test_distinct_cut_states_do_not_trigger_camera_conflicts(self):
        bodies = ["[Static wide shot] The dancer sways, teal haze.", BODY]
        self.assertNotIn("camera-conflict", self.codes(cuts([(0, 5), (5, 15)], bodies)))

    def test_appearance_override_and_dialogue_preserved(self):
        body = '[Static wide shot] The dancer wearing a silver top says <d>[English] No, no, not the woman.</d>, teal haze.'
        codes = self.codes(cuts([(0, 15)], [body]), context={"appearance_override": True})
        self.assertNotIn("appearance-prose", codes)
        self.assertNotIn("negative-prose", codes)
        self.assertNotIn("repeated-word", codes)

    def test_environment_and_energy_only_follow_explicit_context(self):
        body = "[Static wide shot] The dancer moves with calm grace, blue light."
        prompt = cuts([(0, 15)], [body])
        codes = self.codes(prompt, context={"high_energy_shots": [1], "environment_suffix": "teal haze."})
        self.assertTrue({"energy-conflict", "environment-lock"} <= codes)
        self.assertNotIn("energy-conflict", self.codes(prompt))

    def test_action_budget_and_no_cut_contradiction(self):
        body = "[Static wide shot] The dancer moves " + "very " * 40 + "fast."
        self.assertIn("action-budget", self.codes(cuts([(0, 1), (1, 15)], [body, BODY])))
        self.assertIn("cut-contradiction", self.codes(cuts([(0, 5), (5, 15)], [BODY + " No cuts.", BODY])))

    def test_cli_exit_codes_and_duplicate_schedule_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            prompt = Path(directory) / "prompt.txt"
            schedule = Path(directory) / "schedule.json"
            prompt.write_text(cuts([(0, 15)]), encoding="utf-8")
            command = [sys.executable, str(SCRIPT), str(prompt), "--duration", "15"]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            prompt.write_text(cuts([(0, 15)], [BODY + " No singing."]), encoding="utf-8")
            self.assertEqual(subprocess.run(command + ["--strict"], capture_output=True).returncode, 1)
            schedule.write_text('{"0":"one","0":"two"}', encoding="utf-8")
            self.assertEqual(subprocess.run(command + ["--schedule", str(schedule)], capture_output=True).returncode, 2)


if __name__ == "__main__":
    unittest.main()
