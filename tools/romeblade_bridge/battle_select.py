"""Identify the two armies of a fight from an RTW save.

Live scroll reading is deferred (no RTW automation while the user plays).
The reliable offline method is **composition match**: each army block has a
fingerprint of EDU type -> current soldiers; the two stacks on a pre-battle
scroll are the unique pair whose fingerprints match the scroll's counts.

Also supports explicit army indices (from a pending-battle manifest the
bridge will write once scroll detection is allowed again).
"""
from __future__ import print_function

import json
import os
from collections import Counter

from . import armies as armies_mod
from . import config

FACTION_STRINGS = [
    "romans_julii",
    "romans_brutii",
    "romans_scipii",
    "egypt",
    "greek_cities",
    "gauls",
    "britons",
    "carthage",
    "spain",
    "macedon",
    "seleucid",
    "parthia",
    "pontus",
    "armenia",
    "dacia",
    "scythia",
    "germania",
    "thrace",
    "numidia",
    "slave",
]

EDU_CULTURE = [
    ("roman ", "roman"),
    ("egyptian ", "egypt"),
    ("greek ", "greek"),
    ("carthaginian ", "carthage"),
    ("numidian ", "numidia"),
    ("east ", "east"),
    ("barb ", "barb"),
    ("warband ", "barb"),
]


def edu_culture(by_type):
    for pref, cult in EDU_CULTURE:
        if any(k.startswith(pref) for k in by_type):
            return cult
    return "unknown"


def nearest_faction(data, name_off, back=60000):
    start = max(0, name_off - back)
    window = data[start:name_off]
    best = None
    for f in FACTION_STRINGS:
        i = window.rfind(f.encode("ascii"))
        if i < 0:
            continue
        dist = len(window) - i
        if best is None or dist < best[0]:
            best = (dist, f)
    return best[1] if best else None


def enrich_army(data, army):
    by = army["summary"]["by_type"]
    army = dict(army)
    army["culture"] = edu_culture(by)
    army["faction_guess"] = nearest_faction(data, army["name_off0"])
    army["fingerprint"] = dict(sorted(by.items()))
    return army


def list_battle_armies(save_path):
    data = open(save_path, "rb").read()
    raw = armies_mod.armies_from_save(save_path)
    return [enrich_army(data, a) for a in raw]


def fingerprint_distance(fp_a, fp_b):
    """L1 distance over type counts; missing types count as 0."""
    keys = set(fp_a) | set(fp_b)
    return sum(abs(fp_a.get(k, 0) - fp_b.get(k, 0)) for k in keys)


def find_army_by_fingerprint(armies, fingerprint, max_distance=0):
    """Return (army, distance) best match; None if best distance > max_distance."""
    best = None
    for a in armies:
        d = fingerprint_distance(a["fingerprint"], fingerprint)
        if best is None or d < best[1]:
            best = (a, d)
    if best is None or best[1] > max_distance:
        return None
    return best


def select_pair_by_indices(armies, index_a, index_b):
    by_idx = {a["index"]: a for a in armies}
    if index_a not in by_idx or index_b not in by_idx:
        raise KeyError("army index not found: %s %s" % (index_a, index_b))
    return by_idx[index_a], by_idx[index_b]


def select_pair_by_fingerprints(armies, fp_a, fp_b, max_distance=0):
    ma = find_army_by_fingerprint(armies, fp_a, max_distance=max_distance)
    mb = find_army_by_fingerprint(armies, fp_b, max_distance=max_distance)
    if not ma or not mb:
        raise LookupError(
            "could not match fingerprints (a=%s b=%s)" % (ma, mb)
        )
    if ma[0]["index"] == mb[0]["index"]:
        raise LookupError("both fingerprints matched the same army")
    return ma[0], mb[0]


def battle_spec(save_path, army_a, army_b):
    """Serializable battle description for M&B prep and result write-back."""
    def side(a):
        units = []
        for u in a["units"]:
            units.append(
                {
                    "name": u["name"],
                    "name_off": u["name_off"],
                    "cur_off": u["cur_off"],
                    "current": u["current"],
                    "full": u["full"],
                }
            )
        return {
            "index": a["index"],
            "men": a["summary"]["men"],
            "units": a["summary"]["units"],
            "culture": a.get("culture"),
            "faction_guess": a.get("faction_guess"),
            "fingerprint": a["fingerprint"],
            "unit_rows": units,
        }

    return {
        "source_save": os.path.abspath(save_path),
        "army_a": side(army_a),
        "army_b": side(army_b),
    }


def write_battle_json(spec, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, sort_keys=True)
    return path


def load_battle_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def default_battle_json_path():
    return os.path.join(config.REPO_ROOT, "out", "bridge_battle.json")
