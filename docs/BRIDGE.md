# RomeBlade bridge (RTW ↔ M&B)

## Jeden executable?

**Jeden silnik: nie.** **Jeden most bez UI: tak** — `start_romeblade.bat` = bridge (w tle) + Rome `-ne`, bez UZBRÓJ.

## Co Wave bierze z RTW

| Działa | Jeszcze nie |
|--------|-------------|
| Sumy armii z **+34** (display) | Modele 1:1 typów EDU→troop |
| Proporcje ról piechota/strzelcy/jazda → spawn + fale | Dokładna para armii ze zwoju (bez manifestu bywa fallback „hostile”) |
| `prepare_mb` patch `menus.txt` (8 immediates) | Auto Graj/Nowa gra (celowo nie — bez UI-klikania) |

Stand-iny: Swadian (A) / Vaegir (B). Po `mb_start` w logu: `prepare_mb` z `roles_a` / `roles_b`.

## One instruction (next try)

1. Zamknij okna Rome / bridge / M&B z poprzedniej próby (bez panelu Arm).
2. Odpal **`start_romeblade.bat`** → kampania → zwój przed bitwą → **Begin Battle** (GDI uzbraja; jak nie — **F5**, potem klik).
3. W M&B ręcznie: **Graj** → **Nowa gra** → Wave. Sprawdź, że strona gracza ma dużo strzelców jeśli RTW miało łuczników, a wróg prawie samą piechotę (ostatni przykład ~1880 inf / 52 cav).

Log: `out\bridge_events.log` — `hook_armed source=gdi` (lub `hotkey_f5`) → `click_swallowed` → `prepare_mb ok=true` → `mb_start`.
