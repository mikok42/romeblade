# RomeBlade — local progress (DESKTOP-QO223A2)

Updated: 2026-11-13 (worker `bc-5b5e7c67-2142-57a4-a5b2-b8c7c00665d1`)  
Folder: `c:\Users\Mikok\Documents\RomeAndBlade`  
Repo: https://github.com/mikok42/romeblade  

## Everyday start

```bat
start_romeblade.bat
```

On the pre-battle scroll: **F5** then **Begin Battle**. Do not close the minimized bridge window.  
Logs: `out\bridge_events.log` (steps) + `out\bridge_run.log` (stdout).

## First live try (failed) — disk evidence

- Hook always-on + **1903×** `CallNextHookEx` `OverflowError` (Win64 LPARAM) → cursor stutter, swallow broken.
- No `scroll detected` / swallow / M&B start in log; M&B `rgl_log` stale (11:34).
- `live.bmp` **not black** — bright desktop (GDI saw wallpaper, not RTW UI).
- Restart hit `TypeError: MouseHook.__init__()` mid-fix (partial deploy). Bridge then saw `RomeTW.exe gone` and exited.

## Fixes since

- Hook only while armed; ctypes-only callback; **CallNextHookEx argtypes** fixed.
- Detect ~22 s → ~0.13 s (crop); below-normal priority.
- **F5 arm** without GDI; `bridge_events.log` for each step.

## E1

+34 alone survives end turn on card; +30/slots not synced. Retrain unverified.
