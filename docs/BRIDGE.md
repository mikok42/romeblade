# RomeBlade bridge (RTW ↔ M&B)

## Goal

On the RTW **pre-battle scroll**, click **Begin Battle** → fight in **Mount & Blade** (`RomeBladeRTS`) → RTW continues **without** its own tactical battle, with the bridge’s result applied (`auto_win` + autoresolve, then a result save when per-unit patches exist).

## How to run

```bat
cd /d c:\Users\Mikok\Documents\RomeAndBlade
python -m tools.romeblade_bridge
```

Optional: `--simulate-result attacker` to test the return path without an M&B log line.

Leave the bridge running, start RTW, open a land battle scroll, click **Begin Battle**.

## Trigger (chosen)

| Step | Method |
|------|--------|
| Know a battle scroll is up | Match on-screen pixels to `data\ui\*\eventpics\prebattle_*.tga` |
| Know you pressed Begin Battle | Low-level mouse hook; click in the guessed button hitbox is **swallowed** so RTW should not enter deployment |
| Know the two armies | Newest `.sav` in `saves\`; two largest unit-clusters (M1 heuristic — not yet “these two on the scroll”) |
| Skip RTW fight | Click never reaches Begin Battle; fallback Escape if RTW still reacts |
| Apply outcome | Console `auto_win attacker\|defender`, then a guessed Auto Resolve click |
| Exact losses | Planned: new file `romeblade_result.sav` only (never overwrite `RomaAroma` / `Autosave` / `niunia`) |

Alternatives considered: process memory RE (no ready 1.5 tool), watching `battle\custom\__temp` (appears **after** Begin Battle — too late to divert cleanly), campaign script `PreBattlePanelOpen` (needs editing stock campaign data).

## E1 save proof

Tool: `tools\rtw_save_units.py`

- **current (+30) alone does not drive the card** (most_proba/proba2 = 30 in file, UI 80).
- **full (+34) does** (`proba_full30` current=full=30 → UI 30).
- Player faction in `RomaAroma`: **romans_julii**. No natural Julii depleted units (all depleted hastati are Brutii / FOW).
- Next check: load **`proba_julii30`** — Julii ~1432-men field army, one Roman Hastati, expect **30** with full still 80 (slots 30–79 zeroed). Also waiting on **`proba3`** (end-turn from proba_full30).

```bat
python tools\rtw_save_units.py list "<saves>\RomaAroma.sav" --type "roman hastati"
python tools\rtw_save_units.py diff "<saves>\RomaAroma.sav" "<saves>\most_proba.sav"
```

## Offline loop pieces (no RTW / no mouse hook)

| Piece | Status |
|-------|--------|
| Army list (generals + captain_card faction) | `battle_select.list_battle_armies` — generals no longer dropped |
| Battle pair from save alone | **Blocked** without map adjacency (not decoded). Needs `out/bridge_pending_battle.json` with `index_a/b` or composition `fingerprint_a/b` |
| Bake sizes into RomeBladeRTS wave menu | `prepare_mb` patches `menus.txt` + writes `bridge_battle.json` |
| M&B result line | `script_romeblade_wave_emit_result` → `ROME BLADE RESULT\|…` in rgl_log (module rebuilt) |
| Result save | `write_result` → new `romeblade_result.sav` (current patches only — display recipe still open) |

## Manual leftover (until automation is solid)

1. Bridge must be running before the scroll.
2. Army pairing may be wrong until M1 ownership/position is done — check the console dump.
3. Wave sizes are patched into `menus.txt` by `prepare_mb`; troop-type plan is in `bridge_mb_meta.json` (spawn wiring still thin).
4. If Auto Resolve click misses, click it once yourself after `auto_win`.
5. Loading `romeblade_result` is not fully hands-free yet.

## Related

- Plan §12: store `docs/plan-rozwoju-gry.md`
- Wave battle play: `docs/Z1-PLAY.md`
