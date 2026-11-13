# Z1 — RomeBladeRTS (M&B 1.011)

## Module

`C:\Program Files (x86)\Steam\steamapps\common\Mount and Blade\Modules\RomeBladeRTS`  
Native is **not** modified.

## Launch

1. Start Mount & Blade → module **RomeBladeRTS** (bridge sets `last_module` itself).
2. **New Game** or **Custom Battle** both jump straight into **RomeBlade Wave Battle** (menu INIT — no scenario picker).
3. Bridge also auto-clicks **New Game** after launch so you should land in the mission without Native menus.

## Bird-eye controls (F10)

| Key | Action |
|-----|--------|
| **F10** | Toggle bird's-eye |
| **WASD** | Move camera on horizontal plane (relative to look yaw) |
| **Q / E** | Down / up |
| **Shift** | Faster move |
| **Backspace** | Order panel (kept open in bird-eye) |
| **F9 / F8 / F7** | Hold-at-point / Charge / Follow |

While bird-eye is on, **rider and horse** are frozen at a stash point + HP lock (1611cc7 only froze the rider; mounted WASD still moved the horse — fixed in this build).

## Wave battle defaults (edit in `tools/romeblade_rts_ms/module_constants.py`)

| Constant | Default | Meaning |
|----------|---------|---------|
| `rb_wave_army_a` | **300** | Player-side host size |
| `rb_wave_army_b` | **150** | Enemy host size (entry ratio 2:1) |
| `rb_wave_field_cap` | **90** | Max non-hero humans on field |
| `rb_wave_refill_pct` | **50** | Refill when living &lt; 50% of that side's field target |
| `rb_wave_spawn_chunk` | **12** | Max spawns per side per pulse |
| `rb_wave_check_interval` | **3** | Seconds between checks |

With 300 vs 150 and cap 90: field targets **60 vs 30**, reserves **240 vs 120**. HUD shows on-field + reserve counts.

## Rebuild

```bat
cd /d c:\Users\Mikok\Documents\RomeAndBlade\tools\romeblade_rts_ms
build_module.bat
```
