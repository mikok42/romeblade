# RomeBlade bridge (RTW ↔ M&B)

## One instruction (next try)

1. Close **only** Rome / bridge / Arm / M&B windows from the last try (do not kill unrelated processes).
2. Run **`start_romeblade.bat`** → load campaign → open land-battle scroll → **UZBRÓJ** → **Begin Battle**.
3. Expect: click swallowed → **RomeBladeRTS** starts → auto **New Game** click → **Wave Battle** mission (not Native / not idle main menu).

Log: `out\bridge_events.log` (`mb_start`, `mb_wave_enter_clicked`). If you land on the M&B title screen without a battle, click **New Game** once (INIT still forces Wave Battle).

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
