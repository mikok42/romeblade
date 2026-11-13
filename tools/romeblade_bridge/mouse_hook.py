"""Low-level mouse hook to see (and optionally eat) left clicks."""
from __future__ import print_function

import ctypes
import ctypes.wintypes as wt
import threading
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_MOUSE_LL = 14
WM_LBUTTONDOWN = 0x0201
WM_QUIT = 0x0012
HC_ACTION = 0


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wt.POINT),
        ("mouseData", wt.DWORD),
        ("flags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


LowLevelMouseProc = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_int, wt.WPARAM, wt.LPARAM
)


class MouseHook(object):
    def __init__(self, on_left_down):
        """on_left_down(x, y) -> True to swallow the click."""
        self.on_left_down = on_left_down
        self._hook = None
        self._proc = LowLevelMouseProc(self._callback)
        self._thread = None
        self._tid = None
        self._stopped = threading.Event()

    def _callback(self, nCode, wParam, lParam):
        if nCode == HC_ACTION and wParam == WM_LBUTTONDOWN:
            info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            try:
                swallow = self.on_left_down(info.pt.x, info.pt.y)
            except Exception:
                swallow = False
            if swallow:
                return 1  # nonzero = don't pass to next hook / app
        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def start(self):
        def runner():
            self._tid = kernel32.GetCurrentThreadId()
            self._hook = user32.SetWindowsHookExW(
                WH_MOUSE_LL, self._proc, None, 0
            )
            if not self._hook:
                raise ctypes.WinError(ctypes.get_last_error())
            msg = wt.MSG()
            while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            if self._hook:
                user32.UnhookWindowsHookEx(self._hook)
                self._hook = None
            self._stopped.set()

        self._stopped.clear()
        self._thread = threading.Thread(target=runner, name="rb-mouse-hook")
        self._thread.daemon = True
        self._thread.start()
        # Brief wait so SetWindowsHookEx has run before callers proceed.
        time.sleep(0.15)

    def stop(self):
        """Unhook and join the hook thread. Safe to call more than once."""
        if self._tid:
            user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(timeout=3)
        # If the thread did not clear the hook (stuck GetMessage), force unhook.
        if self._hook:
            try:
                user32.UnhookWindowsHookEx(self._hook)
            except Exception:
                pass
            self._hook = None
        self._tid = None
        self._stopped.set()
