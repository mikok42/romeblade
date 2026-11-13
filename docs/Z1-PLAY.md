# Z1 — RomeBladeRTS bird's-eye battle (M&B 1.011)

## What was installed

| Piece | Where |
|-------|--------|
| Module | `C:\Program Files (x86)\Steam\steamapps\common\Mount and Blade\Modules\RomeBladeRTS` |
| Module System sources | `c:\Users\Mikok\Documents\RomeAndBlade\tools\romeblade_rts_ms\` |
| Python 2.7.18 | `C:\Python27\python.exe` (compile only) |

**Native was not modified.** Only `Modules\RomeBladeRTS` is added/updated.

## How to launch

1. Start **Mount & Blade**.
2. Pick module **RomeBladeRTS**.
3. Start a **Quick Battle**.
4. On-screen **CONTROLS** legend appears at battle start (`tutorial_message`).

## Controls

| Key | Action |
|-----|--------|
| **F10** | Toggle bird's-eye camera |
| **WASD** / arrows | Move camera on the **horizontal plane**, relative to where the camera looks (W/S forward-back, A/D strafe) |
| **Q** | Camera **down** |
| **E** | Camera **up** |
| **Shift** | Faster camera move |
| **Backspace** | Stock order panel (auto-kept open while bird-eye is on; if you close it, it reopens) |
| **F9** | HOLD everyone at ground under camera |
| **F8** | CHARGE |
| **F7** | FOLLOW |

While bird-eye is on, the player body is frozen at a stashed high position + HP locked so WASD does not walk the soldier. There is no true input-disable op in stock 1.011.

## Rebuild

```bat
cd /d c:\Users\Mikok\Documents\RomeAndBlade\tools\romeblade_rts_ms
build_module.bat
```
