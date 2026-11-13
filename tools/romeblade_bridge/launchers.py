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

# M&B 1.011 on this disk: no CLI to skip SkinMagic or enter a mission.
# Wave Battle entry is module menu INIT (New Game / Custom Battle) — user clicks
# Graj then Nowa gra. Bridge must NOT SendInput / BM_CLICK any M&B UI.


def set_mb_module(module_name):
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\MountAndBladeKeys")
    winreg.SetValueEx(key, "last_module", 0, winreg.REG_SZ, module_name)
    winreg.CloseKey(key)


def start_mb(module_name=None, enter_wave=False):
    """Set last_module and start mount&blade.exe. No UI clicking.

    enter_wave is ignored (kept for call-site compat). Wave Battle is entered
    only via RomeBladeRTS menu INIT after the user clicks Graj + Nowa gra.
    """
    module_name = module_name or config.MB_MODULE
    set_mb_module(module_name)
    if not os.path.isfile(config.MB_EXE):
        raise RuntimeError("M&B exe missing: %s" % config.MB_EXE)

    from . import blog

    if process_running("mount&blade"):
        print(
            "BRIDGE: mount&blade.exe already running - not starting another, "
            "not clicking UI. Close its windows if you need a fresh RomeBladeRTS launch."
        )
        blog.event("mb_already_running", module=module_name)
        return None

    proc = subprocess.Popen(
        [config.MB_EXE],
        cwd=config.MB_ROOT,
        close_fds=True,
    )
    blog.event("mb_exe_started", module=module_name)
    print(
        "BRIDGE: started %s (module=%s). Manual: Graj -> Nowa gra -> Wave Battle."
        % (config.MB_EXE, module_name)
    )
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
