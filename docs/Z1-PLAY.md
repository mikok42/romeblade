# Z1 — RomeBladeRTS bird's-eye battle (M&B 1.011)

## What was installed

| Piece | Where |
|-------|--------|
| Module | `C:\Program Files (x86)\Steam\steamapps\common\Mount and Blade\Modules\RomeBladeRTS` |
| Module System 1.010 (sources) | `c:\Users\Mikok\Documents\RomeAndBlade\tools\romeblade_rts_ms\` |
| Stock MS zip | `c:\Users\Mikok\Documents\RomeAndBlade\tools\module_system_1010\` |
| Python 2.7.18 | `C:\Python27\python.exe` (used only to compile) |

**Native was not modified.** Only a new `Modules\RomeBladeRTS` folder was added (seeded from Native, then rebuilt).

## How to launch

1. Start **Mount & Blade** (Steam appid 22100).
2. In the module dropdown (launcher / main menu module list), pick **RomeBladeRTS** (not Native).
3. Start a **Quick Battle** / custom battle with both sides filled (try ~50 vs 50 first, then raise).
4. In battle:
   - **F10** — toggle bird's-eye RTS camera on/off
   - **WASD** / arrows — pan; **Q/E** — height; **Shift** — faster pan
   - **Backspace** — stock battle order panel (F1–F4 groups, etc.)
   - **F9** — HOLD at ground under camera (point-order prototype)
   - **F8** — CHARGE everyone
   - **F7** — FOLLOW

## Answers Z1 must produce (prototype intent)

1. **Player body while camera is up:** stashed high above the field (`position_set_z`) + continuous HP lock to 100%. There is **no** true invulnerability or AI hand-off op in stock 1.011 — this is the best available handling.
2. **Orders from above:** stock Backspace panel works; F9 adds hold-at-camera-ground via `team_set_order_position`.
3. **Soldier count / FPS:** measure on this PC in Quick Battle; raise troop counts until it stutters.

## Rebuild after script edits

```bat
cd /d c:\Users\Mikok\Documents\RomeAndBlade\tools\romeblade_rts_ms
build_module.bat
```

Exports into `Modules\RomeBladeRTS\` (see `module_info.py`).
