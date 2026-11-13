# RomeBlade — local progress

Updated: 2026-11-13  
`start_romeblade.bat` = bridge + **Arm panel** + Rome **`-ne`**.

## M&B landed on main menu (after first swallow success)

`last_module` was already RomeBladeRTS; `start_mb` only set registry + Popen. Fix: Wave Battle ops in `start_game_1` / `start_game_3` INIT + launcher auto-clicks New Game; `prepare_mb` patches army sizes on all three assign pairs. Rebuild done into Modules/RomeBladeRTS.

## No UI clicking (user veto)

Auto-click launcher/New Game abandoned. Honest path: bridge `last_module` + exe; user **Graj** → **Nowa gra**; Wave INIT.

## RTW composition + no Arm panel

`prepare_mb` patches army totals + inf/mis/cav role mix into menus; spawn weighted by those globals. Stand-ins still Swadian/Vaegir (not 1:1 RTW models). Default starter: Rome `-ne` + GDI arm, **no UZBRÓJ panel**.
