"""After M&B: clear the RTW scroll without a tactical fight, apply result save.

Return path no longer uses the Load Game menu (proven unreliable). Primary
path: write ``romeblade_result.sav``, install it as ``quicksave.sav`` (after
backing up any existing quicksave), then Ctrl+L.

``auto_win`` + Auto Resolve click remain as a fallback to dismiss the scroll
if quick-load does not (both still best-effort / partly unverified).
"""
from __future__ import print_function

import os
import time

from . import config
from . import quicksave
from . import save_io
from . import win_input


def focus_rtw():
    wins = win_input.find_windows("Rome") or win_input.find_windows("Total War")
    if not wins:
        return False
    win_input.focus_window(wins[0][0])
    return True


def send_auto_win(side):
    """side: 'attacker' or 'defender'. Must run on the pre-battle scroll."""
    if side not in ("attacker", "defender"):
        raise ValueError(side)
    if not focus_rtw():
        return False
    win_input.tap_vk(win_input.VK_OEM_3, pause=0.4)
    win_input.tap_text_unicode("auto_win %s" % side)
    win_input.tap_vk(win_input.VK_RETURN, pause=0.3)
    win_input.tap_vk(win_input.VK_OEM_3, pause=0.3)  # close console
    return True


def click_auto_resolve_guess(screen_w=None, screen_h=None):
    """Best-effort click on Auto Resolve (middle of the three buttons)."""
    import ctypes

    user32 = ctypes.windll.user32
    if screen_w is None:
        screen_w = user32.GetSystemMetrics(0)
    if screen_h is None:
        screen_h = user32.GetSystemMetrics(1)
    cx = screen_w // 2 + 120
    cy = int(screen_h * 0.74)
    user32.SetCursorPos(cx, cy)
    time.sleep(0.05)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    return (cx, cy)


def write_result_save_from_source(src_save, patches, dest_name=None):
    """patches: list of (cur_off, new_current). Creates ONLY a new file."""
    dest_name = dest_name or config.RESULT_SAVE_NAME
    dst = os.path.join(config.RTW_SAVES, dest_name)
    if os.path.exists(dst):
        if os.path.basename(dst) in config.PROTECTED_SAVES:
            raise RuntimeError("protected")
        os.remove(dst)
    save_io.patch_currents_in_copy(src_save, dst, patches, config.PROTECTED_SAVES)
    return dst


def return_via_quicksave(result_path):
    """Install result as quicksave and send Ctrl+L. No menu navigation.

    Returns a dict with backup path and whether Ctrl+L was sent.
    Quick-load effect in-game is UNVERIFIED.
    """
    info = quicksave.install_result_as_quicksave(result_path)
    sent = quicksave.send_quick_load()
    info["ctrl_l_sent"] = sent
    info["ctrl_l_effect"] = "unverified"
    return info
