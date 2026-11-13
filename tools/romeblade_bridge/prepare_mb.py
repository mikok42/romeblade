"""Bake a bridge_battle.json into RomeBladeRTS wave sizes (no RTW needed)."""
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


def prepare_from_spec(spec, out_json=None):
    """Write battle JSON (repo out/ + module copy) and patch installed menus.txt sizes."""
    out_json = out_json or battle_select.default_battle_json_path()
    battle_select.write_battle_json(spec, out_json)
    mod_json = battle_json_in_module()
    os.makedirs(config.MB_MODULE_DIR, exist_ok=True)
    shutil.copyfile(out_json, mod_json)

    men_a = int(spec["army_a"]["men"])
    men_b = int(spec["army_b"]["men"])
    plan_a = edu_map.troop_plan(spec["army_a"]["fingerprint"], "player")
    plan_b = edu_map.troop_plan(spec["army_b"]["fingerprint"], "enemy")

    meta = {
        "army_a_men": men_a,
        "army_b_men": men_b,
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

    patched = patch_menus_army_sizes(men_a, men_b)
    meta["menus_patched"] = patched
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta


def patch_menus_army_sizes(men_a, men_b):
    """Patch compiled menus.txt wave army A/B assign immediates.

    Wave option + start_game INIT blocks begin with:
      2133 2 <var_a> <men_a>  2133 2 <var_b> <men_b> ...
    Discover current values from mno_romeblade_wave_battle_entry (works after
    prior patches, not only the 300/150 defaults), then replace every matching
    assign pair and refresh the option title.
    """
    path = os.path.join(config.MB_MODULE_DIR, "menus.txt")
    if not os.path.isfile(path):
        return {"ok": False, "reason": "menus.txt missing"}
    text = open(path, "r", encoding="utf-8", errors="ignore").read()
    men_a = int(men_a)
    men_b = int(men_b)

    head = re.search(
        r"mno_romeblade_wave_battle_entry\s+0\s+(\S+)\s+(\d+)\s+"
        r"2133\s+2\s+(\d+)\s+(\d+)\s+2133\s+2\s+(\d+)\s+(\d+)",
        text,
    )
    if not head:
        return {"ok": False, "reason": "wave assign immediates not found"}
    old_title, _opcount, var_a, old_a_s, var_b, old_b_s = head.groups()
    old_a = int(old_a_s)
    old_b = int(old_b_s)
    new_title = "RomeBlade_Wave_Battle_(%d_vs_%d)" % (men_a, men_b)

    pair = re.compile(
        r"(2133\s+2\s+" + re.escape(var_a) + r"\s+)" + re.escape(str(old_a))
        + r"(\s+2133\s+2\s+" + re.escape(var_b) + r"\s+)" + re.escape(str(old_b))
    )
    text2, n_pairs = pair.subn(
        lambda mm: mm.group(1) + str(men_a) + mm.group(2) + str(men_b), text
    )
    if n_pairs < 1:
        return {
            "ok": False,
            "reason": "assign pair replace failed",
            "old_a": old_a,
            "old_b": old_b,
        }

    # Title token only on the menu option line (underscored, no spaces).
    text2 = text2.replace(old_title, new_title, 1)

    bak = path + ".rb_bak"
    if not os.path.isfile(bak):
        shutil.copyfile(path, bak)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text2)
    return {
        "ok": True,
        "men_a": men_a,
        "men_b": men_b,
        "old_a": old_a,
        "old_b": old_b,
        "pairs_patched": n_pairs,
        "title": new_title,
        "backup": bak,
    }


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
