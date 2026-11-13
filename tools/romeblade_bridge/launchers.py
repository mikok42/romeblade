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


def start_mb(module_name=None):
    module_name = module_name or config.MB_MODULE
    set_mb_module(module_name)
    if not os.path.isfile(config.MB_EXE):
        raise RuntimeError("M&B exe missing: %s" % config.MB_EXE)
    return subprocess.Popen(
        [config.MB_EXE],
        cwd=config.MB_ROOT,
        close_fds=True,
    )


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
    # Lightweight check via tasklist (no psutil dependency).
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq %s" % name_substr],
            universal_newlines=True,
            errors="ignore",
        )
        return name_substr.lower() in out.lower() and "No tasks" not in out
    except Exception:
        return False


def wait_for_process(image_name, timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if process_running(image_name):
            return True
        time.sleep(0.5)
    return False
