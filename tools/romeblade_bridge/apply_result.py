"""After M&B: drive auto_win + Auto Resolve, then write a result save copy."""
from __future__ import print_function

import os
import time

from . import config
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


def click_auto_resolve_guess(screen_w=1920, screen_h=1080):
    """Best-effort click on Auto Resolve (middle of the three buttons)."""
    # Without a confirmed hitbox, click near Begin Battle's left neighbour.
    # User may still need to click Auto Resolve once if this misses.
    import ctypes

    user32 = ctypes.windll.user32
    cx = screen_w // 2 + 120
    cy = int(screen_h * 0.74)
    user32.SetCursorPos(cx, cy)
    time.sleep(0.05)
    # mouse_event left down/up
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    return (cx, cy)


def write_result_save_from_source(src_save, patches, dest_name=None):
    """patches: list of (cur_off, new_current). Creates ONLY a new file."""
    dest_name = dest_name or config.RESULT_SAVE_NAME
    dst = os.path.join(config.RTW_SAVES, dest_name)
    if os.path.exists(dst):
        # Allow replacing OUR previous result save only.
        if os.path.basename(dst) in config.PROTECTED_SAVES:
            raise RuntimeError("protected")
        os.remove(dst)
    save_io.patch_currents_in_copy(src_save, dst, patches, config.PROTECTED_SAVES)
    return dst
