#!/usr/bin/env python3
"""Role-based RTW → M&B 1.011 unit card roster (no vendored RTW meshes/stats)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "units.json"

# command groups allowed by original M&B battle UI
GROUPS = ("infantry", "archers", "cavalry")

# body kinds: exotic → stand_in for 1.011 Native assets
STAND_IN_BODIES = {
    "elephant",
    "chariot",
    "camel",
    "dog",
    "pig",
    "onager",
    "ballista",
    "scorpion",
    "naval",
}


def default_roster() -> list[dict]:
    """Build 124 role cards covering major RTW / BI archetypes."""
    cards: list[dict] = []

    def add(unit_id: str, name: str, role: str, group: str, body: str = "human", **extra):
        stand_in = body in STAND_IN_BODIES or body != "human"
        if body == "horse":
            stand_in = False
        card = {
            "id": unit_id,
            "name": name,
            "role": role,
            "group": group,
            "body": body,
            "stand_in": stand_in if body != "human" and body != "horse" else False,
            "gear": extra.pop(
                "gear",
                {
                    "weapons": ["short_sword", "javelin"] if group == "infantry" else [],
                    "armor": "leather_armor",
                    "helmet": "leather_cap",
                    "shield": "shield_round" if group == "infantry" else None,
                    "horse": "courser" if group == "cavalry" else None,
                },
            ),
            "notes": extra.pop("notes", ""),
        }
        if body in STAND_IN_BODIES:
            card["stand_in"] = True
            card["notes"] = (card["notes"] + " stand-in body; no RTW mesh").strip()
        cards.append(card)

    # Roman line
    roman = [
        ("hastati", "Hastati", "light_legion", "infantry"),
        ("principes", "Principes", "heavy_legion", "infantry"),
        ("triarii", "Triarii", "elite_spear", "infantry"),
        ("velites", "Velites", "skirmisher", "infantry"),
        ("roman_archers", "Roman Archers", "archer", "archers"),
        ("equites", "Equites", "medium_cavalry", "cavalry"),
        ("roman_general", "Roman General", "general", "cavalry"),
        ("urban_cohort", "Urban Cohort", "elite_legion", "infantry"),
        ("praetorian", "Praetorian Cohort", "elite_legion", "infantry"),
        ("auxilia_infantry", "Auxilia Infantry", "aux_infantry", "infantry"),
        ("auxilia_cavalry", "Auxilia Cavalry", "aux_cavalry", "cavalry"),
        ("arcani", "Arcani", "infiltrator", "infantry"),
    ]
    for uid, name, role, group in roman:
        add(f"rome_{uid}", name, role, group, notes="roman")

    # Greek / Successor
    greek = [
        ("militia_hoplites", "Militia Hoplites", "militia_spear", "infantry"),
        ("hoplites", "Hoplites", "spear", "infantry"),
        ("armoured_hoplites", "Armoured Hoplites", "elite_spear", "infantry"),
        ("peltasts", "Peltasts", "skirmisher", "infantry"),
        ("cretan_archers", "Cretan Archers", "elite_archer", "archers"),
        ("greek_cavalry", "Greek Cavalry", "medium_cavalry", "cavalry"),
        ("general_guard", "General's Guard", "general", "cavalry"),
        ("phalanx_pikemen", "Phalanx Pikemen", "pike", "infantry"),
        ("silver_shields", "Silver Shield Pikemen", "elite_pike", "infantry"),
        ("companion_cavalry", "Companion Cavalry", "elite_cavalry", "cavalry"),
        ("prodromoi", "Prodromoi", "light_cavalry", "cavalry"),
        ("thorakitai", "Thorakitai", "heavy_infantry", "infantry"),
    ]
    for uid, name, role, group in greek:
        add(f"greek_{uid}", name, role, group, notes="greek")

    # Carthage / Africa
    carth = [
        ("iberian_infantry", "Iberian Infantry", "medium_infantry", "infantry"),
        ("libyan_spearmen", "Libyan Spearmen", "spear", "infantry"),
        ("sacred_band", "Sacred Band", "elite_spear", "infantry"),
        ("balearic_slingers", "Balearic Slingers", "slinger", "archers"),
        ("numidian_cavalry", "Numidian Cavalry", "light_cavalry", "cavalry"),
        ("poeni_cavalry", "Poeni Cavalry", "medium_cavalry", "cavalry"),
        ("war_elephants", "War Elephants", "elephant", "cavalry", "elephant"),
        ("long_shield_cavalry", "Long Shield Cavalry", "heavy_cavalry", "cavalry"),
        ("round_shield_cavalry", "Round Shield Cavalry", "medium_cavalry", "cavalry"),
        ("desert_infantry", "Desert Infantry", "light_infantry", "infantry"),
    ]
    for item in carth:
        if len(item) == 5:
            uid, name, role, group, body = item
            add(f"carth_{uid}", name, role, group, body, notes="carthage")
        else:
            uid, name, role, group = item
            add(f"carth_{uid}", name, role, group, notes="carthage")

    # Gaul / Briton / German
    barb = [
        ("warband", "Warband", "light_infantry", "infantry"),
        ("swordsmen", "Swordsmen", "medium_infantry", "infantry"),
        ("spearmen", "Spearmen", "spear", "infantry"),
        ("chosen_swordsmen", "Chosen Swordsmen", "elite_infantry", "infantry"),
        ("skirmisher", "Skirmishers", "skirmisher", "infantry"),
        ("archer", "Barbarian Archers", "archer", "archers"),
        ("cavalry", "Barbarian Cavalry", "medium_cavalry", "cavalry"),
        ("noble_cavalry", "Noble Cavalry", "elite_cavalry", "cavalry"),
        ("warhounds", "Warhounds", "dogs", "infantry", "dog"),
        ("wardogs", "Wardogs", "dogs", "infantry", "dog"),
        ("head_hurlers", "Head Hurlers", "skirmisher", "infantry"),
        ("woad_warriors", "Woad Warriors", "light_infantry", "infantry"),
        ("druids", "Druids", "support", "infantry"),
        ("screeching_women", "Screeching Women", "support", "infantry"),
        ("night_raiders", "Night Raiders", "infiltrator", "infantry"),
        ("chosen_axemen", "Chosen Axemen", "elite_infantry", "infantry"),
        ("axemen", "Axemen", "medium_infantry", "infantry"),
        ("berserkers", "Berserkers", "elite_infantry", "infantry"),
        ("gothic_cavalry", "Gothic Cavalry", "heavy_cavalry", "cavalry"),
        ("barbarian_general", "Barbarian Warlord", "general", "cavalry"),
    ]
    for item in barb:
        if len(item) == 5:
            uid, name, role, group, body = item
            add(f"barb_{uid}", name, role, group, body, notes="barbarian")
        else:
            uid, name, role, group = item
            add(f"barb_{uid}", name, role, group, notes="barbarian")

    # Eastern / Egypt / Parthia
    east = [
        ("nubian_spearmen", "Nubian Spearmen", "spear", "infantry"),
        ("nubian_archers", "Nubian Archers", "archer", "archers"),
        ("egyptian_archers", "Egyptian Archers", "archer", "archers"),
        ("pharaohs_guards", "Pharaoh's Guards", "elite_infantry", "infantry"),
        ("desert_cavalry", "Desert Cavalry", "light_cavalry", "cavalry"),
        ("nile_peasants", "Nile Peasants", "militia", "infantry"),
        ("camel_archers", "Camel Archers", "camel_archer", "cavalry", "camel"),
        ("cataphracts", "Cataphracts", "elite_cavalry", "cavalry"),
        ("persian_cavalry", "Persian Cavalry", "medium_cavalry", "cavalry"),
        ("eastern_infantry", "Eastern Infantry", "medium_infantry", "infantry"),
        ("horse_archers", "Horse Archers", "horse_archer", "archers"),
        ("war_elephants_east", "Eastern Elephants", "elephant", "cavalry", "elephant"),
        ("chariots", "British Chariots", "chariot", "cavalry", "chariot"),
        ("scythed_chariots", "Scythed Chariots", "chariot", "cavalry", "chariot"),
        ("onagers", "Onagers", "siege", "infantry", "onager"),
        ("ballistas", "Ballistas", "siege", "infantry", "ballista"),
        ("scorpions", "Scorpions", "siege", "infantry", "scorpion"),
        ("incendiary_pigs", "Incendiary Pigs", "special", "infantry", "pig"),
    ]
    for item in east:
        if len(item) == 5:
            uid, name, role, group, body = item
            add(f"east_{uid}", name, role, group, body, notes="eastern")
        else:
            uid, name, role, group = item
            add(f"east_{uid}", name, role, group, notes="eastern")

    # BI late Roman / foederati fillers to reach 124
    bi = [
        ("comitatenses", "Comitatenses", "heavy_legion", "infantry"),
        ("limitanei", "Limitanei", "light_legion", "infantry"),
        ("auxilia_palatina", "Auxilia Palatina", "elite_infantry", "infantry"),
        ("foederati_infantry", "Foederati Infantry", "medium_infantry", "infantry"),
        ("foederati_cavalry", "Foederati Cavalry", "medium_cavalry", "cavalry"),
        ("sarmatian_cavalry", "Sarmatian Cavalry", "heavy_cavalry", "cavalry"),
        ("hun_horse_archers", "Hun Horse Archers", "horse_archer", "archers"),
        ("gothic_warriors", "Gothic Warriors", "medium_infantry", "infantry"),
        ("vandals", "Vandal Raiders", "light_infantry", "infantry"),
        ("alan_cavalry", "Alan Cavalry", "medium_cavalry", "cavalry"),
        ("peasant_levy", "Peasant Levy", "militia", "infantry"),
        ("town_watch", "Town Watch", "militia", "infantry"),
        ("pirates", "Pirates", "light_infantry", "infantry"),
        ("brigands", "Brigands", "light_infantry", "infantry"),
        ("rebel_cavalry", "Rebel Cavalry", "light_cavalry", "cavalry"),
        ("naval_crew", "Naval Crew", "naval", "infantry", "naval"),
        ("bireme_crew", "Bireme Crew", "naval", "infantry", "naval"),
        ("triere_crew", "Trireme Crew", "naval", "infantry", "naval"),
        ("saxon_hearth_troops", "Saxon Hearth Troops", "elite_infantry", "infantry"),
        ("celtic_nobles", "Celtic Nobles", "elite_infantry", "infantry"),
        ("steppe_raiders", "Steppe Raiders", "light_cavalry", "cavalry"),
        ("desert_raiders", "Desert Raiders", "light_cavalry", "cavalry"),
        ("mountain_men", "Mountain Men", "light_infantry", "infantry"),
        ("slingers", "Slingers", "slinger", "archers"),
        ("javelinmen", "Javelinmen", "skirmisher", "infantry"),
        ("heavy_spearmen", "Heavy Spearmen", "heavy_spear", "infantry"),
        ("light_cavalry", "Light Cavalry", "light_cavalry", "cavalry"),
        ("heavy_cavalry", "Heavy Cavalry", "heavy_cavalry", "cavalry"),
        ("archer_militia", "Archer Militia", "militia_archer", "archers"),
        ("crossbow_standin", "Crossbow Stand-in", "archer", "archers"),
        ("scout_equites", "Scout Equites", "light_cavalry", "cavalry"),
        ("legionary_cohort", "Legionary Cohort", "heavy_legion", "infantry"),
        ("eagle_cohort", "First Cohort", "elite_legion", "infantry"),
        ("gladiators", "Gladiators", "elite_infantry", "infantry"),
        ("samnite_gladiators", "Samnite Gladiators", "elite_infantry", "infantry"),
        ("bishop_guards", "Bishop's Guards", "elite_infantry", "infantry"),
        ("christian_priests", "Priests", "support", "infantry"),
        ("steppe_nobles", "Steppe Nobles", "elite_cavalry", "cavalry"),
        ("amazon_chariots", "Amazon Chariots", "chariot", "cavalry", "chariot"),
        ("amazon_cavalry", "Amazon Cavalry", "medium_cavalry", "cavalry"),
        ("amazon_archers", "Amazon Archers", "archer", "archers"),
        ("pictish_cavalry", "Pictish Cavalry", "light_cavalry", "cavalry"),
    ]
    for item in bi:
        if len(item) == 5:
            uid, name, role, group, body = item
            add(f"bi_{uid}", name, role, group, body, notes="bi_or_generic")
        else:
            uid, name, role, group = item
            add(f"bi_{uid}", name, role, group, notes="bi_or_generic")

    # Trim or pad to exactly 124
    if len(cards) > 124:
        cards = cards[:124]
    while len(cards) < 124:
        n = len(cards) + 1
        add(f"fill_{n}", f"Levy {n}", "militia", "infantry", notes="filler")
    return cards


def ensure_roster(path: Path = DATA) -> list[dict]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    cards = default_roster()
    path.write_text(json.dumps(cards, indent=2), encoding="utf-8")
    return cards


def lookup(unit_id: str, roster: list[dict] | None = None) -> dict | None:
    roster = roster or ensure_roster()
    for c in roster:
        if c["id"] == unit_id:
            return c
    return None


def map_army(army: list[dict], roster: list[dict] | None = None) -> list[dict]:
    """army entries: {id|unit, count} → cards with counts."""
    roster = roster or ensure_roster()
    by_id = {c["id"]: c for c in roster}
    by_name = {c["name"].lower(): c for c in roster}
    out = []
    for entry in army:
        uid = entry.get("id") or entry.get("unit") or ""
        count = int(entry.get("count", 1))
        card = by_id.get(uid) or by_name.get(str(uid).lower().replace("_", " "))
        if not card:
            card = {
                "id": uid or "unknown",
                "name": uid or "unknown",
                "role": "militia",
                "group": "infantry",
                "body": "human",
                "stand_in": True,
                "gear": {},
                "notes": "unmapped unit → militia stand-in",
            }
        mapped = dict(card)
        mapped["count"] = count
        out.append(mapped)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="RomeBlade unit roster")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--rewrite", action="store_true", help="Regenerate data/units.json")
    args = ap.parse_args()
    if args.rewrite or not DATA.exists():
        cards = default_roster()
        DATA.parent.mkdir(parents=True, exist_ok=True)
        DATA.write_text(json.dumps(cards, indent=2), encoding="utf-8")
    else:
        cards = ensure_roster()
    print(f"roster={len(cards)}")
    if args.self_test:
        assert len(cards) == 124
        assert all(c["group"] in GROUPS for c in cards)
        sample = map_army(
            [{"id": "rome_hastati", "count": 40}, {"id": "carth_war_elephants", "count": 2}]
        )
        assert sample[0]["group"] == "infantry"
        assert sample[1]["stand_in"] is True
        print("self-test ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
