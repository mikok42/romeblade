#!/usr/bin/env python3
"""Synthetic Mediterranean-ish M&B map.txt generator (offline; no game install required)."""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / "out"

# M&B face terrain codes (subset used by original engine)
TERRAIN_SEA = 0
TERRAIN_PLAIN = 1
TERRAIN_STEPPE = 2
TERRAIN_SNOW = 3
TERRAIN_DESERT = 4
TERRAIN_FOREST = 8
TERRAIN_MOUNTAIN = 10


def _height(nx: float, ny: float) -> float:
    """nx,ny in [0,1]; rough Med basin + Alps/Atlas hints."""
    # water bowl toward center-south
    basin = -6.0 + 14.0 * ((nx - 0.52) ** 2 + (ny - 0.42) ** 2)
    alps = 18.0 * math.exp(-((nx - 0.48) ** 2) / 0.01 - ((ny - 0.72) ** 2) / 0.004)
    atlas = 10.0 * math.exp(-((nx - 0.35) ** 2) / 0.02 - ((ny - 0.28) ** 2) / 0.008)
    anatolia = 8.0 * math.exp(-((nx - 0.72) ** 2) / 0.015 - ((ny - 0.58) ** 2) / 0.01)
    noise = 1.2 * math.sin(nx * 37.1) * math.cos(ny * 29.3)
    return basin + alps + atlas + anatolia + noise


def _terrain(h: float, nx: float, ny: float) -> int:
    if h < 0.35:
        return TERRAIN_SEA
    if h > 12.0:
        return TERRAIN_MOUNTAIN
    if ny > 0.78 and h > 4.0:
        return TERRAIN_SNOW
    if ny < 0.32 and h < 6.0:
        return TERRAIN_DESERT
    if 0.55 < nx < 0.7 and 0.45 < ny < 0.65 and h < 5.0:
        return TERRAIN_STEPPE
    if h > 3.5 and (math.sin(nx * 50) + math.cos(ny * 40)) > 0.6:
        return TERRAIN_FOREST
    return TERRAIN_PLAIN


def generate(cols: int = 140, rows: int = 110, span: float = 210.0) -> tuple[list, list, list]:
    """Return verts [(x,y,z)], faces [(i,j,k,terrain)], settlements list."""
    verts: list[tuple[float, float, float]] = []
    for r in range(rows):
        for c in range(cols):
            nx = c / (cols - 1)
            ny = r / (rows - 1)
            x = (nx - 0.5) * span
            y = (ny - 0.5) * span
            z = _height(nx, ny)
            verts.append((x, y, z))

    faces: list[tuple[int, int, int, int]] = []
    for r in range(rows - 1):
        for c in range(cols - 1):
            i = r * cols + c
            v00, v10, v01, v11 = i, i + 1, i + cols, i + cols + 1
            nx = (c + 0.5) / (cols - 1)
            ny = (r + 0.5) / (rows - 1)
            h = sum(verts[k][2] for k in (v00, v10, v01, v11)) / 4.0
            t = _terrain(h, nx, ny)
            faces.append((v00, v10, v11, t))
            faces.append((v00, v11, v01, t))

    settlements = [
        {"id": "rome", "name": "Rome", "x": 8.0, "y": 12.0, "faction": "romans_julii"},
        {"id": "carthage", "name": "Carthage", "x": -18.0, "y": -8.0, "faction": "carthage"},
        {"id": "athens", "name": "Athens", "x": 42.0, "y": 6.0, "faction": "greek_cities"},
        {"id": "alexandria", "name": "Alexandria", "x": 55.0, "y": -35.0, "faction": "egypt"},
        {"id": "massilia", "name": "Massilia", "x": -25.0, "y": 35.0, "faction": "gauls"},
    ]
    return verts, faces, settlements


def write_map_txt(path: Path, verts: list, faces: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii", newline="\n") as f:
        f.write(f"{len(verts)}\n")
        for x, y, z in verts:
            f.write(f"{x:.6f} {y:.6f} {z:.6f}\n")
        f.write(f"{len(faces)}\n")
        for a, b, c, t in faces:
            f.write(f"{a} {b} {c} {t}\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate synthetic RomeBlade map.txt")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--cols", type=int, default=140)
    ap.add_argument("--rows", type=int, default=110)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    verts, faces, settlements = generate(args.cols, args.rows)
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    map_path = out / "map.txt"
    write_map_txt(map_path, verts, faces)
    (out / "settlements.json").write_text(
        json.dumps(settlements, indent=2), encoding="utf-8"
    )
    summary = {
        "verts": len(verts),
        "faces": len(faces),
        "cols": args.cols,
        "rows": args.rows,
        "map": str(map_path),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"wrote {map_path} verts={len(verts)} faces={len(faces)}")
    if args.self_test:
        assert len(verts) == args.cols * args.rows
        assert len(faces) == (args.cols - 1) * (args.rows - 1) * 2
        assert map_path.stat().st_size > 1000
        print("self-test ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
