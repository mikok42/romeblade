# RomeBlade — local progress

Updated: 2026-11-13  
`start_romeblade.bat` = bridge + **Arm panel** + Rome **`-ne`**.

## M&B landed on main menu (after first swallow success)

`last_module` was already RomeBladeRTS; `start_mb` only set registry + Popen. Fix: Wave Battle ops in `start_game_1` / `start_game_3` INIT + launcher auto-clicks New Game; `prepare_mb` patches army sizes on all three assign pairs. Rebuild done into Modules/RomeBladeRTS.

## No UI clicking (user veto)

Auto-click launcher/New Game abandoned — unreliable and a bad trip. Disk check: no SkinMagic off-switch, no CLI mission entry. Honest path: bridge only `last_module` + start exe; user **Graj** → **Nowa gra**; module INIT already enters Wave Battle.
