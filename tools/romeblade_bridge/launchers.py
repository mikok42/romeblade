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


# Launcher Play button labels (EN + PL). language.txt on this machine is "pl".
_LAUNCHER_PLAY_NEEDLES = (
    "graj w mount",
    "graj",
    "play mount",
    "play mount&blade",
)


def _mb_top_windows():
    from . import win_input

    wins = win_input.find_windows("Mount") or win_input.find_windows("Blade")
    return wins or []


def dismiss_mb_launcher(timeout=60):
    """Click the SkinMagic launcher Play button (EN/PL). Does not kill processes.

    Returns True if Play was clicked (or launcher already gone / no Play button
    because the game window is already up).
    """
    from . import blog
    from . import win_input

    t0 = time.time()
    while time.time() - t0 < timeout:
        for hwnd, title in _mb_top_windows():
            btn, btn_text = win_input.find_button_hwnd(hwnd, _LAUNCHER_PLAY_NEEDLES)
            if not btn:
                # Already past launcher: large client area, no Play button.
                w, h = win_input.window_client_size(hwnd)
                if w >= 800 and h >= 600:
                    print("BRIDGE: M&B game window already up %dx%d" % (w, h))
                    blog.event("mb_launcher_skip", reason="game_window", w=w, h=h)
                    return True
                continue
            win_input.focus_window(hwnd)
            time.sleep(0.3)
            try:
                win_input.bm_click(btn)
            except Exception:
                win_input.click_control_center(btn)
            print(
                "BRIDGE: launcher Play clicked (%s) on '%s'"
                % (btn_text.replace("&&", "&"), title)
            )
            blog.event("mb_launcher_play", button=btn_text, title=title)
            return True
        time.sleep(0.4)
    print("BRIDGE: M&B launcher Play not found")
    blog.event("mb_launcher_fail", reason="no_play_button")
    return False


def wait_mb_game_window(timeout=120):
    """Wait until the DirectX game window is up (launcher dialog gone)."""
    from . import win_input

    t0 = time.time()
    while time.time() - t0 < timeout:
        for hwnd, title in _mb_top_windows():
            btn, _ = win_input.find_button_hwnd(hwnd, _LAUNCHER_PLAY_NEEDLES)
            w, h = win_input.window_client_size(hwnd)
            # Game window: no Play button, reasonably large (windowed or FS).
            if btn is None and (w >= 640 and h >= 480):
                return hwnd, title, w, h
        time.sleep(0.5)
    return None, None, 0, 0


def enter_wave_from_main_menu(timeout=120):
    """Launcher Play → wait for game → New Game → Wave Battle (menu INIT).

    Does not kill processes; no-ops if windows missing.
    """
    from . import blog
    from . import win_input

    if not dismiss_mb_launcher(timeout=min(60, timeout)):
        # Last resort: Enter often activates the default Play button.
        hwnd = win_input.wait_for_window("Mount", timeout=5) or win_input.wait_for_window(
            "Blade", timeout=3
        )
        if hwnd:
            win_input.focus_window(hwnd)
            win_input.tap_vk(win_input.VK_RETURN, pause=0.5)
            blog.event("mb_launcher_enter_fallback")
            print("BRIDGE: launcher fallback VK_RETURN")
        else:
            blog.event("mb_wave_enter_fail", reason="no_launcher")
            return False

    hwnd, title, w, h = wait_mb_game_window(timeout=timeout)
    if not hwnd:
        print("BRIDGE: M&B game window not found after launcher")
        blog.event("mb_wave_enter_fail", reason="no_game_window")
        return False
    print("BRIDGE: M&B game window '%s' %dx%d — clicking New Game" % (title, w, h))
    blog.event("mb_game_window", title=title, w=w, h=h)
    win_input.focus_window(hwnd)
    # Main menu fade-in after load.
    time.sleep(3.0)
    # New Game is the top main-menu button (center column).
    for fy in (0.42, 0.48, 0.36, 0.52):
        x, y = win_input.click_window_client_frac(hwnd, 0.5, fy, pause=0.7)
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
        # Direct exe (not runme.exe). last_module already set; launcher still
        # appears but Play will load RomeBladeRTS without touching Native.
        proc = subprocess.Popen(
            [config.MB_EXE],
            cwd=config.MB_ROOT,
            close_fds=True,
        )
    if enter_wave:
        try:
            enter_wave_from_main_menu(timeout=120)
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
