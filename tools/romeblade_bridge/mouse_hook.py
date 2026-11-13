"""Low-level mouse hook — install only while armed for Begin Battle.

Modes:
  * box — swallow left-down inside a ctypes hitbox
  * any — swallow the next left-down anywhere (F5 path; most reliable)

Callback stays ctypes-only on the hot path. CallNextHookEx uses Win64 argtypes.
"""
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

LRESULT = ctypes.c_ssize_t
HHOOK = ctypes.c_void_p
user32.CallNextHookEx.argtypes = [HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
user32.CallNextHookEx.restype = LRESULT
user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    ctypes.c_void_p,
    wt.HINSTANCE,
    wt.DWORD,
]
user32.SetWindowsHookExW.restype = HHOOK
user32.UnhookWindowsHookEx.argtypes = [HHOOK]
user32.UnhookWindowsHookEx.restype = wt.BOOL


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wt.POINT),
        ("mouseData", wt.DWORD),
        ("flags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


LowLevelMouseProc = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)

MODE_BOX = 0
MODE_ANY = 1


class MouseHook(object):
    def __init__(self):
        self._armed = ctypes.c_int(0)
        self._mode = ctypes.c_int(MODE_BOX)
        self._box = (ctypes.c_long * 4)(0, 0, 0, 0)
        self._swallowed = ctypes.c_int(0)
        self._sx = ctypes.c_long(0)
        self._sy = ctypes.c_long(0)
        self._seen = ctypes.c_int(0)  # left-downs while armed (swallowed or not)
        self._lastx = ctypes.c_long(0)
        self._lasty = ctypes.c_long(0)
        self._hook = None
        self._proc = LowLevelMouseProc(self._callback)
        self._thread = None
        self._tid = None
        self._stopped = threading.Event()

    @property
    def installed(self):
        return self._thread is not None and self._thread.is_alive()

    def set_hitbox(self, x0, y0, x1, y1):
        self._box[0] = int(x0)
        self._box[1] = int(y0)
        self._box[2] = int(x1)
        self._box[3] = int(y1)
        self._mode.value = MODE_BOX

    def set_swallow_any(self):
        """Next left-click anywhere is swallowed (F5 / reliability mode)."""
        self._mode.value = MODE_ANY

    def arm(self):
        self._swallowed.value = 0
        self._seen.value = 0
        self._armed.value = 1

    def disarm(self):
        self._armed.value = 0

    def take_swallow(self):
        if not self._swallowed.value:
            return None
        self._swallowed.value = 0
        return (int(self._sx.value), int(self._sy.value))

    def take_seen_click(self):
        """Any left-down while armed (for miss diagnostics)."""
        if not self._seen.value:
            return None
        self._seen.value = 0
        return (int(self._lastx.value), int(self._lasty.value))

    def _callback(self, nCode, wParam, lParam):
        if nCode != HC_ACTION or wParam != WM_LBUTTONDOWN:
            return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)
        if not self._armed.value:
            return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)
        info = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
        x = info.pt.x
        y = info.pt.y
        self._lastx.value = x
        self._lasty.value = y
        self._seen.value = 1
        hit = self._mode.value == MODE_ANY or (
            self._box[0] <= x <= self._box[2]
            and self._box[1] <= y <= self._box[3]
        )
        if hit:
            self._armed.value = 0
            self._sx.value = x
            self._sy.value = y
            self._swallowed.value = 1
            return 1
        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return

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
            self._armed.value = 0
            self._stopped.set()

        self._stopped.clear()
        self._thread = threading.Thread(target=runner, name="rb-mouse-hook")
        self._thread.daemon = True
        self._thread.start()
        time.sleep(0.05)

    def stop(self):
        self._armed.value = 0
        if self._tid:
            user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(timeout=3)
        if self._hook:
            try:
                user32.UnhookWindowsHookEx(self._hook)
            except Exception:
                pass
            self._hook = None
        self._tid = None
        self._thread = None
        self._stopped.set()
