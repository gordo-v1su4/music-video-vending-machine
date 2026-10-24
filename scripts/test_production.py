import json
import os
import shutil
import subprocess
import tempfile
import unittest

from mvvm_gen import h3lint
from mvvm_gen.production import Conflict, Production, fingerprint
from mvvm_gen.production_review import Edit, Repairs, Review

PACKET = os.path.join(os.path.dirname(__file__), "mvvm_gen", "plans", "i-ran-demo-packet.json")
MAP = {"subjects": {"1": "Rafa"}, "pictures": {"1": "gorge"}, "audios": {"1": "song"},
       "guides": [{"name": "B", "frame": 120}]}
VALID = """subject_definitions: <Subject 1> is Rafa, a young man in an open olive shirt. <Picture 1> is the night gorge. <Audio 1> is the song.
summary: [reference generation + audio reference] Rafa falls backward off the ledge into fog.
retention_analysis: <Subject 1>: fully_preserved. <Picture 1>: fully_preserved. <Audio 1>: reference.
detailed_description: One continuous shot. The crumbling edge drops away under his boot and his body keeps travelling down and back into the mist.
overall_soundscape: Rumbling earth, wind rushing past.
non_diegetic_music: <Audio 1> drives the cut."""


class LintTests(unittest.TestCase):
    def test_valid_prompt_passes(self):
        r = h3lint.lint(VALID, MAP, 12)
        self.assertTrue(r["ok"], r["findings"])
        self.assertEqual(r["frames"], 294)

    def test_frame_grid_matches_workflow_expression(self):
        for s in (5, 8.3, 11.84, 14):
            n = h3lint.h3_frames(s)
            self.assertEqual((n - 5) % 17, 0)
        self.assertEqual(h3lint.h3_frames(14), 345)

    def test_unknown_picture_and_missing_section_are_errors(self):
        bad = VALID.replace("<Picture 1> is the night gorge.", "<Picture 2> is the guide image.").replace(
            "overall_soundscape: Rumbling earth, wind rushing past.\n", "")
        codes = {f["code"] for f in h3lint.lint(bad, MAP, 12)["findings"]}
        self.assertIn("unknown-label", codes)
        self.assertIn("missing-section", codes)

    def test_cut_contradiction_and_range(self):
        bad = VALID.replace("into the mist.", "into the mist. [Shot 2] At 00:13.000, a close-up.")
        codes = [f["code"] for f in h3lint.lint(bad, MAP, 12)["findings"]]
        self.assertIn("cut-contradiction", codes)
        self.assertIn("cut-range", codes)

    def test_negated_action_list_is_flagged(self):
        bad = VALID.replace("keeps travelling down", "never stops, does not sit or crouch, and keeps travelling down")
        self.assertIn("negated-action", [f["code"] for f in h3lint.lint(bad, MAP, 12)["findings"]])

    def test_guide_out_of_range_and_stale_revision(self):
        r = h3lint.lint(VALID, dict(MAP, guides=[{"name": "B", "frame": 400}]), 12, packet_revision=3, expected_revision=4)
        codes = {f["code"] for f in r["findings"]}
        self.assertEqual(codes & {"guide-range", "stale-packet"}, {"guide-range", "stale-packet"})
        self.assertFalse(r["ok"])


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.prod = Production(self.root)
        with open(PACKET, encoding="utf-8") as fh:
            self.seed = json.load(fh)
        self.prod.save_packet(self.seed, expected_revision=None)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_pending_identity_blocks_approval_and_reference_change_invalidates(self):
        p = self.prod.packet()
        self.assertIn("lune-sheet: identity reference is pending", p["blocking"])
        with self.assertRaises(Conflict):
            self.prod.approve("director", p["revision"])
        p = self.prod.decide_reference("lune-sheet", "approved", "Look matches sheet", p["revision"])
        p = self.prod.approve("director", p["revision"])
        self.assertTrue(p["approved"])
        p = self.prod.decide_reference("festival", "rejected", "wrong stage", p["revision"])
        self.assertFalse(p["approved"])
        self.assertIn("packet changed since approval; re-approve", p["blocking"])

    def test_stale_revision_conflicts(self):
        p = self.prod.packet()
        self.prod.decide_reference("gorge", "approved", "", p["revision"])
        with self.assertRaises(Conflict):
            self.prod.decide_reference("gorge", "rejected", "", p["revision"])

    def test_fingerprint_ignores_bookkeeping(self):
        a = dict(self.seed, revision=1, updated_at="x")
        b = dict(self.seed, revision=9, updated_at="y")
        self.assertEqual(fingerprint(a), fingerprint(b))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "needs ffmpeg")
class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.clip = os.path.join(self.root, "two-shot.mp4")
        # Two visually distinct 1 s shots: a supplied multi-shot clip.
        subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=red:s=160x90:d=1:r=24",
                        "-f", "lavfi", "-i", "color=c=blue:s=160x90:d=1:r=24", "-filter_complex",
                        "[0][1]concat=n=2:v=1:a=0", "-pix_fmt", "yuv420p", self.clip], check=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_import_review_reload_keeps_lineage(self):
        prod = Production(self.root)
        clip = prod.add_clip(self.clip, "supplied", {"note": "fixture"})
        self.assertEqual(clip["media"]["frames"], 48)
        proposed = prod.propose_cuts(clip["id"])
        self.assertEqual([(s["in"], s["out"]) for s in proposed], [(0, 24), (24, 48)])
        self.assertTrue(all(s["status"] == "proposed" for s in proposed))
        prod.set_shots(clip["id"], [dict(proposed[0], status="reviewed"), proposed[1]], "editor")
        again = Production(self.root).registry()["clips"][clip["id"]]
        self.assertEqual([s["status"] for s in again["shots"]], ["reviewed", "proposed"])
        self.assertEqual(again["lineage"], {"note": "fixture"})
        self.assertEqual(prod.add_clip(self.clip, "supplied")["id"], clip["id"])

    def test_invalid_ranges_rejected(self):
        prod = Production(self.root)
        clip = prod.add_clip(self.clip, "supplied")
        with self.assertRaises(Conflict):
            prod.set_shots(clip["id"], [{"in": 10, "out": 60}], "editor")
        with self.assertRaises(Conflict):
            prod.set_shots(clip["id"], [{"in": 0, "out": 30}, {"in": 20, "out": 40}], "editor")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "needs ffmpeg")
class ReviewEditTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.prod = Production(self.root)
        with open(PACKET, encoding="utf-8") as fh:
            self.prod.save_packet(json.load(fh), expected_revision=None)
        self.start = self.prod.packet()["sequence"]["song_start_s"]
        self.song = os.path.join(self.root, "song.wav")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=f=220:d={self.start + 10}",
                        self.song], check=True)
        self.clips = []
        for i, colour in enumerate(("red", "blue")):
            path = os.path.join(self.root, f"c{i}.mp4")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c={colour}:s=160x90:d=2:r=24",
                            "-metadata", "comment=secret prompt text", "-pix_fmt", "yuv420p", path], check=True)
            self.clips.append(self.prod.add_clip(path, "generated", label=f"cand-{i}"))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_blind_media_strips_prompt_and_reports_are_write_once(self):
        rev = Review(self.prod)
        media = rev.blind(["cand-0", "cand-1"], seed=1)
        bid = next(iter(media))
        tags = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags", "-of", "json", media[bid]],
                              capture_output=True, text=True).stdout
        self.assertNotIn("secret prompt text", tags)
        ident = {"provider": "test", "model": "m", "access": "sampled frames"}
        rev.save_report("r1", ident, bid, [{"scope": "clip", "kind": "brief", "severity": "hard", "gate": "identity",
                                             "text": "face drifts", "scores": {"identity": 2, "bogus": 9}}])
        with self.assertRaises(Conflict):
            rev.save_report("r1", ident, bid, [])
        f = rev.import_reports()[0]
        self.assertEqual(f["gate_status"], "alleged")
        self.assertEqual(f["scores"], {"identity": 2})
        self.assertFalse(rev.hard_blocked(f["candidate"]))
        rev.set_gate(f["id"], "confirmed", "director")
        self.assertTrue(rev.hard_blocked(f["candidate"]))
        self.assertEqual(rev.import_reports()[0]["gate_status"], "confirmed")  # survives re-import

    def test_build_keep_unsafe_join_and_restore(self):
        edit = Edit(self.prod, master=self.song)
        segs = [{"clip_id": self.clips[0]["id"], "in_s": 0.5, "out_s": 1.5, "song_s": self.start},
                {"clip_id": self.clips[1]["id"], "in_s": 0, "out_s": 1.25, "song_s": self.start + 1}]
        a = edit.build("a", "A", segs, [{"at_s": self.start + 1, "verdict": "valid", "reasons": ["match"]}])
        self.assertTrue(a["timing"]["within_one_frame"])
        self.assertEqual(a["timing"]["actual_frames"], 54)
        b = edit.build("b", "B", segs[:1], [{"at_s": self.start + 1, "verdict": "unsafe", "reasons": ["jump"]}])
        with self.assertRaises(Conflict):
            edit.act("b", "keep")
        self.assertIsNone(edit.state()["active"])  # building never activates
        edit.act("a", "keep")
        c = edit.build("c", "C", segs[:1], [], repair_of="a")
        edit.act("c", "keep")
        self.assertEqual(edit.state()["active"], "c")
        self.assertEqual(edit.act("c", "restore")["active"], "a")
        with self.assertRaises(Conflict):
            edit.build("d", "D", [dict(segs[1], song_s=self.start + 3)], [])

    def test_repair_allowance_and_existing_media_costs_nothing(self):
        rev = Review(self.prod)
        bid = next(iter(rev.blind(["cand-0"], seed=2)))
        rev.save_report("r1", {"provider": "t", "model": "m", "access": "x"}, bid,
                        [{"scope": "shot", "kind": "technical", "severity": "major", "text": "bad open"}])
        fid = rev.import_reports()[0]["id"]
        reps = Repairs(self.prod)
        trim = reps.propose(fid, "trim", "cand-0 0-1 s", "cut the bad opening")
        self.assertEqual(trim["gpu_attempts"], 0)
        reps.decide(trim["id"], "approved", "director")
        reps.applied(trim["id"], "edit:x")
        allowed = self.prod.packet()["allowance"]["repair_renders"]
        for i in range(allowed):
            r = reps.propose(fid, "rerender", "cand-0", "again")
            reps.decide(r["id"], "approved", "director")
            reps.applied(r["id"], f"cand-r{i}", gpu_attempts_used=1)
        extra = reps.propose(fid, "rerender", "cand-0", "once more")
        with self.assertRaises(Conflict):
            reps.decide(extra["id"], "approved", "director")


if __name__ == "__main__":
    unittest.main()
