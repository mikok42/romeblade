#!/usr/bin/env python3
"""Convert Rome: Total War map base (TGA/HGT + descr_regions) → M&B map.txt + settlements.json."""
from __future__ import annotations

import argparse
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# M&B terrain codes
T_SEA, T_PLAIN, T_STEPPE, T_SNOW, T_DESERT, T_FOREST, T_MOUNTAIN = 0, 1, 2, 3, 4, 8, 10


def read_tga(path: Path) -> tuple[int, int, list[tuple[int, int, int]]]:
    data = path.read_bytes()
    if len(data) < 18:
        raise ValueError(f"TGA too small: {path}")
    w, h = struct.unpack_from("<HH", data, 12)
    bpp = data[16]
    if bpp not in (24, 32):
        raise ValueError(f"Unsupported TGA bpp={bpp} in {path}")
    id_len = data[0]
    pixel_offset = 18 + id_len
    stride = bpp // 8
    pixels: list[tuple[int, int, int]] = []
    # TGA bottom-up unless descriptor bit 5 set
    top_down = bool(data[17] & 0x20)
    raw = data[pixel_offset : pixel_offset + w * h * stride]
    rows = []
    for y in range(h):
        row = []
        for x in range(w):
            i = (y * w + x) * stride
            b, g, r = raw[i], raw[i + 1], raw[i + 2]
            row.append((r, g, b))
        rows.append(row)
    if not top_down:
        rows.reverse()
    for row in rows:
        pixels.extend(row)
    return w, h, pixels


def read_hgt_floats(path: Path, w: int, h: int) -> list[float]:
    raw = path.read_bytes()
    need = w * h * 4
    if len(raw) < need:
        # try int16
        need16 = w * h * 2
        if len(raw) >= need16:
            vals = list(struct.unpack_from(f"<{w * h}h", raw, 0))
            return [v / 100.0 for v in vals]
        raise ValueError(f"HGT too small: {path} size={len(raw)} need={need}")
    return list(struct.unpack_from(f"<{w * h}f", raw, 0))


def parse_descr_regions(path: Path) -> list[dict]:
    lines = path.read_text(encoding="latin-1").splitlines()
    regions: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith(";"):
            i += 1
            continue
        # region id line (no spaces typically)
        if " " in line and "\t" not in line:
            i += 1
            continue
        name = line.split()[0] if line.split() else line
        block = [name]
        i += 1
        while i < len(lines) and len(block) < 8:
            s = lines[i].strip()
            if not s or s.startswith(";"):
                i += 1
                continue
            block.append(s)
            i += 1
        if len(block) < 5:
            continue
        rgb = [int(x) for x in block[4].replace(",", " ").split() if x.isdigit()]
        if len(rgb) < 3:
            continue
        regions.append(
            {
                "region": block[0],
                "settlement": block[1].split()[0],
                "faction": block[2].split()[0],
                "rebel": block[3].split()[0] if len(block) > 3 else "",
                "rgb": rgb[:3],
            }
        )
    return regions


def parse_descr_terrain(path: Path) -> tuple[int, int]:
    w = h = None
    if not path.exists():
        return 255, 156
    for line in path.read_text(encoding="latin-1").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[0] == "width" and parts[-1].isdigit():
            w = int(parts[-1])
        elif len(parts) >= 2 and parts[0] == "height" and parts[-1].isdigit():
            h = int(parts[-1])
    return w or 255, h or 156


def ground_to_terrain(rgb: tuple[int, int, int], height: float, climate_rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    # RTW ground_types: deep water often dark blue/black; mountains bright
    if height < -50 or (b > r + 40 and b > g + 20 and b < 80 and r < 40):
        return T_SEA
    if height < 5 and r < 30 and g < 40 and b < 60:
        return T_SEA
    if height > 1800 or (r > 160 and g > 160 and b > 160 and height > 800):
        return T_MOUNTAIN
    cr, cg, cb = climate_rgb
    # rough climate heuristics
    if cb > 180 and cg > 180 and cr > 180 and height > 400:
        return T_SNOW
    if cr > 180 and cg > 140 and cb < 100:
        return T_DESERT
    if g > r + 30 and g > b + 20 and height > 100:
        return T_FOREST
    if cr > 150 and cg > 120 and cb < 120:
        return T_STEPPE
    return T_PLAIN


def downsample_grid(
    src_w: int,
    src_h: int,
    heights: list[float],
    ground: list[tuple[int, int, int]],
    climate: list[tuple[int, int, int]],
    max_edge: int = 140,
) -> tuple[int, int, list[float], list[tuple[int, int, int]], list[tuple[int, int, int]]]:
    scale = max(src_w, src_h) / float(max_edge)
    if scale <= 1.0:
        return src_w, src_h, heights, ground, climate
    dw = max(8, int(round(src_w / scale)))
    dh = max(8, int(round(src_h / scale)))
    nh, ng, nc = [], [], []
    for y in range(dh):
        for x in range(dw):
            sx = min(src_w - 1, int(x * (src_w - 1) / (dw - 1)))
            sy = min(src_h - 1, int(y * (src_h - 1) / (dh - 1)))
            i = sy * src_w + sx
            nh.append(heights[i])
            ng.append(ground[i])
            nc.append(climate[i])
    return dw, dh, nh, ng, nc


def build_mesh(
    w: int,
    h: int,
    heights: list[float],
    ground: list[tuple[int, int, int]],
    climate: list[tuple[int, int, int]],
    span_x: float = 210.0,
    span_y: float = 130.0,
) -> tuple[list, list]:
    # normalize heights to M&B-ish z
    finite = [v for v in heights if math.isfinite(v)]
    lo = min(finite) if finite else 0.0
    hi = max(finite) if finite else 1.0
    mid = (lo + hi) * 0.5
    scale_z = 25.0 / max(hi - lo, 1.0)

    verts = []
    for y in range(h):
        for x in range(w):
            i = y * w + x
            px = (x / (w - 1) - 0.5) * span_x
            py = (0.5 - y / (h - 1)) * span_y  # north-up
            pz = (heights[i] - mid) * scale_z
            verts.append((px, py, pz))

    faces = []
    for y in range(h - 1):
        for x in range(w - 1):
            i = y * w + x
            v00, v10, v01, v11 = i, i + 1, i + w, i + w + 1
            avg_h = (heights[v00] + heights[v10] + heights[v01] + heights[v11]) / 4.0
            g = ground[i]
            c = climate[i]
            t = ground_to_terrain(g, avg_h, c)
            faces.append((v00, v10, v11, t))
            faces.append((v00, v11, v01, t))
    return verts, faces


def settlements_from_regions(
    regions: list[dict],
    regions_w: int,
    regions_h: int,
    region_pixels: list[tuple[int, int, int]],
    span_x: float,
    span_y: float,
) -> list[dict]:
    # centroid of each region colour
    sums: dict[tuple[int, int, int], list] = {}
    for y in range(regions_h):
        for x in range(regions_w):
            rgb = region_pixels[y * regions_w + x]
            if rgb == (0, 0, 0):
                continue
            bucket = sums.setdefault(rgb, [0, 0, 0])
            bucket[0] += x
            bucket[1] += y
            bucket[2] += 1
    by_rgb = {tuple(r["rgb"]): r for r in regions}
    out = []
    for rgb, (sx, sy, n) in sums.items():
        meta = by_rgb.get(rgb)
        if not meta or n <= 0:
            continue
        cx = sx / n
        cy = sy / n
        px = (cx / max(regions_w - 1, 1) - 0.5) * span_x
        py = (0.5 - cy / max(regions_h - 1, 1)) * span_y
        out.append(
            {
                "id": meta["settlement"].lower(),
                "name": meta["settlement"].replace("_", " "),
                "region": meta["region"],
                "faction": meta["faction"],
                "x": round(px, 3),
                "y": round(py, 3),
                "rgb": list(rgb),
            }
        )
    out.sort(key=lambda s: s["name"])
    return out


def convert_base(base: Path, out_dir: Path, max_edge: int = 140) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    heights_tga = base / "map_heights.tga"
    ground_tga = base / "map_ground_types.tga"
    climate_tga = base / "map_climates.tga"
    regions_tga = base / "map_regions.tga"
    hgt = base / "map_heights.hgt"
    descr_regions = base / "descr_regions.txt"
    descr_terrain = base / "descr_terrain.txt"

    tw, th, _ = read_tga(heights_tga)
    gw, gh, ground = read_tga(ground_tga)
    cw, ch, climate = read_tga(climate_tga)
    if (gw, gh) != (tw, th) or (cw, ch) != (tw, th):
        raise ValueError("TGA dimension mismatch between heights/ground/climates")

    if hgt.exists():
        heights = read_hgt_floats(hgt, tw, th)
    else:
        # fallback: luminance of heights TGA
        _, _, hp = read_tga(heights_tga)
        heights = [float(r) for r, g, b in hp]

    tile_w, tile_h = parse_descr_terrain(descr_terrain)
    rw, rh, region_pixels = read_tga(regions_tga)
    regions = parse_descr_regions(descr_regions) if descr_regions.exists() else []

    dw, dh, heights_d, ground_d, climate_d = downsample_grid(
        tw, th, heights, ground, climate, max_edge=max_edge
    )
    span_x, span_y = 210.0, 210.0 * (dh / dw)
    verts, faces = build_mesh(dw, dh, heights_d, ground_d, climate_d, span_x, span_y)
    settlements = settlements_from_regions(regions, rw, rh, region_pixels, span_x, span_y)

    map_path = out_dir / "map.txt"
    with map_path.open("w", encoding="ascii", newline="\n") as f:
        f.write(f"{len(verts)}\n")
        for x, y, z in verts:
            f.write(f"{x:.6f} {y:.6f} {z:.6f}\n")
        f.write(f"{len(faces)}\n")
        for a, b, c, t in faces:
            f.write(f"{a} {b} {c} {t}\n")
    (out_dir / "settlements.json").write_text(
        json.dumps(settlements, indent=2), encoding="utf-8"
    )
    summary = {
        "source": str(base),
        "src_tga": [tw, th],
        "tile": [tile_w, tile_h],
        "downsampled": [dw, dh],
        "verts": len(verts),
        "faces": len(faces),
        "settlements": len(settlements),
        "map": str(map_path),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def self_test(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / "base"
    base.mkdir(parents=True, exist_ok=True)
    w, h = 32, 20
    # minimal TGA writer
    def write_tga(path: Path, w: int, h: int, pixel_fn):
        hdr = bytearray(18)
        hdr[2] = 2  # uncompressed true-color
        struct.pack_into("<HH", hdr, 12, w, h)
        hdr[16] = 24
        hdr[17] = 0x20  # top-down
        body = bytearray()
        for y in range(h):
            for x in range(w):
                r, g, b = pixel_fn(x, y)
                body.extend([b, g, r])
        path.write_bytes(bytes(hdr) + body)

    def height_px(x, y):
        v = int(40 + 80 * (x / w) + 20 * (y / h))
        return (v, v, v)

    def ground_px(x, y):
        if y < 3:
            return (10, 10, 80)  # sea-ish
        if y > h - 3:
            return (200, 200, 200)
        return (40, 120, 40)

    def climate_px(x, y):
        if y > h - 3:
            return (220, 220, 220)
        if y < 5:
            return (200, 160, 60)
        return (80, 140, 80)

    def region_px(x, y):
        if x < w // 2:
            return (232, 41, 198)
        return (58, 177, 95)

    write_tga(base / "map_heights.tga", w, h, height_px)
    write_tga(base / "map_ground_types.tga", w, h, ground_px)
    write_tga(base / "map_climates.tga", w, h, climate_px)
    write_tga(base / "map_regions.tga", w, h, region_px)
    # float heights
    heights = []
    for y in range(h):
        for x in range(w):
            heights.append(-200.0 if y < 3 else 100.0 + x * 10 + y)
    (base / "map_heights.hgt").write_bytes(struct.pack(f"<{w * h}f", *heights))
    (base / "descr_terrain.txt").write_text(
        "dimensions\n{\n\twidth  16\n\theight  10\n}\n", encoding="ascii"
    )
    (base / "descr_regions.txt").write_text(
        ";\nTest_West\n\tWestport\n\tromans_julii\n\tRebels\n\t232 41 198\n\tgrain\n\t5\n\t5\n"
        "Test_East\n\tEastfort\n\tgauls\n\tRebels\n\t58 177 95\n\ttimber\n\t5\n\t3\n",
        encoding="ascii",
    )
    summary = convert_base(base, out_dir / "out", max_edge=24)
    assert summary["verts"] > 0 and summary["faces"] > 0
    assert summary["settlements"] >= 1
    print("self-test ok", summary)


def main() -> int:
    ap = argparse.ArgumentParser(description="RTW map base → M&B map.txt")
    ap.add_argument("base", nargs="?", type=Path, help="Path to RTW data/world/maps/base")
    ap.add_argument("--out", type=Path, default=ROOT / "out" / "from-rome")
    ap.add_argument("--max-edge", type=int, default=140)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test(ROOT / "out" / "self-test")
        return 0
    if not args.base:
        paths = ROOT / "paths.json"
        if paths.exists():
            cfg = json.loads(paths.read_text(encoding="utf-8"))
            args.base = Path(cfg["rome_total_war"]["map_base"])
        else:
            ap.error("base path required (or paths.json)")
    summary = convert_base(args.base, args.out, max_edge=args.max_edge)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
