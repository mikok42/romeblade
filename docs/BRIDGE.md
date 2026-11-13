# RomeBlade bridge (RTW ↔ M&B)

## CLI (M&B 1.011 na tym dysku)

**Nie** — `mount&blade.exe` nie ma przełącznika, który pomija launcher albo od razu ładuje misję / Custom Battle / Wave Battle. Moduł bierze z `HKCU\Software\MountAndBladeKeys\last_module`; potem zawsze SkinMagic (**Graj w Mount&Blade**), potem New Game (INIT Wave).

## One instruction (next try)

1. Zamknij **okna** Rome / bridge / Arm / Mount&Blade z poprzedniej próby (nie zabijaj innych procesów).
2. `start_romeblade.bat` → scroll → **UZBRÓJ** → **Begin Battle**.
3. W logu kolejno: `mb_exe_started` (albo `mb_reuse_windows`) → **`mb_launcher_play`** (pid mount&blade) → `mb_wave_enter_clicked`. Jeśli znów tylko launcher bez `mb_launcher_play` — daj znać.

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
