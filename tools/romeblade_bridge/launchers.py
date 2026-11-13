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
    "play mount",
    "graj w",
    "play mount&blade",
)
# Image name filter — never match Cursor / RomeAndBlade title windows.
_MB_EXE_SUBSTR = "mount&blade"


def _mb_owned_windows():
    """Windows belonging to mount&blade.exe only (not title-substring matches)."""
    from . import win_input

    return win_input.find_windows_for_exe(_MB_EXE_SUBSTR, visible_only=False)


def _click_play_on_hwnd(hwnd, title):
    from . import win_input

    btn, btn_text = win_input.find_button_hwnd(hwnd, _LAUNCHER_PLAY_NEEDLES)
    win_input.focus_window(hwnd)
    time.sleep(0.25)
    if btn:
        # Triple attempt: BM_CLICK, physical click on button, Enter (default btn).
        try:
            win_input.bm_click(btn)
        except Exception:
            pass
        time.sleep(0.15)
        win_input.click_control_center(btn, pause=0.2)
        time.sleep(0.15)
        win_input.tap_vk(win_input.VK_RETURN, pause=0.3)
        return btn_text or "Play"
    # No enumerated button (odd SkinMagic theme) — Enter + center-ish click.
    w, h = win_input.window_client_size(hwnd)
    if w > 0 and h > 0:
        # Play is typically mid-lower on the small launcher dialog.
        win_input.click_window_client_frac(hwnd, 0.50, 0.62, pause=0.25)
        win_input.click_window_client_frac(hwnd, 0.50, 0.72, pause=0.25)
    win_input.tap_vk(win_input.VK_RETURN, pause=0.3)
    return "(fallback Enter/frac)"


def dismiss_mb_launcher(timeout=90):
    """Click SkinMagic launcher Play on a mount&blade.exe-owned window.

    Does not kill processes. Returns True if Play clicked or game already up.
    """
    from . import blog
    from . import win_input

    t0 = time.time()
    while time.time() - t0 < timeout:
        wins = _mb_owned_windows()
        for hwnd, title, pid, exe in wins:
            btn, _ = win_input.find_button_hwnd(hwnd, _LAUNCHER_PLAY_NEEDLES)
            w, h = win_input.window_client_size(hwnd)
            if btn:
                label = _click_play_on_hwnd(hwnd, title)
                print(
                    "BRIDGE: launcher Play on pid=%s '%s' via %s"
                    % (pid, title, label.replace("&&", "&"))
                )
                blog.event(
                    "mb_launcher_play",
                    button=label,
                    title=title,
                    pid=pid,
                    w=w,
                    h=h,
                )
                return True
            # Game DirectX window: large client, no Win32 Play button.
            if w >= 640 and h >= 480 and user32_is_visible(hwnd):
                print(
                    "BRIDGE: M&B game window already up pid=%s %dx%d '%s'"
                    % (pid, w, h, title)
                )
                blog.event(
                    "mb_launcher_skip",
                    reason="game_window",
                    w=w,
                    h=h,
                    pid=pid,
                    title=title,
                )
                return True
        time.sleep(0.4)
    print("BRIDGE: M&B launcher Play not found (no mount&blade.exe window)")
    blog.event("mb_launcher_fail", reason="no_mb_window")
    return False


def user32_is_visible(hwnd):
    from . import win_input

    return bool(win_input.user32.IsWindowVisible(hwnd))


def wait_mb_game_window(timeout=120):
    """Wait until mount&blade.exe owns a large window without a Play button."""
    from . import win_input

    t0 = time.time()
    while time.time() - t0 < timeout:
        for hwnd, title, pid, exe in _mb_owned_windows():
            btn, _ = win_input.find_button_hwnd(hwnd, _LAUNCHER_PLAY_NEEDLES)
            w, h = win_input.window_client_size(hwnd)
            if btn is None and w >= 640 and h >= 480:
                return hwnd, title, w, h, pid
        time.sleep(0.5)
    return None, None, 0, 0, 0


def enter_wave_from_main_menu(timeout=120):
    """Launcher Play → wait for game → New Game → Wave Battle (menu INIT).

    Windows are resolved by process image mount&blade.exe only — never by the
    substring 'Blade' (that matched the Cursor 'RomeAndBlade' window and left
    the real launcher sitting idle). Does not kill processes.
    """
    from . import blog
    from . import win_input

    # 1.011 has no CLI to skip launcher or jump into a mission — only
    # HKCU\\...\\last_module + SkinMagic Play, then in-game New Game.
    if not dismiss_mb_launcher(timeout=min(90, timeout)):
        blog.event("mb_wave_enter_fail", reason="no_launcher")
        return False

    hwnd, title, w, h, pid = wait_mb_game_window(timeout=timeout)
    if not hwnd:
        print("BRIDGE: M&B game window not found after launcher")
        blog.event("mb_wave_enter_fail", reason="no_game_window")
        return False
    print(
        "BRIDGE: M&B game window pid=%s '%s' %dx%d - clicking New Game"
        % (pid, title, w, h)
    )
    blog.event("mb_game_window", title=title, w=w, h=h, pid=pid)
    win_input.focus_window(hwnd)
    time.sleep(3.0)
    for fy in (0.42, 0.48, 0.36, 0.52):
        x, y = win_input.click_window_client_frac(hwnd, 0.5, fy, pause=0.7)
        print("BRIDGE: click New Game candidate @ %d,%d (fy=%.2f)" % (x, y, fy))
    blog.event("mb_wave_enter_clicked", pid=pid)
    return True


def start_mb(module_name=None, enter_wave=True):
    """Set last_module, start mount&blade.exe (not runme), dismiss launcher, Wave.

    CLI note (1.011 on this disk): no working -m / mission switch in the exe.
    Module comes from registry last_module; SkinMagic launcher still appears.
    """
    module_name = module_name or config.MB_MODULE
    set_mb_module(module_name)
    if not os.path.isfile(config.MB_EXE):
        raise RuntimeError("M&B exe missing: %s" % config.MB_EXE)

    from . import blog

    owned = _mb_owned_windows()
    if owned:
        print(
            "BRIDGE: mount&blade.exe already has %d window(s) - reuse, no kill"
            % len(owned)
        )
        blog.event("mb_reuse_windows", count=len(owned))
        proc = None
    elif process_running(_MB_EXE_SUBSTR):
        # Process without a usable top-level window — still do not kill; launch
        # a fresh exe so the user gets a launcher we can click (second instance
        # is better than clicking Cursor by mistake).
        print("BRIDGE: mount&blade.exe running without window - starting another")
        blog.event("mb_start_extra_instance", reason="no_window")
        proc = subprocess.Popen(
            [config.MB_EXE],
            cwd=config.MB_ROOT,
            close_fds=True,
        )
    else:
        proc = subprocess.Popen(
            [config.MB_EXE],
            cwd=config.MB_ROOT,
            close_fds=True,
        )
        blog.event("mb_exe_started", module=module_name)
    if enter_wave:
        try:
            enter_wave_from_main_menu(timeout=120)
        except Exception as e:
            print("BRIDGE: auto-enter wave failed:", e)
            try:
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
