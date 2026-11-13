# RomeBlade

File-ledger switcher between **Rome: Total War** (campaign turns) and original **Mount & Blade 1.011** (battle / town / field).  
Not a dual-engine mashup: games stay stock; handoff is a JSON ledger.

## Layout

| Path | Role |
|------|------|
| `generate_map.py` | Synthetic Mediterranean `map.txt` |
| `rtw_map.py` | RTW `data/world/maps/base` → M&B `map.txt` + settlements |
| `switch.py` | Ledger: `to-blade` / `to-rome` / `status` |
| `units.py` + `data/units.json` | 124 role-based unit cards (stand-ins for exotic bodies) |
| `prepare.py` | Bake `module/RomeBlade/` skeleton |
| `paths.json` | Local Steam install paths (this PC) |
| `module/RomeBlade/` | Uncompiled module skeleton + `BUILD.txt` |
| `handoff/` | Runtime ledger (`state.json`) |

## Quick start (this PC)

```powershell
cd c:\Users\Mikok\Documents\RomeAndBlade
python units.py --rewrite --self-test
python generate_map.py --self-test
python rtw_map.py --self-test
python switch.py --self-test
python prepare.py --self-test

# Real RTW bake (Gold imperial/base map):
python rtw_map.py --out out\from-rome
python prepare.py --base "C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold\data\world\maps\base" --battle out\battle.sample.json
```

## Honest blockers

- **Module System 1.011 + Python 2.7** required to compile a loadable M&B module (`BUILD.txt`).
- **`.sco` town scenes** must be made in the M&B scene editor — not generated here.
- **No automatic RTW army export / save write-back** — ledger is manual.
- Elephants, chariots, siege, camels, dogs, pigs, naval = **stand-in** cards; no RTW meshes vendored.

## Games (DESKTOP-QO223A2)

See `paths.json` and Project doc `docs/romeblade-local-progress.md`.
