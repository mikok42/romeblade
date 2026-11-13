"""Minimal Win32 window focus + keystroke helpers (ctypes only)."""
from __future__ import print_function

import ctypes
import ctypes.wintypes as wt
import time

user32 = ctypes.windll.user32

VK_ESCAPE = 0x1B
VK_RETURN = 0x0D
VK_DOWN = 0x28
VK_UP = 0x26
VK_TAB = 0x09
VK_MENU = 0x12  # Alt
VK_OEM_3 = 0xC0  # ~ tilde / console on many layouts

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wt.WORD),
        ("wScan", wt.WORD),
        ("dwFlags", wt.DWORD),
        ("time", wt.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("union", INPUT_UNION)]


def _send_vk(vk, up=False):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki = KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP if up else 0, 0, None)
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def tap_vk(vk, hold=0.05, pause=0.15):
    _send_vk(vk, up=False)
    time.sleep(hold)
    _send_vk(vk, up=True)
    time.sleep(pause)


def tap_text_unicode(text, pause=0.03):
    """Type ASCII via VkKeyScanA (US-ish). Good enough for save names."""
    for ch in text:
        vk = user32.VkKeyScanA(ctypes.c_char(ch.encode("ascii")))
        if vk == -1:
            continue
        lo = vk & 0xFF
        shift = bool(vk & 0x100)
        if shift:
            _send_vk(0x10, up=False)  # VK_SHIFT
        tap_vk(lo, hold=0.02, pause=pause)
        if shift:
            _send_vk(0x10, up=True)


EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)


def find_windows(title_substr):
    wanted = title_substr.lower()
    found = []

    def cb(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        title = buf.value
        if wanted in title.lower():
            found.append((hwnd, title))
        return True

    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return found


def focus_window(hwnd):
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)


MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def click_screen(x, y, pause=0.2):
    """Left-click at absolute screen coordinates via SetCursorPos + mouse_event."""
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(pause)


def click_window_client_frac(hwnd, fx, fy, pause=0.35):
    """Click inside hwnd's client area at fractional (fx, fy) in 0..1."""
    rect = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    pt = wt.POINT(int(rect.right * float(fx)), int(rect.bottom * float(fy)))
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    click_screen(pt.x, pt.y, pause=pause)
    return pt.x, pt.y


def wait_for_window(title_substr, timeout=90, poll=0.5):
    """Return first visible hwnd whose title contains title_substr, or None."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        found = find_windows(title_substr)
        if found:
            return found[0][0]
        time.sleep(poll)
    return None


BM_CLICK = 0x00F5


def window_title(hwnd):
    buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buf, 512)
    return buf.value


def window_class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def window_client_size(hwnd):
    rect = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    return int(rect.right), int(rect.bottom)


def enum_child_windows(hwnd):
    """Return [(child_hwnd, class_name, title), ...] for direct+nested children."""
    found = []

    def cb(child, _lparam):
        found.append((child, window_class(child), window_title(child)))
        return True

    user32.EnumChildWindows(hwnd, EnumWindowsProc(cb), 0)
    return found


def find_button_hwnd(parent, text_needles):
    """Find a child control whose title contains any needle (case-insensitive).

    M&B launcher stores labels with '&&' for a single '&' (SkinMagic).
    Prefer class names containing 'button', but accept any text match.
    """
    needles = [n.lower() for n in text_needles]
    fallback = (None, None)
    for child, cls, title in enum_child_windows(parent):
        if not title:
            continue
        norm = title.replace("&&", "&").lower()
        if not any(n in norm for n in needles):
            continue
        cls_l = (cls or "").lower()
        if "button" in cls_l:
            return child, title
        if fallback[0] is None:
            fallback = (child, title)
    return fallback


def bm_click(hwnd):
    """Send BM_CLICK to a Win32 button (works on the M&B SkinMagic launcher)."""
    user32.SendMessageW(hwnd, BM_CLICK, 0, 0)


def click_control_center(hwnd, pause=0.35):
    """Left-click the center of a control's window rect (screen coords)."""
    rect = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    x = (rect.left + rect.right) // 2
    y = (rect.top + rect.bottom) // 2
    click_screen(x, y, pause=pause)
    return x, y


def _bitmapinfo_topdown(width, height):
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wt.DWORD),
            ("biWidth", ctypes.c_long),
            ("biHeight", ctypes.c_long),
            ("biPlanes", wt.WORD),
            ("biBitCount", wt.WORD),
            ("biCompression", wt.DWORD),
            ("biSizeImage", wt.DWORD),
            ("biXPelsPerMeter", ctypes.c_long),
            ("biYPelsPerMeter", ctypes.c_long),
            ("biClrUsed", wt.DWORD),
            ("biClrImportant", wt.DWORD),
        ]

    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.biWidth = width
    bi.biHeight = -height  # top-down
    bi.biPlanes = 1
    bi.biBitCount = 24
    bi.biCompression = 0
    row = ((width * 3 + 3) & ~3)
    bi.biSizeImage = row * height
    return bi, row


def grab_screen_rgb(x=0, y=0, width=None, height=None):
    """GDI BitBlt a screen rectangle → (w, h, bytearray BGR rows padded).

    Prefer a center crop over the full desktop — full 2560×1440 grabs are costly.
    """
    gdi32 = ctypes.windll.gdi32
    sw = user32.GetSystemMetrics(0)
    sh = user32.GetSystemMetrics(1)
    if width is None:
        width = sw - x
    if height is None:
        height = sh - y
    width = max(1, min(int(width), sw - int(x)))
    height = max(1, min(int(height), sh - int(y)))
    x, y = int(x), int(y)

    hdc = user32.GetDC(0)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, width, height)
    gdi32.SelectObject(mem, bmp)
    gdi32.BitBlt(mem, 0, 0, width, height, hdc, x, y, 0x00CC0020)
    bi, row = _bitmapinfo_topdown(width, height)
    buf = ctypes.create_string_buffer(bi.biSizeImage)
    gdi32.GetDIBits(mem, bmp, 0, height, buf, ctypes.byref(bi), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(0, hdc)
    return width, height, bytearray(buf.raw), row, x, y


def screenshot_window_bmp(path, x=0, y=0, width=None, height=None):
    """Capture screen (full or crop) to BMP via GDI (no extra deps)."""
    w, h, pixels, row, _ox, _oy = grab_screen_rgb(x, y, width, height)
    bi, _row = _bitmapinfo_topdown(w, h)

    class BITMAPFILEHEADER(ctypes.Structure):
        _pack_ = 1
        _fields_ = [
            ("bfType", wt.WORD),
            ("bfSize", wt.DWORD),
            ("bfReserved1", wt.WORD),
            ("bfReserved2", wt.WORD),
            ("bfOffBits", wt.DWORD),
        ]

    bf = BITMAPFILEHEADER()
    bf.bfType = 0x4D42
    bf.bfOffBits = ctypes.sizeof(BITMAPFILEHEADER) + bi.biSize
    bf.bfSize = bf.bfOffBits + bi.biSizeImage
    with open(path, "wb") as f:
        f.write(ctypes.string_at(ctypes.byref(bf), ctypes.sizeof(bf)))
        f.write(ctypes.string_at(ctypes.byref(bi), bi.biSize))
        f.write(pixels)
    return path
