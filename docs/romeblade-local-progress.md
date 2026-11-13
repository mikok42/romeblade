# RomeBlade — local progress

Updated: 2026-11-13  
`start_romeblade.bat` = bridge + **Arm panel** + Rome **`-ne`**.

## M&B landed on main menu (after first swallow success)

`last_module` was already RomeBladeRTS; `start_mb` only set registry + Popen. Fix: Wave Battle ops in `start_game_1` / `start_game_3` INIT + launcher auto-clicks New Game; `prepare_mb` patches army sizes on all three assign pairs. Rebuild done into Modules/RomeBladeRTS.

## Launcher stuck (after c1f2e46)

Auto-clicks hit the SkinMagic **launcher** (PL: Graj w Mount&Blade), not the in-game New Game. Fix: BM_CLICK Play → wait for game window → then New Game. See `docs/BRIDGE.md`.
