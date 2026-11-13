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


def captain_card_faction(data, name_off, back=80000):
    """Faction from the nearest preceding captain_card_*.tga path (reliable)."""
    start = max(0, name_off - back)
    window = data[start:name_off]
    key = b"captain_card_"
    i = window.rfind(key)
    if i < 0:
        return None
    j = i + len(key)
    end = window.find(b".tga", j)
    if end < 0 or end - j > 40:
        return None
    return window[j:end].decode("ascii", errors="ignore")


def detect_player_faction(armies, hint=None):
    """Player faction for this campaign.

    Prefer an explicit hint (manifest / config). Otherwise, if Julii stacks
    exist this project treats them as the human side (RomaAroma / imperial
    campaign). Fall back to the roman_* with the most stacks, then any top
    faction by men — never 'whoever has the biggest AI doomstack'.
    """
    if hint:
        return hint
    by_men = Counter()
    by_stacks = Counter()
    for a in armies:
        fac = a.get("faction_guess")
        if not fac:
            continue
        by_men[fac] += a["summary"]["men"]
        by_stacks[fac] += 1
    if not by_men:
        return None
    if "romans_julii" in by_stacks:
        return "romans_julii"
    romans = [k for k in by_stacks if k.startswith("romans_")]
    if romans:
        return max(romans, key=lambda k: (by_stacks[k], by_men[k]))
    return max(by_men.items(), key=lambda kv: kv[1])[0]

def enrich_army(data, army):
    by = army["summary"]["by_type"]
    army = dict(army)
    army["culture"] = edu_culture(by)
    card = captain_card_faction(data, army["name_off0"])
    army["faction_guess"] = card or nearest_faction(data, army["name_off0"])
    army["fingerprint"] = dict(sorted(by.items()))
    army["has_general"] = any(
        u["name"] and armies_mod_is_general(u["name"]) for u in army["units"]
    )
    return army


def armies_mod_is_general(name):
    from . import save_io

    return save_io.is_general_unit(name)


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


def pending_manifest_path():
    return os.path.join(config.REPO_ROOT, "out", "bridge_pending_battle.json")


def load_pending_manifest(path=None):
    path = path or pending_manifest_path()
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def select_pair_from_manifest(armies, manifest):
    """Resolve a pending-battle manifest to two armies.

    Manifest forms (first match wins):
      {"index_a": int, "index_b": int}
      {"fingerprint_a": {...}, "fingerprint_b": {...}, "max_distance": 0}
    """
    if manifest is None:
        raise LookupError("no pending battle manifest")
    if "index_a" in manifest and "index_b" in manifest:
        return select_pair_by_indices(
            armies, int(manifest["index_a"]), int(manifest["index_b"])
        )
    if "fingerprint_a" in manifest and "fingerprint_b" in manifest:
        return select_pair_by_fingerprints(
            armies,
            manifest["fingerprint_a"],
            manifest["fingerprint_b"],
            max_distance=int(manifest.get("max_distance", 0)),
        )
    raise LookupError("manifest needs index_a/b or fingerprint_a/b")


def select_battle_pair(save_path, manifest=None, manifest_path=None):
    """Pick the two armies for a fight.

    Order of attempts:
      1) explicit pending manifest (indices or composition fingerprints)
      2) blocked — map-adjacency / scroll identity is not decoded yet

    Returns (army_a, army_b, meta). Raises LookupError when blocked.
    """
    armies = list_battle_armies(save_path)
    man = manifest
    if man is None:
        man = load_pending_manifest(manifest_path)
    player = detect_player_faction(
        armies, hint=(man or {}).get("player_faction") if man else None
    )
    meta = {
        "player_faction": player,
        "army_count": len(armies),
        "method": None,
    }
    if man is not None:
        a, b = select_pair_from_manifest(armies, man)
        # Prefer player stack as army_a when detectable.
        if player and a.get("faction_guess") != player and b.get("faction_guess") == player:
            a, b = b, a
        meta["method"] = "manifest"
        meta["manifest"] = man
        return a, b, meta
    raise LookupError(
        "battle pair blocked: need out/bridge_pending_battle.json with "
        "index_a/index_b or fingerprint_a/fingerprint_b — map positions "
        "for adjacency are not decoded in the RTW 1.5 save yet "
        "(player_faction=%s, armies=%d)" % (player, len(armies))
    )


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
