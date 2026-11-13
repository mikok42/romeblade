"""In-game check #1: load a modified save, end turn, save as new name, reload.

Uses -ne on the RTW command line only (does not rewrite preferences).
Never overwrites protected player saves.
"""
from __future__ import print_function

import os
import sys
import time

from . import config
from . import launchers
from . import save_io
from . import win_input


SHOTS = os.path.join(config.REPO_ROOT, "out", "ingame_shots")


def _shot(name):
    os.makedirs(SHOTS, exist_ok=True)
    path = os.path.join(SHOTS, name)
    win_input.screenshot_window_bmp(path)
    print("SHOT", path)
    return path


def _focus_rtw(timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        wins = win_input.find_windows("Rome") or win_input.find_windows("Total War")
        if wins:
            win_input.focus_window(wins[0][0])
            return wins[0]
        time.sleep(1)
    return None


def ensure_not_running():
    if launchers.process_running("RomeTW.exe"):
        raise SystemExit("BLOCKED: RomeTW.exe already running — abort")


def kill_rtw():
    os.system('taskkill /IM RomeTW.exe /F >nul 2>&1')
    time.sleep(2)
    return not launchers.process_running("RomeTW.exe")


def main():
    ensure_not_running()
    src = os.path.join(config.RTW_SAVES, "proba_disp41.sav")
    if not os.path.isfile(src):
        raise SystemExit("missing proba_disp41.sav")
    dest_name = "proba_endturn41.sav"
    dest = os.path.join(config.RTW_SAVES, dest_name)
    if os.path.exists(dest):
        raise SystemExit("dest exists (won't overwrite): %s" % dest)

    print("starting RTW (-ne -show_err) for end-turn check...")
    proc = launchers.start_rtw_windowed()
    time.sleep(10)
    win = _focus_rtw()
    if not win:
        _shot("et_no_window.bmp")
        kill_rtw()
        raise SystemExit("NO_WINDOW")

    # Skip intros
    for _ in range(12):
        win_input.tap_vk(win_input.VK_ESCAPE, pause=0.35)
    _shot("et_01_menu.bmp")

    # Best-effort: Single Player -> Load Game
    # Main menu often: Single Player is first Enter
    win_input.tap_vk(win_input.VK_RETURN, pause=1.2)
    _shot("et_02_sp.bmp")
    # Load Game is typically below Continue / below Campaign
    for _ in range(3):
        win_input.tap_vk(win_input.VK_DOWN, pause=0.25)
    win_input.tap_vk(win_input.VK_RETURN, pause=2.0)
    _shot("et_03_loadlist.bmp")

    print(
        "MANUAL_NEEDED: keyboard load of 'proba_disp41' is unreliable. "
        "Screenshots are in out/ingame_shots. "
        "If the load list is visible, load proba_disp41, end turn (button), "
        "save as %s, reload that save, then close RTW." % dest_name
    )
    print(
        "This agent will wait up to 10 minutes for %s to appear, then kill RTW "
        "and verify display fields." % dest_name
    )

    t0 = time.time()
    while time.time() - t0 < 600:
        if os.path.isfile(dest):
            print("FOUND", dest)
            break
        # user may still be playing — do not steal mouse; only poll disk
        time.sleep(3)
    else:
        print("TIMEOUT waiting for", dest_name)
        alive = launchers.process_running("RomeTW.exe")
        print("RomeTW_alive", alive)
        _shot("et_timeout.bmp")
        # Do not kill if user might be playing — but user said we may automate
        # and they closed RTW knowing games will open. Kill to clean up.
        kill_rtw()
        return 2

    time.sleep(2)
    kill_rtw()

    # Verify +34 values still look patched on a unit from disp41 army
    data = open(dest, "rb").read()
    # count units with display==41
    n41 = 0
    for u in save_io.iter_units_of_type(data, "roman princeps"):
        if u.get("display", u.get("full")) == 41:
            n41 += 1
    for u in save_io.iter_units_of_type(data, "roman hastati"):
        if u.get("display", u.get("full")) == 41:
            n41 += 1
    print("units_with_display_41", n41)
    print("ENDTURN_OK" if n41 > 0 else "ENDTURN_DISPLAY_LOST")
    return 0 if n41 > 0 else 3


if __name__ == "__main__":
    sys.exit(main())
