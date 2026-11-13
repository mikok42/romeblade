#!/usr/bin/env python3
"""JSON ledger switcher: RTW campaign turn ↔ M&B 1.011 battle/town/field."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import units as units_mod

ROOT = Path(__file__).resolve().parent
HANDOFF = ROOT / "handoff"
STATE = HANDOFF / "state.json"
RESULT_SAMPLE = HANDOFF / "result.sample.json"
BATTLE_SAMPLE = ROOT / "out" / "battle.sample.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def default_state() -> dict:
    return {
        "version": 1,
        "mode": "rome",  # rome | blade
        "updated": _now(),
        "campaign": {
            "turn": 1,
            "faction": "romans_julii",
            "notes": "Manual army export from RTW; no save write-back.",
        },
        "army": [
            {"id": "rome_hastati", "count": 80},
            {"id": "rome_principes", "count": 60},
            {"id": "rome_velites", "count": 40},
            {"id": "rome_equites", "count": 20},
            {"id": "rome_roman_archers", "count": 30},
        ],
        "enemy": [
            {"id": "barb_warband", "count": 100},
            {"id": "barb_skirmisher", "count": 40},
            {"id": "barb_cavalry", "count": 25},
        ],
        "context": {
            "kind": "field",  # field | battle | town
            "settlement": None,
            "terrain": "plain",
        },
        "last_result": None,
        "mapped_army": [],
        "mapped_enemy": [],
    }


def load_state() -> dict:
    HANDOFF.mkdir(parents=True, exist_ok=True)
    if not STATE.exists():
        st = default_state()
        save_state(st)
        return st
    return json.loads(STATE.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    HANDOFF.mkdir(parents=True, exist_ok=True)
    state["updated"] = _now()
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def ensure_samples() -> None:
    HANDOFF.mkdir(parents=True, exist_ok=True)
    (ROOT / "out").mkdir(parents=True, exist_ok=True)
    if not RESULT_SAMPLE.exists():
        RESULT_SAMPLE.write_text(
            json.dumps(
                {
                    "winner": "player",
                    "losses": {
                        "rome_hastati": 12,
                        "rome_principes": 5,
                        "rome_velites": 8,
                        "rome_equites": 2,
                        "rome_roman_archers": 3,
                    },
                    "enemy_losses": {
                        "barb_warband": 55,
                        "barb_skirmisher": 20,
                        "barb_cavalry": 10,
                    },
                    "notes": "Paste real M&B battle losses here, then: switch.py to-rome --result handoff/result.sample.json",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    if not BATTLE_SAMPLE.exists():
        st = default_state()
        battle = {
            "kind": "battle",
            "player_faction": st["campaign"]["faction"],
            "army": st["army"],
            "enemy": st["enemy"],
            "terrain": "plain",
        }
        BATTLE_SAMPLE.write_text(json.dumps(battle, indent=2), encoding="utf-8")


def cmd_status(state: dict) -> None:
    print(f"mode={state['mode']} turn={state['campaign']['turn']} updated={state['updated']}")
    print(f"army stacks={len(state.get('army', []))} enemy stacks={len(state.get('enemy', []))}")
    if state.get("last_result"):
        print(f"last_result winner={state['last_result'].get('winner')}")


def cmd_to_blade(state: dict, kind: str) -> dict:
    roster = units_mod.ensure_roster()
    state["mode"] = "blade"
    state["context"]["kind"] = kind
    state["mapped_army"] = units_mod.map_army(state.get("army", []), roster)
    state["mapped_enemy"] = units_mod.map_army(state.get("enemy", []), roster)
    out = {
        "handoff": "to-blade",
        "kind": kind,
        "campaign": state["campaign"],
        "mapped_army": state["mapped_army"],
        "mapped_enemy": state["mapped_enemy"],
        "module_hint": "module/RomeBlade — compile with Module System 1.011 + Python 2.7 (see BUILD.txt)",
        "manual": [
            "Export army composition from RTW by hand into handoff/state.json",
            "Fight in Mount & Blade 1.011 (battle / town / field)",
            "Write losses JSON, then run: python switch.py to-rome --result <file>",
            "Apply remaining counts back into RTW manually (no save write-back)",
        ],
    }
    blade_path = HANDOFF / "to_blade.json"
    blade_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    save_state(state)
    print(f"wrote {blade_path} kind={kind}")
    return state


def apply_losses(stacks: list[dict], losses: dict) -> list[dict]:
    out = []
    for s in stacks:
        uid = s["id"]
        lost = int(losses.get(uid, 0))
        left = max(0, int(s.get("count", 0)) - lost)
        if left > 0:
            out.append({"id": uid, "count": left})
    return out


def cmd_to_rome(state: dict, result_path: Path) -> dict:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    state["army"] = apply_losses(state.get("army", []), result.get("losses", {}))
    state["enemy"] = apply_losses(state.get("enemy", []), result.get("enemy_losses", {}))
    state["mode"] = "rome"
    state["campaign"]["turn"] = int(state["campaign"].get("turn", 1)) + 1
    state["last_result"] = result
    state["mapped_army"] = []
    state["mapped_enemy"] = []
    save_state(state)
    print(
        f"applied result winner={result.get('winner')} -> mode=rome turn={state['campaign']['turn']}"
    )
    print("Apply remaining army counts to RTW manually (toolkit does not write RTW saves).")
    return state


def main() -> int:
    ap = argparse.ArgumentParser(description="RomeBlade ledger switcher")
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("status")
    p_blade = sub.add_parser("to-blade")
    p_blade.add_argument("--kind", choices=["battle", "town", "field"], default="battle")
    p_rome = sub.add_parser("to-rome")
    p_rome.add_argument("--result", type=Path, required=True)
    args = ap.parse_args()

    ensure_samples()
    units_mod.ensure_roster()
    state = load_state()

    if args.self_test:
        state = default_state()
        save_state(state)
        state = cmd_to_blade(state, "battle")
        assert state["mode"] == "blade"
        assert state["mapped_army"]
        state = cmd_to_rome(state, RESULT_SAMPLE)
        assert state["mode"] == "rome"
        cmd_status(state)
        print("self-test ok")
        return 0

    if args.cmd == "status" or args.cmd is None:
        cmd_status(state)
        return 0
    if args.cmd == "to-blade":
        cmd_to_blade(state, args.kind)
        return 0
    if args.cmd == "to-rome":
        cmd_to_rome(state, args.result)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
