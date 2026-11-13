#!/usr/bin/env python3
"""Bake RomeBlade module skeleton from map/settlements + battle handoff."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import generate_map
import rtw_map
import units as units_mod

ROOT = Path(__file__).resolve().parent
MODULE = ROOT / "module" / "RomeBlade"


def write_module_ini(path: Path) -> None:
    path.write_text(
        """module_name = RomeBlade
map_min_x   = -105
map_max_x   =  105
map_min_y   = -105
map_max_y   =  105
map_sea_direction = -40
map_sea_speed_x = 0.02
map_sea_speed_y = -0.02
map_river_direction = 140
map_river_speed_x = 0.01
map_river_speed_y = -0.01

map_tree_types = 17
map_snow_tree_types  = 3
map_steppe_tree_types = 5
map_desert_tree_types  = 0

compatible_with_version_min = 1000
compatible_with_version_max = 1011
works_with_version_min  = 1000
works_with_version_max  = 1011

scan_module_textures = 1
scan_module_sounds = 0
""",
        encoding="ascii",
    )


def write_build_txt(path: Path) -> None:
    path.write_text(
        """RomeBlade module build (Windows)
================================

This folder is a DATA SKELETON, not a compiled Mount & Blade module.

Blocked / required on the game PC:
1. Mount & Blade Module System for **1.011** (official / community pack matching original M&B).
2. **Python 2.7** to run the Module System `build_module.bat` / process_*.py scripts.
3. Copy or merge generated texts into a Module System project, compile to Native-format
   `*.txt` under `Modules/RomeBlade/` beside the game:
   C:\\Program Files (x86)\\Steam\\steamapps\\common\\Mount and Blade\\Modules\\RomeBlade
4. Town street geometry (`.sco`) must be created in the in-game **scene editor**.
   This toolkit does NOT generate .sco files.

What is present here:
- module.ini (1.011 band)
- map.txt (synthetic or RTW-baked)
- JSON planning files: settlements, scenes, troops, menus, parties, battle_parties, visit

Honest status: until Module System compile succeeds and .sco scenes exist, the module
is NOT loadable as a playable mod.
""",
        encoding="utf-8",
    )


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def bake(
    dest: Path,
    map_src: Path | None,
    settlements: list,
    battle: dict | None,
) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    write_module_ini(dest / "module.ini")
    write_build_txt(dest / "BUILD.txt")

    if map_src and map_src.exists():
        shutil.copy2(map_src, dest / "map.txt")
    elif (MODULE / "map.txt").exists() and dest.resolve() != MODULE.resolve():
        shutil.copy2(MODULE / "map.txt", dest / "map.txt")
    else:
        verts, faces, synth = generate_map.generate()
        generate_map.write_map_txt(dest / "map.txt", verts, faces)
        if not settlements:
            settlements = synth

    roster = units_mod.ensure_roster()
    battle = battle or {
        "kind": "battle",
        "army": [{"id": "rome_hastati", "count": 40}],
        "enemy": [{"id": "barb_warband", "count": 50}],
    }
    mapped_army = units_mod.map_army(battle.get("army", []), roster)
    mapped_enemy = units_mod.map_army(battle.get("enemy", []), roster)

    scenes = [
        {
            "id": "town_streets_placeholder",
            "type": "town",
            "sco": None,
            "status": "missing — create in M&B scene editor",
        },
        {"id": "field_battle", "type": "field", "sco": None, "status": "uses engine field"},
    ]
    troops = [
        {
            "id": c["id"],
            "name": c["name"],
            "group": c["group"],
            "stand_in": c.get("stand_in", False),
        }
        for c in roster
    ]
    menus = [
        {"id": "camp_switch", "text": "RomeBlade handoff ledger (external)"},
        {"id": "visit_settlement", "text": "Visit settlement (town scene TBD)"},
    ]
    parties = [
        {"id": f"party_{s['id']}", "settlement": s["id"], "x": s.get("x", 0), "y": s.get("y", 0)}
        for s in settlements[:40]
    ]
    battle_parties = {
        "player": mapped_army,
        "enemy": mapped_enemy,
        "kind": battle.get("kind", "battle"),
    }
    visit = {
        "settlements": settlements,
        "note": "Town visit requires .sco; field/battle usable after Module System compile.",
    }

    write_json(dest / "settlements.json", settlements)
    write_json(dest / "scenes.json", scenes)
    write_json(dest / "troops.json", troops)
    write_json(dest / "menus.json", menus)
    write_json(dest / "parties.json", parties)
    write_json(dest / "battle_parties.json", battle_parties)
    write_json(dest / "visit.json", visit)

    summary = {
        "dest": str(dest),
        "map": str(dest / "map.txt"),
        "settlements": len(settlements),
        "troops": len(troops),
        "battle_kind": battle.get("kind", "battle"),
        "blockers": [
            "Module System 1.011 + Python 2.7 compile not run",
            ".sco town scenes not generated",
        ],
    }
    write_json(dest / "summary.json", summary)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepare RomeBlade module skeleton")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--base", type=Path, help="RTW data/world/maps/base for real bake")
    ap.add_argument("--battle", type=Path, help="battle JSON")
    ap.add_argument("--out", type=Path, default=MODULE)
    ap.add_argument("--max-edge", type=int, default=140)
    args = ap.parse_args()

    units_mod.ensure_roster()
    battle = None
    if args.battle and args.battle.exists():
        battle = json.loads(args.battle.read_text(encoding="utf-8"))

    if args.self_test:
        out = ROOT / "out" / "prepare-test" / "RomeBlade"
        verts, faces, settlements = generate_map.generate(80, 60)
        map_path = ROOT / "out" / "prepare-test" / "map.txt"
        generate_map.write_map_txt(map_path, verts, faces)
        summary = bake(out, map_path, settlements, battle)
        assert (out / "module.ini").exists()
        assert (out / "map.txt").exists()
        assert (out / "troops.json").exists()
        print("self-test ok", json.dumps(summary))
        return 0

    settlements: list = []
    map_path = None
    if args.base:
        bake_out = ROOT / "out" / "from-rome"
        summary_rtw = rtw_map.convert_base(args.base, bake_out, max_edge=args.max_edge)
        map_path = Path(summary_rtw["map"])
        settlements = json.loads((bake_out / "settlements.json").read_text(encoding="utf-8"))
    else:
        # prefer existing from-rome, else synthetic
        fr = ROOT / "out" / "from-rome"
        if (fr / "map.txt").exists():
            map_path = fr / "map.txt"
            sp = fr / "settlements.json"
            if sp.exists():
                settlements = json.loads(sp.read_text(encoding="utf-8"))
        else:
            verts, faces, settlements = generate_map.generate()
            map_path = ROOT / "out" / "map.txt"
            generate_map.write_map_txt(map_path, verts, faces)
            (ROOT / "out" / "settlements.json").write_text(
                json.dumps(settlements, indent=2), encoding="utf-8"
            )

    summary = bake(args.out, map_path, settlements, battle)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
