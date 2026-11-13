#!/usr/bin/env python3
"""Read / patch unit soldier counts in an uncompressed RTW 1.5 .sav.

Unit records embed the EDU type name as ASCII. Relative to the end of that
name the layout used by experiment E1 is:

  +28  marker bytes A0 42 (observed on army units)
  +30  u32 LE current soldiers
  +34  u32 LE full soldiers

Only records with 0 <= current <= full <= MAX_FULL are treated as units.
Writes never overwrite an existing path.
"""
from __future__ import print_function

import argparse
import os
import struct
import sys
from collections import Counter

MARKER = b"\xa0\x42"
CUR_OFF = 30
FULL_OFF = 34
MAX_FULL = 240


def _u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


def _put_u32(buf, off, value):
    struct.pack_into("<I", buf, off, value)


def find_units(data, unit_type=None):
    """Yield dicts: name, name_off, cur_off, full_off, current, full."""
    if unit_type is None:
        # Broad scan: find marker then walk back for a length-prefixed name.
        # For listing a specific type we search the name string (faster / exact).
        raise ValueError("unit_type is required for this scanner")

    name = unit_type.encode("ascii")
    start = 0
    while True:
        i = data.find(name, start)
        if i < 0:
            break
        end = i + len(name)
        start = i + 1
        if end + FULL_OFF + 4 > len(data):
            continue
        if bytes(data[end + 28 : end + 30]) != MARKER:
            continue
        # Length-prefixed name: u16 LE count includes the trailing NUL.
        if i < 2 or end >= len(data) or data[end] != 0:
            continue
        declared = struct.unpack_from("<H", data, i - 2)[0]
        if declared != len(name) + 1:
            continue
        current = _u32(data, end + CUR_OFF)
        full = _u32(data, end + FULL_OFF)
        if not (0 <= current <= full <= MAX_FULL and full > 0):
            continue
        yield {
            "name": unit_type,
            "name_off": i,
            "cur_off": end + CUR_OFF,
            "full_off": end + FULL_OFF,
            "current": current,
            "full": full,
        }


def list_units(path, unit_type):
    data = open(path, "rb").read()
    rows = list(find_units(data, unit_type))
    print("file=%s size=%d type=%r units=%d" % (path, len(data), unit_type, len(rows)))
    counts = Counter((r["current"], r["full"]) for r in rows)
    print("current/full histogram:")
    for (cur, ful), n in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        print("  %3d / %3d  x%d" % (cur, ful, n))
    for r in rows:
        print(
            "  @%d  current=%d full=%d  (cur_off=%d)"
            % (r["name_off"], r["current"], r["full"], r["cur_off"])
        )
    return rows


def set_current(src, dst, unit_type, new_current, dry_run=False):
    if new_current < 0 or new_current > MAX_FULL:
        raise SystemExit("new_current out of range 0..%d" % MAX_FULL)
    if os.path.exists(dst):
        raise SystemExit("refusing to overwrite existing file: %s" % dst)

    data = bytearray(open(src, "rb").read())
    rows = list(find_units(data, unit_type))
    if not rows:
        raise SystemExit("no matching units for %r in %s" % (unit_type, src))

    changes = []
    for r in rows:
        old = r["current"]
        if old == new_current:
            continue
        # Keep current <= full; clamp is a hard error so E1 stays honest.
        if new_current > r["full"]:
            raise SystemExit(
                "refusing current=%d > full=%d at name_off=%d"
                % (new_current, r["full"], r["name_off"])
            )
        changes.append((r["cur_off"], old, new_current, r["name_off"]))

    print(
        "matched=%d will_change=%d already=%d"
        % (len(rows), len(changes), len(rows) - len(changes))
    )
    for off, old, new, name_off in changes:
        print("  name@%d cur@%d %d -> %d" % (name_off, off, old, new))
        if not dry_run:
            _put_u32(data, off, new)

    if dry_run:
        print("dry-run: not writing")
        return changes

    # Write via temp in same folder then rename, still only creating dst.
    tmp = dst + ".tmp"
    if os.path.exists(tmp):
        raise SystemExit("temp path exists: %s" % tmp)
    with open(tmp, "wb") as f:
        f.write(data)
    os.rename(tmp, dst)
    print("wrote %s (%d bytes)" % (dst, len(data)))
    return changes


def diff_saves(a_path, b_path, context=0):
    a = open(a_path, "rb").read()
    b = open(b_path, "rb").read()
    if len(a) != len(b):
        print("LENGTH DIFFERS: %d vs %d" % (len(a), len(b)))
        return
    diffs = []
    i = 0
    n = len(a)
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        j = i
        while j < n and a[j] != b[j]:
            j += 1
        diffs.append((i, j, a[i:j], b[i:j]))
        i = j
    print("equal_length=%d changed_spans=%d changed_bytes=%d" % (
        n,
        len(diffs),
        sum(j - i for i, j, _, _ in diffs),
    ))
    for i, j, aa, bb in diffs:
        print(
            "  [%d:%d) %s -> %s"
            % (i, j, aa.hex(), bb.hex())
        )


def analyze_meta(path):
    data = open(path, "rb").read()
    size = len(data)
    print("size=%d (0x%x)" % (size, size))
    print("head32=%s" % data[:32].hex())
    print("tail32=%s" % data[-32:].hex())
    # File size as u32 anywhere in first 256 / last 256 bytes?
    needle = struct.pack("<I", size)
    hits = []
    pos = 0
    while True:
        j = data.find(needle, pos)
        if j < 0:
            break
        hits.append(j)
        pos = j + 1
    print("u32(filesize) occurrences: %d  first=%s" % (len(hits), hits[:10]))
    # Same for size- something common in headers
    for delta in (0, 4, 8, 16, 32, 48, 64):
        if size > delta:
            n2 = struct.pack("<I", size - delta)
            c = data.count(n2)
            if c:
                print("  u32(size-%d)=%d count=%d" % (delta, size - delta, c))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="list units of a given EDU type")
    p.add_argument("save")
    p.add_argument("--type", required=True, help="EDU type name, e.g. 'roman hastati'")

    p = sub.add_parser("set-current", help="copy save and set current soldiers for a type")
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--type", required=True)
    p.add_argument("--current", type=int, required=True)
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("diff", help="byte-span diff of two equal-length saves")
    p.add_argument("a")
    p.add_argument("b")

    p = sub.add_parser("meta", help="print size/header clues (checksum/length hunt)")
    p.add_argument("save")

    args = ap.parse_args(argv)
    if args.cmd == "list":
        list_units(args.save, args.type)
    elif args.cmd == "set-current":
        set_current(args.src, args.dst, args.type, args.current, dry_run=args.dry_run)
    elif args.cmd == "diff":
        diff_saves(args.a, args.b)
    elif args.cmd == "meta":
        analyze_meta(args.save)
    else:
        ap.error("unknown command")
    return 0


if __name__ == "__main__":
    sys.exit(main())
