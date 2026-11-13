"""Global F5 (configurable) to arm the Begin Battle hook without GDI detect.

Justification: exclusive fullscreen often makes GDI BitBlt useless (black or
desktop-behind-game). There is no reliable on-disk prebattle marker before
Begin Battle (``temp\\battle.rpy`` appears only after the fight starts).
A one-key arm while the scroll is visible is the screenshot-independent path.

UNVERIFIED in-game: RegisterHotKey while RTW has exclusive focus may still
receive F5; if not, user must Alt-Tab once or use windowed ``-ne``.
"""
from __future__ import print_function

import ctypes
import ctypes.wintypes as wt
import threading

from . import config

user32 = ctypes.windll.user32

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_NOREPEAT = 0x4000


class HotkeyArm(object):
    def __init__(self, vk=None, hotkey_id=None):
        self.vk = vk if vk is not None else config.HOTKEY_VK
        self.hotkey_id = hotkey_id if hotkey_id is not None else config.HOTKEY_ID
        self._pressed = threading.Event()
        self._thread = None
        self._tid = None

    def take_press(self):
        if self._pressed.is_set():
            self._pressed.clear()
            return True
        return False

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return

        def runner():
            self._tid = ctypes.windll.kernel32.GetCurrentThreadId()
            ok = user32.RegisterHotKey(None, self.hotkey_id, MOD_NOREPEAT, self.vk)
            if not ok:
                # Still run message loop; bridge logs failure.
                self._register_ok = False
            else:
                self._register_ok = True
            msg = wt.MSG()
            while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
                if msg.message == WM_HOTKEY and msg.wParam == self.hotkey_id:
                    self._pressed.set()
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            user32.UnregisterHotKey(None, self.hotkey_id)

        self._register_ok = None
        self._thread = threading.Thread(target=runner, name="rb-hotkey")
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        if self._tid:
            user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(timeout=2)
        self._tid = None
        self._thread = None
