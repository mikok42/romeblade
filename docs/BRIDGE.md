# RomeBlade bridge (RTW ↔ M&B)

## Goal

On the RTW **pre-battle scroll**, click **Begin Battle** → fight in **Mount & Blade** (`RomeBladeRTS`) → RTW continues **without** its own tactical battle, with losses applied via **quicksave + Ctrl+L** (no Load Game menu).

## How to run (everyday)

Double-click or run:

```bat
start_romeblade.bat
```

That starts the bridge minimized (`out\bridge_run.log`) and launches `RomeTW.exe` **without** `-ne` (your normal fullscreen). You load the campaign and bring up a land battle yourself. The bridge only waits for the scroll.

Close Rome when done — the bridge unhooks and exits. No leftover hook/process by design.

Manual (bridge only, you start Rome yourself):

```bat
cd /d c:\Users\Mikok\Documents\RomeAndBlade
python -m tools.romeblade_bridge
```

Optional: `--simulate-result attacker` · `--no-watch-rtw` (keep bridge after Rome quits).

## Trigger (chosen)

| Step | Method |
|------|--------|
| Know a battle scroll is up | Match on-screen pixels to `data\ui\*\eventpics\prebattle_*.tga` (GDI desktop grab) |
| Know you pressed Begin Battle | Low-level mouse hook; click in the guessed button hitbox is **swallowed** |
| Know the two armies | Newest `.sav` / pending-battle manifest (M1 heuristic until adjacency) |
| Skip RTW fight | Click never reaches Begin Battle; fallback Escape |
| Apply outcome | `romeblade_result.sav` → backup any `quicksave.sav` → overwrite `quicksave.sav` → **Ctrl+L** |
| Scroll dismiss fallback | Console `auto_win` + guessed Auto Resolve click (if Ctrl+L does not clear the panel) |

**Removed:** navigating RTW Load Game menus (unreliable on this desk).

## Quicksave return (offline evidence)

| Claim | Status |
|-------|--------|
| `keys.dat` has `save_stratmap` / `load_stratmap` under `strat_ui` | **Confirmed** in this install |
| FAQ / manual extract: Ctrl+S quick save, Ctrl+L quick load | **Confirmed** in community FAQ text |
| File name `quicksave.sav` in `saves\` | **Confirmed** by hotseat guides; **no** string in `RomeTW.exe` on this disk |
| Overwrite `quicksave.sav` then Ctrl+L mid-campaign / on scroll | **UNVERIFIED in-game** |
| SendInput Ctrl+L accepted like a real key | **UNVERIFIED in-game** |

If a player `quicksave.sav` already exists, the bridge copies it to `rb_qs_backup_<stamp>.sav` **before** replacing. Never deletes that backup. Never touches `RomaAroma` / `Autosave` / `niunia`.

## Fullscreen (scroll detect + hook)

| Piece | Expectation | Uncertainty |
|-------|-------------|-------------|
| `WH_MOUSE_LL` hook | Usually works over exclusive fullscreen | Game may use raw input; swallow race still possible |
| Begin Battle hitbox | Derived from matched template + screen metrics | Tuned for 1920×1080; other resolutions need a real shot |
| Scroll detect (`BitBlt` desktop) | Works for windowed / borderless | **Exclusive fullscreen DirectX often captures black** — UNVERIFIED on this machine in fullscreen |
| Starter launches without `-ne` | Matches everyday play | If detect stays dark, try one windowed session only via CLI `-ne` (not prefs) |

## E1 save proof

Tool: `tools\rtw_save_units.py`

- **current (+30) alone does not drive the card**; **full/display (+34) does** (`proba_disp41` → UI 41).
- Player faction: **romans_brutii**.
- End-turn persistence of +34 after save/reload: waiting on manual `proba_endturn41` (no disk polling).

## Manual leftover

1. You start via `start_romeblade.bat` (or bridge + Rome yourself).
2. You load the campaign and open the fight scroll.
3. One click on **Begin Battle** (hook must be armed — watch `out\bridge_run.log`).
4. If Auto Resolve fallback misses, click it once after `auto_win`.
5. Confirm once that Ctrl+L after a bridged fight actually loads the patched quicksave.

## Related

- Local progress: `docs/romeblade-local-progress.md` (also in project store)
- Wave battle play: `docs/Z1-PLAY.md`
