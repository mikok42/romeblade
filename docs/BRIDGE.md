# RomeBlade bridge (RTW ↔ M&B)

## M&B 1.011 — uczciwy tor (bez klikania przez bridge)

Na tym dysku **nie da się** wyłączyć SkinMagic / pominąć launchera CLI / wejść w misję bez menu głównego (brak przełącznika w exe, tylko `last_module` + SkinMagic). Bridge **nie klika** okien.

Po `mb_start`: Ty robisz **Graj w Mount&Blade**, potem **Nowa gra** (albo Bitwa własna) — INIT w RomeBladeRTS sam ładuje **Wave Battle**.

## One instruction (next try)

1. Zamknij okna Rome / bridge / Arm / Mount&Blade z poprzedniej próby.
2. `start_romeblade.bat` → scroll → **UZBRÓJ** → **Begin Battle**.
3. Gdy wyskoczy M&B: **Graj** → **Nowa gra** → od razu Wave Battle (bez pickera scenariusza).

## Why F5 failed (log proof 2026-11-13 13:58)

Bridge was alive (`bridge_start`, continuous `detect`). **Zero** `hotkey_f5` / `hook_armed` / `click_swallowed` while the user pressed F5 in exclusive fullscreen. GDI often `black_likely_exclusive_fs` or desktop wallpaper. So F5 never armed the hook → Rome got Begin Battle.

Fix: **Arm panel** (flag file) + windowed `-ne` starter + GetAsyncKeyState(F5) backup + swallow-**any** click once armed.

## Trigger

| Step | Method |
|------|--------|
| Arm | **UZBRÓJ** panel, or F5 (async/hotkey), or GDI scroll match |
| Swallow | After arm: **next left-click anywhere** is eaten |
| Armies / M&B / return | unchanged (save → quicksave + Ctrl+L) |

Fullscreen bat exists but requires Alt+Tab → UZBRÓJ → back to Rome. Prefer windowed.
