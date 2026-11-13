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
Copy already in the saves folder: **`most_proba`** (from `RomaAroma`, all 84 `roman hastati` current counts set to **30**). Same length; only the current-count low bytes change. No file-size field found in the save.

```bat
python tools\rtw_save_units.py list "<saves>\RomaAroma.sav" --type "roman hastati"
python tools\rtw_save_units.py diff "<saves>\RomaAroma.sav" "<saves>\most_proba.sav"
```

## Manual leftover (until automation is solid)

1. Bridge must be running before the scroll.
2. Army pairing may be wrong until M1 ownership/position is done — check the console dump.
3. M&B still opens the normal module entry (wave sizes from the save not fully wired into the mission yet).
4. If Auto Resolve click misses, click it once yourself after `auto_win`.
5. Loading `romeblade_result` is not fully hands-free yet.

## Related

- Plan §12: store `docs/plan-rozwoju-gry.md`
- Wave battle play: `docs/Z1-PLAY.md`
