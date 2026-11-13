"""Minimal uncompressed TGA reader (RTW UI eventpics)."""
from __future__ import print_function

import struct


def load_tga(path):
    data = open(path, "rb").read()
    idlen, cmap_type, img_type = data[0], data[1], data[2]
    if cmap_type != 0 or img_type not in (2, 10):
        raise ValueError("unsupported TGA %s (type=%d cmap=%d)" % (path, img_type, cmap_type))
    w, h = struct.unpack_from("<HH", data, 12)
    bpp = data[16]
    if bpp not in (24, 32):
        raise ValueError("unsupported bpp %d in %s" % (bpp, path))
    offset = 18 + idlen
    if img_type == 10:
        raise ValueError("RLE TGA not supported: %s" % path)
    stride = w * (bpp // 8)
    raw = data[offset : offset + stride * h]
    # TGA is usually bottom-up; descriptor bit 5 = top-down
    top_down = bool(data[17] & 0x20)
    rows = []
    for y in range(h):
        src_y = y if top_down else (h - 1 - y)
        row = raw[src_y * stride : (src_y + 1) * stride]
        # BGR(A) -> RGB tuples subsampled later
        rows.append(row)
    return {"w": w, "h": h, "bpp": bpp, "rows": rows}


def downsample_rgb(rows, w, h, bpp, step):
    """Average to a small RGB fingerprint list."""
    px = bpp // 8
    out_w = max(1, w // step)
    out_h = max(1, h // step)
    finger = []
    for oy in range(out_h):
        for ox in range(out_w):
            x0, y0 = ox * step, oy * step
            r = g = b = n = 0
            for yy in range(y0, min(y0 + step, h)):
                row = rows[yy]
                for xx in range(x0, min(x0 + step, w)):
                    i = xx * px
                    b += row[i]
                    g += row[i + 1]
                    r += row[i + 2]
                    n += 1
            if n:
                finger.append((r // n, g // n, b // n))
    return out_w, out_h, finger
