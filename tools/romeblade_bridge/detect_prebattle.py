"""Detect RTW pre-battle scroll by matching on-screen eventpic fingerprints.

Chosen signal (most reliable without memory RE):
  the pre-battle scroll embeds large faction eventpics such as
  data/ui/*/eventpics/prebattle_attack.tga (400x128).

Performance: grab a center crop in memory (no BMP disk I/O), few templates,
coarse stride. Full-desktop GDI + dense search was multi-second and, with a
permanent WH_MOUSE_LL hook, made the cursor stutter.

Fullscreen note: exclusive DirectX may still yield a black GDI capture —
UNVERIFIED on desk.
"""
from __future__ import print_function

import glob
import os

from . import config
from . import tga
from . import win_input


def _collect_templates():
    patterns = [
        os.path.join(config.RTW_ROOT, r"data\ui\*\eventpics\prebattle_*.tga"),
    ]
    paths = []
    for pat in patterns:
        paths.extend(glob.glob(pat))
    paths = [p for p in paths if "naval" not in os.path.basename(p).lower()]
    # Prefer attack art first (most common land scroll).
    def key(p):
        b = os.path.basename(p).lower()
        return (0 if "attack" in b else 1, b)

    return sorted(set(paths), key=key)


def build_fingerprints(step=None, limit=None):
    step = config.DETECT_FP_STEP if step is None else step
    limit = config.DETECT_TEMPLATES if limit is None else limit
    fps = []
    for path in _collect_templates()[:limit]:
        try:
            img = tga.load_tga(path)
            ow, oh, finger = tga.downsample_rgb(
                img["rows"], img["w"], img["h"], img["bpp"], step
            )
            fps.append(
                {
                    "path": path,
                    "w": img["w"],
                    "h": img["h"],
                    "ow": ow,
                    "oh": oh,
                    "step": step,
                    "finger": finger,
                }
            )
        except Exception as e:
            print("template skip %s: %s" % (path, e))
    return fps


def _score_at_buf(pixels, row_bytes, cw, ch, fp, x, y):
    step = fp["step"]
    ow, oh = fp["ow"], fp["oh"]
    if x + fp["w"] > cw or y + fp["h"] > ch:
        return 1e9
    err = 0
    n = 0
    finger = fp["finger"]
    for oy in range(oh):
        for ox in range(ow):
            sx = x + ox * step + step // 2
            sy = y + oy * step + step // 2
            if sx >= cw or sy >= ch:
                continue
            o = sy * row_bytes + sx * 3
            b, g, r = pixels[o], pixels[o + 1], pixels[o + 2]
            tr, tg, tb = finger[oy * ow + ox]
            err += abs(r - tr) + abs(g - tg) + abs(b - tb)
            n += 1
    return err / max(1, n)


def find_prebattle_in_buffer(
    fingerprints,
    pixels,
    width,
    height,
    row_bytes,
    origin_x=0,
    origin_y=0,
    stride=None,
    max_avg_err=40,
):
    stride = config.DETECT_STRIDE if stride is None else stride
    best = None
    for fp in fingerprints:
        for y in range(0, max(1, height - fp["h"]), stride):
            for x in range(0, max(1, width - fp["w"]), stride):
                score = _score_at_buf(pixels, row_bytes, width, height, fp, x, y)
                if best is None or score < best["score"]:
                    best = {
                        "score": score,
                        "x": origin_x + x,
                        "y": origin_y + y,
                        "template": fp["path"],
                        "tw": fp["w"],
                        "th": fp["h"],
                    }
    if best and best["score"] <= max_avg_err:
        best["detected"] = True
    else:
        if best:
            best["detected"] = False
    return best


def _center_crop_rect(sw, sh, cw, ch):
    cw = min(cw, sw)
    ch = min(ch, sh)
    x = max(0, (sw - cw) // 2)
    y = max(0, (sh - ch) // 2)
    return x, y, cw, ch


def _buffer_luma_stats(pixels, width, height, row_bytes, sample=8):
    """Quick mean luma + black/bright fraction for GDI usefulness."""
    tot = 0
    n = 0
    black = 0
    bright = 0
    for y in range(0, height, sample):
        for x in range(0, width, sample):
            o = y * row_bytes + x * 3
            b, g, r = pixels[o], pixels[o + 1], pixels[o + 2]
            s = r + g + b
            tot += s
            n += 1
            if s < 24:
                black += 1
            if s > 600:
                bright += 1
    mean = float(tot) / max(1, n)
    return {
        "mean_rgb_sum": round(mean, 1),
        "black_frac": round(black / float(max(1, n)), 3),
        "bright_frac": round(bright / float(max(1, n)), 3),
        "samples": n,
    }


def classify_gdi_capture(stats):
    """Heuristic: exclusive FS often black; BitBlt of desktop-behind is bright wallpaper."""
    if stats["black_frac"] >= 0.85:
        return "black_likely_exclusive_fs"
    if stats["bright_frac"] >= 0.55 and stats["mean_rgb_sum"] >= 500:
        return "bright_likely_desktop_not_rtw"
    return "ok_or_unknown"


def poll_prebattle(fingerprints, shots_dir=None):
    """One detect pass: center crop in RAM, no BMP write."""
    import ctypes

    user32 = ctypes.windll.user32
    sw = user32.GetSystemMetrics(0)
    sh = user32.GetSystemMetrics(1)
    x, y, cw, ch = _center_crop_rect(
        sw, sh, config.DETECT_CROP_W, config.DETECT_CROP_H
    )
    w, h, pixels, row, ox, oy = win_input.grab_screen_rgb(x, y, cw, ch)
    stats = _buffer_luma_stats(pixels, w, h, row)
    gdi = classify_gdi_capture(stats)
    match = find_prebattle_in_buffer(
        fingerprints, pixels, w, h, row, origin_x=ox, origin_y=oy
    )
    if match is None:
        match = {"detected": False, "score": 1e9}
    match["gdi"] = gdi
    match["gdi_stats"] = stats
    match["crop"] = (ox, oy, w, h)
    return match


def poll_prebattle_legacy_full(fingerprints, shots_dir=None):
    """OLD path kept for offline before/after timing only."""
    shots_dir = shots_dir or os.path.join(config.REPO_ROOT, "out", "bridge_shots")
    os.makedirs(shots_dir, exist_ok=True)
    path = os.path.join(shots_dir, "live_legacy.bmp")
    win_input.screenshot_window_bmp(path)  # full desktop
    data = open(path, "rb").read()
    off = int.from_bytes(data[10:14], "little")
    w = int.from_bytes(data[18:22], "little", signed=True)
    h = abs(int.from_bytes(data[22:26], "little", signed=True))
    row = ((w * 3 + 3) & ~3)
    pixels = bytearray(data[off : off + row * h])
    # Legacy used stride 16 and up to 12 templates built by caller.
    return find_prebattle_in_buffer(
        fingerprints, pixels, w, h, row, origin_x=0, origin_y=0, stride=16
    )


def begin_battle_hitbox(screen_w, screen_h, match):
    """Return (x0,y0,x1,y1) guess for the Begin Battle button."""
    if (
        match
        and match.get("detected")
        and match.get("tw")
        and match.get("th")
    ):
        x0 = match["x"] + match["tw"] - 220
        y0 = match["y"] + match["th"] + 80
        return (x0, y0, x0 + 200, y0 + 40)
    # F5 / no template: lower-right of a centered scroll on 16:9.
    cx, cy = screen_w // 2, int(screen_h * 0.72)
    return (cx + 40, cy, cx + 240, cy + 48)


def point_in_box(x, y, box):
    x0, y0, x1, y1 = box
    return x0 <= x <= x1 and y0 <= y <= y1
