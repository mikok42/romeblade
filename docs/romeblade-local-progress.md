# RomeBlade — local progress

Updated: 2026-11-13  
`start_romeblade.bat` = bridge + **Arm panel** + Rome **`-ne`**.

## M&B landed on main menu (after first swallow success)

`last_module` was already RomeBladeRTS; `start_mb` only set registry + Popen. Fix: Wave Battle ops in `start_game_1` / `start_game_3` INIT + launcher auto-clicks New Game; `prepare_mb` patches army sizes on all three assign pairs. Rebuild done into Modules/RomeBladeRTS.

## Launcher stuck (after c1f2e46 / f71b6e5)

Auto-clicks hit the SkinMagic **launcher**, then f71b6e5 matched title **RomeAndBlade** (Cursor) via needle `Blade` and skipped Play (`mb_launcher_skip` + `mb_game_window title=RomeAndBlade`). 1.011 has **no** CLI for mission/skip-launcher. Fix: windows only from `mount&blade.exe` PID + BM_CLICK/click/Enter on Graj.
