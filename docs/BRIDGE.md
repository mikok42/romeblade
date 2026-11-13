# RomeBlade bridge (RTW ↔ M&B)

## One instruction (next try)

1. Close **only** Rome / bridge / Arm / M&B windows from the last try (nie zabijaj innych procesów).
2. Run **`start_romeblade.bat`** → scroll → **UZBRÓJ** → **Begin Battle**.
3. Expect: swallow → M&B launcher → auto **Graj w Mount&Blade** → auto **New Game** → **Wave Battle** (nie zostaje na launcherze).

Log: `out\bridge_events.log` — szukaj `mb_launcher_play`, potem `mb_wave_enter_clicked`.

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
