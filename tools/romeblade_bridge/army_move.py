"""Detect army moves / splits by diffing two saves (composition + captains)."""
from __future__ import print_function

import re
from collections import Counter

from . import battle_select


def list_captain_cards(data, faction=None):
    """Offsets of captain_card_<fac>.tga paths in file order."""
    out = []
    for m in re.finditer(
        br"data/ui/captain banners/captain_card_([a-z_]+)\.tga\x00", data
    ):
        fac = m.group(1).decode("ascii", errors="ignore")
        if fac.endswith("_rebel"):
            continue
        if faction and fac != faction:
            continue
        out.append({"off": m.start(), "faction": fac})
    return out


def attach_captain(data, army, back=80000):
    """Nearest preceding captain_card for this army block."""
    start = max(0, army["name_off0"] - back)
    window = data[start : army["name_off0"]]
    key = b"captain_card_"
    i = window.rfind(key)
    if i < 0:
        army["captain_off"] = None
        return army
    army["captain_off"] = start + i
    j = i + len(key)
    end = window.find(b".tga", j)
    if 0 < end - j <= 40:
        army["captain_faction"] = window[j:end].decode("ascii", errors="ignore")
    return army


def enrich_with_captains(save_path):
    data = open(save_path, "rb").read()
    armies = battle_select.list_battle_armies(save_path)
    return [attach_captain(data, dict(a)) for a in armies]


def _fp_key(fp):
    return tuple(sorted((fp or {}).items()))


def diff_army_moves(before_path, after_path, player_faction=None):
    """Compare two saves; report fingerprint transfers and new captains.

    Used after the user moved a stack out of a city (proba_all17 overwrite).
    """
    player = player_faction or battle_select.player_faction_from_save(after_path)
    before = enrich_with_captains(before_path)
    after = enrich_with_captains(after_path)
    if player:
        before = [a for a in before if a.get("faction_guess") == player]
        after = [a for a in after if a.get("faction_guess") == player]

    b_data = open(before_path, "rb").read()
    a_data = open(after_path, "rb").read()
    caps_b = list_captain_cards(b_data, player)
    caps_a = list_captain_cards(a_data, player)

    before_by_fp = {_fp_key(a["fingerprint"]): a for a in before}
    after_by_fp = {_fp_key(a["fingerprint"]): a for a in after}

    lost = [before_by_fp[k] for k in before_by_fp if k not in after_by_fp]
    gained = [after_by_fp[k] for k in after_by_fp if k not in before_by_fp]
    shifted = []
    for k, ao in after_by_fp.items():
        if k in before_by_fp and before_by_fp[k]["name_off0"] != ao["name_off0"]:
            shifted.append(
                {
                    "men": ao["summary"]["men"],
                    "off_before": before_by_fp[k]["name_off0"],
                    "off_after": ao["name_off0"],
                }
            )

    # Guess a transfer: lost + gained with complementary Counter deltas
    transfers = []
    for lo in lost:
        for ga in gained:
            # units that appear in gained but not lost composition relative to a
            # third unchanged stack — handled by caller for the known case.
            transfers.append(
                {
                    "from_men": lo["summary"]["men"],
                    "to_men": ga["summary"]["men"],
                    "from_fp": lo["fingerprint"],
                    "to_fp": ga["fingerprint"],
                    "from_off": lo["name_off0"],
                    "to_off": ga["name_off0"],
                }
            )

    return {
        "player_faction": player,
        "size_before": len(b_data),
        "size_after": len(a_data),
        "captains_before": len(caps_b),
        "captains_after": len(caps_a),
        "new_captains": max(0, len(caps_a) - len(caps_b)),
        "lost_fingerprints": [
            {"men": a["summary"]["men"], "off": a["name_off0"], "fp": a["fingerprint"]}
            for a in lost
        ],
        "gained_fingerprints": [
            {"men": a["summary"]["men"], "off": a["name_off0"], "fp": a["fingerprint"]}
            for a in gained
        ],
        "shifted": shifted,
        "transfers": transfers,
    }


def select_hostile_pair_near_player(save_path, max_candidates=5):
    """Offline stand-in: player stacks vs non-player, ranked by men (not map dist).

    Map adjacency still blocked. Returns candidate pairs for a manifest.
    """
    armies = enrich_with_captains(save_path)
    player = battle_select.player_faction_from_save(save_path)
    mine = [a for a in armies if a.get("faction_guess") == player]
    foe = [a for a in armies if a.get("faction_guess") and a.get("faction_guess") != player]
    mine.sort(key=lambda a: -a["summary"]["men"])
    foe.sort(key=lambda a: -a["summary"]["men"])
    pairs = []
    for a in mine[:max_candidates]:
        for b in foe[:max_candidates]:
            pairs.append(
                {
                    "index_a": a["index"],
                    "index_b": b["index"],
                    "men_a": a["summary"]["men"],
                    "men_b": b["summary"]["men"],
                    "faction_a": a.get("faction_guess"),
                    "faction_b": b.get("faction_guess"),
                }
            )
    return {"player_faction": player, "candidates": pairs[:max_candidates]}
