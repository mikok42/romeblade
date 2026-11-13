"""Start / focus RTW and Mount & Blade without touching stock game files."""
from __future__ import print_function

import os
import subprocess
import time

try:
    import winreg
except ImportError:
    import _winreg as winreg  # noqa

from . import config


def set_mb_module(module_name):
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\MountAndBladeKeys")
    winreg.SetValueEx(key, "last_module", 0, winreg.REG_SZ, module_name)
    winreg.CloseKey(key)


def enter_wave_from_main_menu(timeout=90):
    """After M&B shows its main screen, click New Game → Wave Battle (menu INIT).

    RomeBladeRTS start_game_1 INIT jumps straight into the wave mission, so one
    New Game click is enough. Does not kill processes; no-ops if window missing.
    """
    from . import blog
    from . import win_input

    hwnd = win_input.wait_for_window("Mount", timeout=timeout)
    if not hwnd:
        # Title is usually "Mount&Blade" — try a second needle.
        hwnd = win_input.wait_for_window("Blade", timeout=5)
    if not hwnd:
        print("BRIDGE: M&B window not found — cannot auto-enter wave")
        blog.event("mb_wave_enter_fail", reason="no_window")
        return False
    win_input.focus_window(hwnd)
    # Let the main menu finish fading in before the click.
    time.sleep(2.5)
    # New Game is the top main-menu button (center column). Try two Y fractions
    # in case of letterboxing / resolution quirks — each click is harmless if miss.
    for fy in (0.42, 0.48, 0.36):
        x, y = win_input.click_window_client_frac(hwnd, 0.5, fy, pause=0.8)
        print("BRIDGE: click New Game candidate @ %d,%d (fy=%.2f)" % (x, y, fy))
    blog.event("mb_wave_enter_clicked")
    return True


def start_mb(module_name=None, enter_wave=True):
    module_name = module_name or config.MB_MODULE
    set_mb_module(module_name)
    if not os.path.isfile(config.MB_EXE):
        raise RuntimeError("M&B exe missing: %s" % config.MB_EXE)
    # Do not kill an already-running M&B; only launch if none is up.
    already = process_running("mount&blade")
    if already:
        print("BRIDGE: M&B already running - skip new process, try enter wave")
        proc = None
    else:
        proc = subprocess.Popen(
            [config.MB_EXE],
            cwd=config.MB_ROOT,
            close_fds=True,
        )
    if enter_wave:
        try:
            enter_wave_from_main_menu(timeout=90)
        except Exception as e:
            print("BRIDGE: auto-enter wave failed:", e)
            try:
                from . import blog

                blog.event("mb_wave_enter_fail", reason=str(e))
            except Exception:
                pass
    return proc


def start_rtw(extra_args=None, windowed=False):
    """Launch RomeTW.

    Default matches everyday play (no -ne → fullscreen as in preferences).
    Pass windowed=True only for agent automation; never rewrite preferences.
    """
    if not os.path.isfile(config.RTW_EXE):
        raise RuntimeError("RTW exe missing: %s" % config.RTW_EXE)
    args = [config.RTW_EXE]
    if windowed:
        args.extend(["-ne", "-show_err"])
    if extra_args:
        args.extend(extra_args)
    return subprocess.Popen(args, cwd=config.RTW_ROOT, close_fds=True)


def start_rtw_windowed(extra_args=None):
    """Explicit windowed launch (-ne on CLI only)."""
    return start_rtw(extra_args=extra_args, windowed=True)


def process_running(name_substr):
    """True if a process image name contains name_substr (case-insensitive).

    Uses Toolhelp snapshot — cheaper than spawning tasklist every poll.
    """
    import ctypes
    import ctypes.wintypes as wt

    TH32CS_SNAPPROCESS = 0x00000002
    kernel32 = ctypes.windll.kernel32

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wt.DWORD),
            ("cntUsage", wt.DWORD),
            ("th32ProcessID", wt.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wt.DWORD),
            ("cntThreads", wt.DWORD),
            ("th32ParentProcessID", wt.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wt.DWORD),
            ("szExeFile", wt.WCHAR * 260),
        ]

    want = name_substr.lower()
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == ctypes.c_void_p(-1).value or snap == -1:
        return False
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not kernel32.Process32FirstW(snap, ctypes.byref(entry)):
            return False
        while True:
            if want in entry.szExeFile.lower():
                return True
            if not kernel32.Process32NextW(snap, ctypes.byref(entry)):
                break
        return False
    finally:
        kernel32.CloseHandle(snap)


def wait_for_process(image_name, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if process_running(image_name):
            return True
        time.sleep(0.5)
    return False
