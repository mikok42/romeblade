"""Return to RTW via campaign quicksave slot — no Load Game menu.

Evidence (offline, not an in-game proof):
  * preferences/keys.dat has strat_ui actions ``save_stratmap`` / ``load_stratmap``.
  * Community FAQ / manual extract: Quick save = Ctrl+S, Quick load = Ctrl+L.
  * Hotseat guides name the file ``quicksave.sav`` under ``saves\\``.
  * This install currently has no ``quicksave.sav`` until the player Ctrl+S once.

UNVERIFIED in-game (must be tried on desk):
  * Overwriting ``quicksave.sav`` while RTW is running, then Ctrl+L, loads that
    file mid-campaign (including from the pre-battle scroll).
  * Whether DirectInput swallows synthetic Ctrl+L the same as a real keypress.
  * Exact casing on disk if the player already has a slot (we use lowercase).
"""
from __future__ import print_function

import os
import shutil
import time
from datetime import datetime

from . import config
from . import win_input

VK_CONTROL = 0x11
VK_S = 0x53
VK_L = 0x4C


def quicksave_path(saves_dir=None):
    saves_dir = saves_dir or config.RTW_SAVES
    return os.path.join(saves_dir, config.QUICKSAVE_NAME)


def backup_existing_quicksave(saves_dir=None):
    """If quicksave.sav exists, copy it to rb_qs_backup_<stamp>.sav. Never delete."""
    saves_dir = saves_dir or config.RTW_SAVES
    src = quicksave_path(saves_dir)
    if not os.path.isfile(src):
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_name = "%s%s.sav" % (config.QUICKSAVE_BACKUP_PREFIX, stamp)
    dest = os.path.join(saves_dir, dest_name)
    # Collision: add a counter rather than overwrite any backup.
    n = 0
    while os.path.exists(dest):
        n += 1
        dest_name = "%s%s_%d.sav" % (config.QUICKSAVE_BACKUP_PREFIX, stamp, n)
        dest = os.path.join(saves_dir, dest_name)
    shutil.copy2(src, dest)
    return dest


def install_result_as_quicksave(result_path, saves_dir=None):
    """Backup any existing quicksave, then copy result_path over quicksave.sav.

    Never deletes the player's previous quicksave without a backup copy.
    Does not touch RomaAroma / Autosave / niunia.
    """
    saves_dir = saves_dir or config.RTW_SAVES
    if not os.path.isfile(result_path):
        raise RuntimeError("missing result save: %s" % result_path)
    base = os.path.basename(result_path)
    if base in config.PROTECTED_SAVES:
        raise RuntimeError("refusing protected source: %s" % base)
    backup = backup_existing_quicksave(saves_dir)
    dest = quicksave_path(saves_dir)
    # Replace via copy (atomic-ish on same volume: write temp then replace).
    tmp = dest + ".rb_tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    shutil.copy2(result_path, tmp)
    if os.path.exists(dest):
        os.remove(dest)
    os.rename(tmp, dest)
    return {"quicksave": dest, "backup": backup, "from": result_path}


def tap_ctrl_key(vk, pause=0.35):
    """Send Ctrl+<vk> via SendInput. Focus RTW first (caller)."""
    win_input._send_vk(VK_CONTROL, up=False)
    time.sleep(0.04)
    win_input.tap_vk(vk, hold=0.05, pause=0.05)
    win_input._send_vk(VK_CONTROL, up=True)
    time.sleep(pause)


def send_quick_load():
    """Ctrl+L — UNVERIFIED that RTW accepts this from SendInput on the scroll."""
    wins = win_input.find_windows("Rome") or win_input.find_windows("Total War")
    if not wins:
        return False
    win_input.focus_window(wins[0][0])
    tap_ctrl_key(VK_L, pause=0.5)
    return True


def send_quick_save():
    """Ctrl+S — optional; bridge normally writes the file itself."""
    wins = win_input.find_windows("Rome") or win_input.find_windows("Total War")
    if not wins:
        return False
    win_input.focus_window(wins[0][0])
    tap_ctrl_key(VK_S, pause=0.5)
    return True
