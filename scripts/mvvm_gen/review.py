"""Side-by-side take review: each setup's seeds are compared as a pair, stored in review/decisions.json.

Takes are grouped by setup (take // seeds): take 0 vs 1 is the main prompt's two seeds, 2 vs 3
the first alternate's, and so on. Each pair is judged on its own (A, B or neither) and no take
carries over into another setup's pair. A setup with one rendered take is kept or rejected alone.
A shot is decided when every setup is; each setup keeps its own winner, and the cut uses the
first setup that has one (main, then alternates in order). Decisions are replayed per setup, so
undo drops the last entry and redoing a setup drops only that setup's entries.
"""

import json
import os
import time

CHOICES = ("a", "b", "neither")


def _setup_round(takes, log):
    """Judge one setup's takes from the front of `log`; more than two seeds meet winner-stays."""
    remaining, leader, rejected, used = list(takes), None, [], 0

    def pair():
        if leader is not None:
            return (leader, remaining[0]) if remaining else None
        if remaining:
            return (remaining[0], remaining[1] if len(remaining) > 1 else None)
        return None

    while (current := pair()) is not None and used < len(log):
        d = log[used]
        if (d.get("a"), d.get("b")) != current:
            raise ValueError(f"decision {d.get('a')}/{d.get('b')} does not match pair {current}")
        a, b = current
        choice = d.get("choice")
        if choice not in CHOICES or (choice == "b" and b is None):
            raise ValueError(f"invalid choice {choice!r} for pair {current}")
        remaining = [t for t in remaining if t not in current]
        if choice == "a":
            leader, rejected = a, rejected + ([b] if b is not None else [])
        elif choice == "b":
            leader, rejected = b, rejected + [a]
        else:
            leader, rejected = None, rejected + [t for t in current if t is not None]
        used += 1
    current = pair()
    return {"pair": current, "rejected": rejected, "used": used,
            "done": current is None, "winner": leader if current is None else None}


def setup_of(take, seeds):
    return take // max(seeds, 1)


def bracket(takes, decisions, seeds=1):
    """Replay `decisions` over `takes` (render order), each setup from its own entries. The next pair
    is the first unfinished setup's. Raises ValueError on a decision that does not match the pair it
    was made against, or on a setup with entries left over after its last pair."""
    groups, by_setup = {}, {}
    for t in takes:
        groups.setdefault(setup_of(t, seeds), []).append(t)
    for d in decisions:
        setup = setup_of(d["a"], seeds) if isinstance(d.get("a"), int) else None
        if setup not in groups:
            raise ValueError(f"decision for take {d.get('a')} matches no rendered setup")
        by_setup.setdefault(setup, []).append(d)
    rejected, setups, pair, pair_setup = [], [], None, None
    for setup, group in groups.items():
        log = by_setup.get(setup, [])
        state = _setup_round(group, log)
        if state["used"] < len(log):
            raise ValueError(f"setup {setup} has {len(log) - state['used']} decision(s) after its last pair")
        rejected += state["rejected"]
        setups.append({"setup": setup, "takes": group, "done": state["done"], "winner": state["winner"]})
        if pair is None and not state["done"]:
            pair, pair_setup = list(state["pair"]), setup
    done = pair is None
    winners = [s["winner"] for s in setups if s["winner"] is not None]
    return {"pair": pair, "setup": pair_setup, "setups": setups, "setupCount": len(groups),
            "rejected": rejected, "done": done, "winner": winners[0] if done and winners else None}


class Store:
    """review/decisions.json: {"shots": {sid: {"decisions": [...]}}}. Callers serialize writes."""

    def __init__(self, root):
        self.path = os.path.join(root, "review", "decisions.json")
        self.data = {"version": 2, "shots": {}}
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as fh:
                self.data = json.load(fh)

    def decisions(self, sid):
        return self.data["shots"].get(sid, {}).get("decisions", [])

    def set_decisions(self, sid, decisions):
        self.data["shots"].setdefault(sid, {})["decisions"] = decisions
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".part"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2)
        os.replace(tmp, self.path)

    def decide(self, sid, takes, seeds, a, b, choice, comment="", clip_ids=None):
        """Append one decision after checking it against the shot's current pair."""
        log = self.decisions(sid)
        entry = {"a": a, "b": b, "choice": choice, "comment": comment.strip(),
                 "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "clips": clip_ids or {}}
        bracket(takes, log + [entry], seeds)
        self.set_decisions(sid, log + [entry])

    def redo(self, sid, seeds, setup):
        """Drop one setup's decisions so its pair comes up again; other setups keep theirs."""
        self.set_decisions(sid, [d for d in self.decisions(sid) if setup_of(d["a"], seeds) != setup])

    def winner(self, sid, takes, seeds):
        """(take, reason): the reviewed winner, or (None, why the review does not decide)."""
        log = self.decisions(sid)
        if not log:
            return None, "not reviewed"
        try:
            state = bracket(takes, log, seeds)
        except ValueError:
            return None, "review no longer matches the rendered takes"
        if not state["done"]:
            return None, "review unfinished"
        return (state["winner"], "reviewed") if state["winner"] is not None else (None, "all takes rejected")
