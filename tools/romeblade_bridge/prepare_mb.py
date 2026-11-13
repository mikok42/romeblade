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
    """Patch the compiled menus.txt wave entry immediates for army A/B.

    The wave menu assigns rb_wave_army_a/b then copies into globals. After build,
    those show up as literal integers near the wave entry. We replace the first
    pair of 300/150 style defaults carefully.
    """
    path = os.path.join(config.MB_MODULE_DIR, "menus.txt")
    if not os.path.isfile(path):
        return {"ok": False, "reason": "menus.txt missing"}
    text = open(path, "r", encoding="utf-8", errors="ignore").read()
    # Anchor on the wave menu token exported as mno_romeblade_wave_battle_entry
    anchor = "mno_romeblade_wave_battle_entry"
    i = text.find(anchor)
    if i < 0:
        return {"ok": False, "reason": "wave menu entry not found"}
    # Within the next ~500 chars, replace first standalone 300 then 150
    # (defaults from module_constants). Use word-ish boundaries in the digit stream.
    window = text[i : i + 800]

    def repl_first(chunk, old, new):
        # opcodes are space-separated ints; replace first exact token
        parts = chunk.split(" ")
        for idx, p in enumerate(parts):
            if p == str(old):
                parts[idx] = str(new)
                return " ".join(parts), True
        return chunk, False

    w2, ok_a = repl_first(window, 300, int(men_a))
    w3, ok_b = repl_first(w2, 150, int(men_b))
    if not (ok_a and ok_b):
        # try whatever constants currently are by reading module_constants defaults pattern
        return {
            "ok": False,
            "reason": "could not find 300/150 tokens near wave entry",
            "ok_a": ok_a,
            "ok_b": ok_b,
        }
    text2 = text[:i] + w3 + text[i + 800 :]
    # backup once
    bak = path + ".rb_bak"
    if not os.path.isfile(bak):
        shutil.copyfile(path, bak)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text2)
    return {"ok": True, "men_a": men_a, "men_b": men_b, "backup": bak}


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
