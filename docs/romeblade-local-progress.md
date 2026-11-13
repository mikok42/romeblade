# RomeBlade — local progress (DESKTOP-QO223A2)

Updated: 2026-11-13 (worker `bc-5b5e7c67-2142-57a4-a5b2-b8c7c00665d1`)  
Folder: `c:\Users\Mikok\Documents\RomeAndBlade`  
Repo: https://github.com/mikok42/romeblade  

## Games

- RTW Gold 1.5.1 / BI 1.6.1 — `...\Rome Total War Gold`
- M&B **1.011** — `...\Mount and Blade`

## Everyday start (no menu automation)

```bat
start_romeblade.bat
```

Starts the bridge in the background (`out\bridge_run.log`) and Rome **normally** (no `-ne`, fullscreen as you play). You load the campaign and open the battle; the bridge waits for the pre-battle scroll. Closing Rome clears the hook and exits the bridge.

## Return path: quicksave (not Load Game menu)

Menu clicking was abandoned as unreliable. Offline evidence:

- `preferences\keys.dat`: `save_stratmap` / `load_stratmap` on `strat_ui`
- FAQ: Ctrl+S / Ctrl+L
- Hotseat docs: file `quicksave.sav`

Bridge writes `romeblade_result.sav`, copies any existing `quicksave.sav` → `rb_qs_backup_<stamp>.sav`, replaces `quicksave.sav`, sends Ctrl+L. **In-game effect still UNVERIFIED.**

## Fullscreen detect / hook

- Hook (`WH_MOUSE_LL`): expected to work; swallow race possible.
- Scroll match: GDI desktop grab — **exclusive fullscreen may capture black** (UNVERIFIED on desk).
- Hitbox: guessed from template + screen size.

## E1 — modified save

- Display field **+34** drives the unit card (`proba_disp41` → UI 41).
- End-turn persistence: waiting on manual `proba_endturn41` (agent does **not** poll disk).

## Protected

Never overwrite/delete `RomaAroma.sav` / `Autosave.sav` / `niunia.sav`.  
Existing `quicksave.sav` is backed up before replace, never discarded.

## Still needs a desk try

1. `proba_disp41` → end turn → `proba_endturn41` → reload (display still 41?).
2. `start_romeblade.bat` → real scroll → Begin Battle swallowed → M&B → quicksave Ctrl+L.
3. Scroll detect in true fullscreen (if black, one windowed `-ne` check only on CLI).
4. Retrain after depleted +34.
