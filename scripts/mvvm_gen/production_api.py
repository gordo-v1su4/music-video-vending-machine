"""HTTP routes for the production journey (apps/web route /production), mounted by review_server under
/pilot-api/production. Thin JSON wrappers over production.Production; media and reference images are
served read-only from paths recorded in the packet/registry, never from request-supplied paths.
"""

import json
import os
import re
import time

from . import h3lint
from .production import Conflict, Production
from .production_review import Edit, Repairs, Review

MAX_BODY = 256 * 1024


class ProductionAPI:
    def __init__(self, run_factory):
        self.run_factory = run_factory

    def prod(self):
        return Production(self.run_factory().root)

    def _read(self, path, default):
        if not os.path.exists(path):
            return default
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    def state(self):
        prod = self.prod()
        p = prod.packet()
        reg = prod.registry()
        prompts = self._read(os.path.join(prod.dir, "prompts.json"), {})
        reviews = self._read(os.path.join(prod.dir, "reviews", "findings.json"), [])
        edit = Edit(prod).state()
        runs = self._read(os.path.join(prod.dir, "runs.json"), [])
        return {"packet": p, "clips": list(reg["clips"].values()), "prompts": prompts, "runs": runs,
                "findings": reviews, "edit": edit, "song": self.song(p),
                "teams": self._read(os.path.join(prod.dir, "private", "teams.json"), {}),
                "repairs": Repairs(prod).all(), "repair_allowance": Repairs(prod).allowance()}

    def song(self, packet):
        """The studio's existing analysis for the passage: edit-plan chunks with sections, roles and energy."""
        plan = self._read(self.run_factory().path("edit-plan.json"), None)
        if not plan:
            return {"chunks": [], "bpm": None}
        start, end = packet["sequence"]["song_start_s"] * 1000, packet["sequence"]["song_end_s"] * 1000
        chunks = [{"index": c["index"], "start_s": c["startMs"] / 1000, "end_s": c["endMs"] / 1000,
                   "sections": c["sections"],
                   "shots": [{"start_s": x["startMs"] / 1000, "role": x["role"], "energy": x["energy"]} for x in c["shots"]]}
                  for c in plan["chunks"] if c["endMs"] > start and c["startMs"] < end]
        return {"chunks": chunks, "bpm": plan.get("bpm"), "source": "edit-plan.json"}

    # GET -----------------------------------------------------------------------------------------------
    def get(self, path):
        if path == "/pilot-api/production":
            return 200, self.state()
        m = re.fullmatch(r"/pilot-api/production/ref-image/([a-z0-9-]+)", path)
        if m:
            ref = next((r for r in self.prod().packet()["references"] if r["id"] == m.group(1)), None)
            return ("file", ref["path"]) if ref and os.path.splitext(ref["path"])[1].lower() in (".png", ".jpg", ".jpeg", ".webp") else (404, {"error": "no image"})
        m = re.fullmatch(r"/pilot-api/production/media/(clip-[0-9a-f]{12})", path)
        if m:
            clip = self.prod().registry()["clips"].get(m.group(1))
            return ("media", clip["path"]) if clip else (404, {"error": "unknown clip"})
        m = re.fullmatch(r"/pilot-api/production/edit-media/([a-z0-9-]+\.mp4)", path)
        if m:
            return "media", os.path.join(self.prod().dir, "edits", m.group(1))
        return None

    # POST ----------------------------------------------------------------------------------------------
    def post(self, path, body):
        prod = self.prod()
        try:
            m = re.fullmatch(r"/pilot-api/production/reference/([a-z0-9-]+)/decide", path)
            if m:
                return 200, prod.decide_reference(m.group(1), body.get("decision"), str(body.get("note", "")), body.get("revision"))
            if path == "/pilot-api/production/plan":
                return 200, prod.edit_plan(body.get("slot"), body.get("fields"), body.get("brief"), body.get("revision"))
            if path == "/pilot-api/production/approve":
                return 200, prod.approve(str(body.get("by", "director"))[:80], body.get("revision"))
            if path == "/pilot-api/production/lint":
                p = prod.packet()
                return 200, h3lint.lint(str(body.get("text", "")), body.get("input_map") or {}, float(body.get("duration", 0)),
                                        packet_revision=body.get("revision"), expected_revision=p["revision"],
                                        cuts=body.get("cuts"))
            if path == "/pilot-api/production/prompt/save":
                return 200, self.save_prompt(prod, body)
            m = re.fullmatch(r"/pilot-api/production/clip/(clip-[0-9a-f]{12})/shots", path)
            if m:
                return 200, prod.set_shots(m.group(1), body.get("shots") or [], str(body.get("by", "editor"))[:80])
            m = re.fullmatch(r"/pilot-api/production/edit/([a-z0-9-]+)/(keep|reject|restore)", path)
            if m:
                return 200, Edit(prod).act(m.group(1), m.group(2), str(body.get("by", "director"))[:80])
            if path == "/pilot-api/production/gate":
                return 200, Review(prod).set_gate(str(body.get("finding")), body.get("status"), str(body.get("by", "director"))[:80])
            if path == "/pilot-api/production/repair/propose":
                return 200, Repairs(prod).propose(str(body.get("finding")), body.get("kind"), str(body.get("scope", "")),
                                                  str(body.get("rationale", "")), body.get("neighbors"))
            m = re.fullmatch(r"/pilot-api/production/repair/(R[0-9]+)/decide", path)
            if m:
                return 200, Repairs(prod).decide(m.group(1), body.get("decision"), str(body.get("by", "director"))[:80])
            m = re.fullmatch(r"/pilot-api/production/clip/(clip-[0-9a-f]{12})/propose-cuts", path)
            if m:
                return 200, {"proposed": prod.propose_cuts(m.group(1))}
        except LookupError as exc:
            return 404, {"error": str(exc)}
        except (Conflict, ValueError, TypeError, PermissionError) as exc:
            return 409, {"error": str(exc)}
        return None

    def save_prompt(self, prod, body):
        """Persist the exact prompt text and its lint result against the current packet revision."""
        p = prod.packet()
        name = str(body.get("name", ""))
        if not re.fullmatch(r"[A-Za-z0-9 _.-]{1,60}", name):
            raise Conflict("prompt name must be 1-60 plain characters")
        text = str(body.get("text", ""))
        lint = h3lint.lint(text, body.get("input_map") or {}, float(body.get("duration", 0)),
                           packet_revision=p["revision"], expected_revision=p["revision"], cuts=body.get("cuts"))
        path = os.path.join(prod.dir, "prompts.json")
        prompts = self._read(path, {})
        prompts[name] = {"slot": body.get("slot"), "text": text, "input_map": body.get("input_map"),
                         "duration": body.get("duration"), "cuts": body.get("cuts"), "packet_revision": p["revision"],
                         "lint": lint, "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        os.makedirs(prod.dir, exist_ok=True)
        with open(path + ".part", "w", encoding="utf-8") as fh:
            json.dump(prompts, fh, indent=1, ensure_ascii=False)
        os.replace(path + ".part", path)
        return prompts[name]
