"""Detect RTW pre-battle scroll by matching on-screen eventpic fingerprints.

Chosen signal (most reliable without memory RE):
  the pre-battle scroll embeds large faction eventpics such as
  data/ui/*/eventpics/prebattle_attack.tga (400x128). Those pixels are
  unique enough to find with a coarse RGB fingerprint on a desktop grab.
"""
from __future__ import print_function

import glob
import os
import time

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
    # Prefer the common land-attack art; skip naval-only if many.
    paths = [p for p in paths if "naval" not in os.path.basename(p).lower()]
    return sorted(set(paths))


def build_fingerprints(step=8, limit=12):
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


def _screen_bmp_to_rows(path):
    data = open(path, "rb").read()
    # BMP we write: BITMAPFILEHEADER(14) + BITMAPINFOHEADER(40) + top-down 24-bit
    if data[:2] != b"BM":
        raise ValueError("not BMP")
    off = int.from_bytes(data[10:14], "little")
    w = int.from_bytes(data[18:22], "little", signed=True)
    h = int.from_bytes(data[22:26], "little", signed=True)
    top_down = h < 0
    h = abs(h)
    bpp = int.from_bytes(data[28:30], "little")
    if bpp != 24:
        raise ValueError("need 24-bit BMP")
    row_size = ((w * 3 + 3) & ~3)
    rows = []
    for y in range(h):
        src_y = y if top_down else (h - 1 - y)
        start = off + src_y * row_size
        rows.append(data[start : start + w * 3])
    return w, h, rows


def _score_at(screen_rows, sw, sh, fp, x, y):
    step = fp["step"]
    ow, oh = fp["ow"], fp["oh"]
    # Compare fingerprint against screen block of size fp['w'] x fp['h']
    if x + fp["w"] > sw or y + fp["h"] > sh:
        return 1e9
    err = 0
    n = 0
    for oy in range(oh):
        for ox in range(ow):
            sx = x + ox * step + step // 2
            sy = y + oy * step + step // 2
            if sx >= sw or sy >= sh:
                continue
            b, g, r = screen_rows[sy][sx * 3 : sx * 3 + 3]
            tr, tg, tb = fp["finger"][oy * ow + ox]
            err += abs(r - tr) + abs(g - tg) + abs(b - tb)
            n += 1
    return err / max(1, n)


def find_prebattle_on_screen(fingerprints, bmp_path, stride=16, max_avg_err=40):
    sw, sh, rows = _screen_bmp_to_rows(bmp_path)
    best = None
    for fp in fingerprints:
        # Eventpics sit in the upper/mid area of the scroll — search broadly.
        for y in range(0, max(1, sh - fp["h"]), stride):
            for x in range(0, max(1, sw - fp["w"]), stride):
                score = _score_at(rows, sw, sh, fp, x, y)
                if best is None or score < best["score"]:
                    best = {
                        "score": score,
                        "x": x,
                        "y": y,
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


def poll_prebattle(fingerprints, interval=0.75, shots_dir=None):
    shots_dir = shots_dir or os.path.join(config.REPO_ROOT, "out", "bridge_shots")
    os.makedirs(shots_dir, exist_ok=True)
    path = os.path.join(shots_dir, "live.bmp")
    win_input.screenshot_window_bmp(path)
    return find_prebattle_on_screen(fingerprints, path)


# Approx Begin-Battle button cluster on 1920x1080 with the scroll centered.
# Tuned later from real shots; used only as a click-hit heuristic.
def begin_battle_hitbox(screen_w, screen_h, match):
    """Return (x0,y0,x1,y1) guess for the Begin Battle button."""
    # Buttons sit under the eventpic on the scroll, toward the right.
    if match and match.get("detected"):
        x0 = match["x"] + match["tw"] - 220
        y0 = match["y"] + match["th"] + 80
        return (x0, y0, x0 + 200, y0 + 40)
    # Fallback: lower-middle of the screen (Org: buttons lower-right of scroll).
    cx, cy = screen_w // 2, int(screen_h * 0.72)
    return (cx + 40, cy, cx + 240, cy + 48)


def point_in_box(x, y, box):
    x0, y0, x1, y1 = box
    return x0 <= x <= x1 and y0 <= y <= y1
