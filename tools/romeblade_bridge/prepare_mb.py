"""Bake a bridge_battle.json into RomeBladeRTS wave sizes + role mix."""
from __future__ import print_function

import json
import os
import re
import shutil

from . import battle_select
from . import config
from . import edu_map


def battle_json_in_module():
    return os.path.join(config.MB_MODULE_DIR, "bridge_battle.json")


def _role_triple(fingerprint):
    roles = edu_map.role_counts(fingerprint)
    inf = int(roles.get("infantry", 0))
    mis = int(roles.get("missile", 0))
    cav = int(roles.get("cavalry", 0))
    if inf + mis + cav <= 0:
        return 1, 0, 0
    return inf, mis, cav


def prepare_from_spec(spec, out_json=None):
    """Write battle JSON and patch menus.txt army totals + role headcounts."""
    out_json = out_json or battle_select.default_battle_json_path()
    battle_select.write_battle_json(spec, out_json)
    mod_json = battle_json_in_module()
    os.makedirs(config.MB_MODULE_DIR, exist_ok=True)
    shutil.copyfile(out_json, mod_json)

    men_a = int(spec["army_a"]["men"])
    men_b = int(spec["army_b"]["men"])
    inf_a, mis_a, cav_a = _role_triple(spec["army_a"]["fingerprint"])
    inf_b, mis_b, cav_b = _role_triple(spec["army_b"]["fingerprint"])
    plan_a = edu_map.troop_plan(spec["army_a"]["fingerprint"], "player")
    plan_b = edu_map.troop_plan(spec["army_b"]["fingerprint"], "enemy")

    meta = {
        "army_a_men": men_a,
        "army_b_men": men_b,
        "roles_a": {"infantry": inf_a, "missile": mis_a, "cavalry": cav_a},
        "roles_b": {"infantry": inf_b, "missile": mis_b, "cavalry": cav_b},
        "plan_a": plan_a,
        "plan_b": plan_b,
        "source_save": spec.get("source_save"),
        "battle_json": out_json,
        "module_json": mod_json,
    }
    meta_path = os.path.join(config.REPO_ROOT, "out", "bridge_mb_meta.json")
    os.makedirs(os.path.dirname(meta_path), exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    patched = patch_menus_wave_immediates(
        men_a, men_b, inf_a, mis_a, cav_a, inf_b, mis_b, cav_b
    )
    meta["menus_patched"] = patched
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta


def patch_menus_wave_immediates(
    men_a, men_b, inf_a, mis_a, cav_a, inf_b, mis_b, cav_b
):
    """Patch the eight leading assign immediates of the wave ops block.

    Compiled shape (after build):
      mno_romeblade_wave_battle_entry 0 <title> <opcount>
      2133 2 <var_army_a> <men_a>
      2133 2 <var_army_b> <men_b>
      2133 2 <var_inf_a> <inf_a>
      ... mis_a, cav_a, inf_b, mis_b, cav_b
    Same octet appears in start_game_1 / start_game_3 INIT.
    """
    path = os.path.join(config.MB_MODULE_DIR, "menus.txt")
    if not os.path.isfile(path):
        return {"ok": False, "reason": "menus.txt missing"}
    text = open(path, "r", encoding="utf-8", errors="ignore").read()
    vals = [
        int(men_a),
        int(men_b),
        int(inf_a),
        int(mis_a),
        int(cav_a),
        int(inf_b),
        int(mis_b),
        int(cav_b),
    ]

    head = re.search(
        r"mno_romeblade_wave_battle_entry\s+0\s+(\S+)\s+(\d+)\s+"
        r"2133\s+2\s+(\d+)\s+(\d+)\s+"
        r"2133\s+2\s+(\d+)\s+(\d+)\s+"
        r"2133\s+2\s+(\d+)\s+(\d+)\s+"
        r"2133\s+2\s+(\d+)\s+(\d+)\s+"
        r"2133\s+2\s+(\d+)\s+(\d+)\s+"
        r"2133\s+2\s+(\d+)\s+(\d+)\s+"
        r"2133\s+2\s+(\d+)\s+(\d+)\s+"
        r"2133\s+2\s+(\d+)\s+(\d+)",
        text,
    )
    if not head:
        return {"ok": False, "reason": "wave 8-assign block not found"}

    old_title = head.group(1)
    # groups: title, opcount, then (var, val) x8 → vars at 3,5,7,..., vals at 4,6,8,...
    old_vals = [int(head.group(4 + 2 * i)) for i in range(8)]
    vars_ = [head.group(3 + 2 * i) for i in range(8)]

    # Build regex for the octet of assign pairs (whitespace between pairs).
    pair_bits = []
    for i in range(8):
        if i:
            pair_bits.append(r"\s+")
        pair_bits.append(
            r"(2133\s+2\s+" + re.escape(vars_[i]) + r"\s+)" + re.escape(str(old_vals[i]))
        )
    octet = re.compile("".join(pair_bits))

    def _sub_octet(_m):
        # Groups are only the '(2133 2 VAR )' prefixes; re-insert spaces between pairs.
        out = []
        for i in range(8):
            if i:
                out.append(" ")
            out.append(_m.group(i + 1) + str(vals[i]))
        return "".join(out)

    text2, n_pairs = octet.subn(_sub_octet, text)
    if n_pairs < 1:
        return {
            "ok": False,
            "reason": "octet replace failed",
            "old_vals": old_vals,
        }

    new_title = "RomeBlade_Wave_Battle_(%d_vs_%d)" % (vals[0], vals[1])
    text2 = text2.replace(old_title, new_title, 1)

    bak = path + ".rb_bak"
    if not os.path.isfile(bak):
        shutil.copyfile(path, bak)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text2)
    return {
        "ok": True,
        "vals": vals,
        "old_vals": old_vals,
        "blocks_patched": n_pairs,
        "title": new_title,
        "backup": bak,
    }


# Back-compat alias used by older call sites / docs.
def patch_menus_army_sizes(men_a, men_b):
    return patch_menus_wave_immediates(men_a, men_b, men_a, 0, 0, men_b, 0, 0)


def prepare_from_save_indices(save_path, index_a, index_b):
    armies = battle_select.list_battle_armies(save_path)
    a, b = battle_select.select_pair_by_indices(armies, index_a, index_b)
    spec = battle_select.battle_spec(save_path, a, b)
    return prepare_from_spec(spec)


def prepare_from_fingerprints(save_path, fp_a, fp_b, max_distance=0):
    armies = battle_select.list_battle_armies(save_path)
    a, b = battle_select.select_pair_by_fingerprints(
        armies, fp_a, fp_b, max_distance=max_distance
    )
    spec = battle_select.battle_spec(save_path, a, b)
    return prepare_from_spec(spec)
