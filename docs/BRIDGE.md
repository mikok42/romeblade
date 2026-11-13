# RomeBlade bridge (RTW ↔ M&B)

## Jeden executable?

**Jeden silnik łączący RTW+M&B: nie.** To dwa osobne exe.  
**Jeden most bez zewnętrznego UI: tak** — `start_romeblade.bat` odpala bridge (w tle) + Rome `-ne`; bez okna UZBRÓJ.

## M&B 1.011 (bez klikania przez bridge)

Bridge ustawia `last_module=RomeBladeRTS` i startuje exe. SkinMagic zostaje: Ty **Graj** → **Nowa gra** → Wave Battle (INIT). Bridge nie klika okien M&B.

Wave dostaje z zapisu RTW (**+34**): sumy armii + proporcje ról (piechota/strzelcy/jazda) → Native stand-iny Swadian/Vaegir. 1:1 modele RTW→M&B jeszcze nie.

## One instruction (next try)

1. Zamknij stare okna Rome / bridge / Mount&Blade (panel Arm nie jest już potrzebny).
2. `start_romeblade.bat` → ładuj kampanię → otwórz zwój → **Begin Battle** (GDI ma uzbroić hak; F5 awaryjnie).
3. W M&B: **Graj** → **Nowa gra** → Wave ze składem z zapisu.

Log: `out\bridge_events.log` — `detect detected=True` → `hook_armed source=gdi` → `click_swallowed` → `mb_start` → `menus_patched`.

## Trigger

| Step | Method |
|------|--------|
| Arm | **GDI** prebattle art (Rome `-ne`), F5 backup |
| Swallow | Po arm: następny LMB zjedzony |
| Armies | `prepare_mb`: totals + role mix w `menus.txt` |
