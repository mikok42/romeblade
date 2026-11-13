"""F5 arm paths: RegisterHotKey + GetAsyncKeyState poll (exclusive-FS backup).

Log proof (2026-11-13 13:58): bridge alive, many detect lines, ZERO hotkey_f5
while user pressed F5 in exclusive Rome — RegisterHotKey alone is not enough.
Main loop should also call ``poll_f5_async`` and the Arm panel flag.
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
VK_F5 = 0x74


class HotkeyArm(object):
    def __init__(self, vk=None, hotkey_id=None):
        self.vk = vk if vk is not None else config.HOTKEY_VK
        self.hotkey_id = hotkey_id if hotkey_id is not None else config.HOTKEY_ID
        self._pressed = threading.Event()
        self._thread = None
        self._tid = None
        self.register_ok = None
        self.register_err = None
        self._async_was_down = False

    def take_press(self):
        if self._pressed.is_set():
            self._pressed.clear()
            return True
        return False

    def poll_f5_async(self):
        """Edge-detect F5 via GetAsyncKeyState (works more often than HotKey under games)."""
        state = user32.GetAsyncKeyState(self.vk)
        down = bool(state & 0x8000)
        edged = down and not self._async_was_down
        self._async_was_down = down
        if edged:
            self._pressed.set()
            return True
        return False

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return

        def runner():
            self._tid = ctypes.windll.kernel32.GetCurrentThreadId()
            ok = user32.RegisterHotKey(None, self.hotkey_id, MOD_NOREPEAT, self.vk)
            self.register_ok = bool(ok)
            if not ok:
                self.register_err = ctypes.get_last_error()
            msg = wt.MSG()
            while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
                if msg.message == WM_HOTKEY and msg.wParam == self.hotkey_id:
                    self._pressed.set()
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            user32.UnregisterHotKey(None, self.hotkey_id)

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
