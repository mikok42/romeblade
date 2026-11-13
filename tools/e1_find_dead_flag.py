"""Find soldier dword predicate that matches (full-current) on depleted units."""
from __future__ import print_function

import struct
from pathlib import Path

RAW = Path(
    r"C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold\saves\RomaAroma.sav"
).read_bytes()
NAME = b"roman hastati"

DEPS = [
    (418618, 62, 80),
    (435874, 74, 80),
    (448608, 73, 80),
    (452949, 72, 80),
    (453351, 79, 80),
    (453753, 79, 80),
    (454155, 79, 80),
]


def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


def sols(off, full):
    end = off + len(NAME)
    return [u32(RAW, end + 42 + i * 4) for i in range(full)]


def score_pred(pred):
    ok = 0
    details = []
    for off, cur, full in DEPS:
        ss = sols(off, full)
        dead = full - cur
        n = sum(1 for s in ss if pred(s))
        hit = n == dead
        details.append((off, dead, n, hit))
        if hit:
            ok += 1
    return ok, details


def main():
    best = []
    for bit in range(32):
        ok, det = score_pred(lambda s, bit=bit: ((s >> bit) & 1) == 1)
        if ok >= 2:
            best.append((ok, "bit%d" % bit, det))

    for bi in range(4):
        for thr in range(256):
            ok, det = score_pred(
                lambda s, bi=bi, thr=thr: ((s >> (8 * bi)) & 0xFF) >= thr
            )
            if ok >= 3:
                best.append((ok, "b%d>=%d" % (bi, thr), det))
            ok, det = score_pred(
                lambda s, bi=bi, thr=thr: ((s >> (8 * bi)) & 0xFF) < thr
            )
            if ok >= 3:
                best.append((ok, "b%d<%d" % (bi, thr), det))

    for a in range(32):
        for b in range(32):
            if a == b:
                continue
            ok, det = score_pred(
                lambda s, a=a, b=b: ((s >> a) & 1) and not ((s >> b) & 1)
            )
            if ok >= 4:
                best.append((ok, "bit%d&~bit%d" % (a, b), det))

    # nibble / masked compares on high word
    for shift in range(0, 32, 4):
        for mask in (0xF, 0xFF, 0xFFF):
            for thr in range(mask + 1):
                ok, det = score_pred(
                    lambda s, shift=shift, mask=mask, thr=thr: ((s >> shift) & mask)
                    == thr
                )
                if ok >= 3:
                    best.append((ok, "(s>>%d)&%x==%d" % (shift, mask, thr), det))

    best.sort(reverse=True)
    print("top predicates:")
    seen = set()
    shown = 0
    for ok, name, det in best:
        if name in seen:
            continue
        seen.add(name)
        print(ok, name, det)
        shown += 1
        if shown >= 40:
            break

    # Compare each depleted unit against a nearby full hastati: which
    # soldier indices look most like outliers vs the full unit's value cloud.
    print("\n--- vs nearby full unit value clouds ---")
    full_off = 417564
    full_ss = set(sols(full_off, 80))
    for off, cur, full in DEPS[:3]:
        ss = sols(off, full)
        rare = [(i, s) for i, s in enumerate(ss) if s not in full_ss]
        print(
            "dep",
            off,
            "cur",
            cur,
            "values_not_in_full80",
            len(rare),
            "sample",
            [(i, hex(s)) for i, s in rare[:8]],
        )


if __name__ == "__main__":
    main()
