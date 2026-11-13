"""Third E1 trial: make one hastati's soldier array match a reduced headcount.

Offline only. Does not overwrite protected / prior trial saves.
"""
from __future__ import print_function

import os
import struct
from pathlib import Path

SAVES = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold\saves")
PROTECTED = {
    "RomaAroma.sav",
    "Autosave.sav",
    "niunia.sav",
    "most_proba.sav",
    "proba2.sav",
    "proba_full30.sav",
    "proba_one7.sav",
}
NAME = b"roman hastati"
# The formerly 62/80 hastati — distinctive slot used in earlier trials.
TARGET_NAME_OFF = 418618
NEW_CUR = 30


def u32(d, o):
    return struct.unpack_from("<I", d, o)[0]


def put_u32(buf, o, v):
    struct.pack_into("<I", buf, o, v)


def main():
    # Start from RomaAroma so the array still has the real 62/18 alive/dead split,
    # then reduce to 30 living slots + zero the rest + set current=30 (full stays 80).
    src = SAVES / "RomaAroma.sav"
    raw = bytearray(src.read_bytes())
    end = TARGET_NAME_OFF + len(NAME)
    assert raw[TARGET_NAME_OFF:end] == NAME
    assert raw[end] == 0
    assert raw[end + 28 : end + 30] == b"\xa0\x42"

    old_cur = u32(raw, end + 30)
    old_full = u32(raw, end + 34)
    print("target @%d was %d/%d" % (TARGET_NAME_OFF, old_cur, old_full))

    # Soldier dwords begin at end+42 (end+38 is a zero pad on these records).
    base = end + 42
    # Keep first NEW_CUR soldier dwords; zero the remaining (full - NEW_CUR) slots.
    for i in range(NEW_CUR, old_full):
        put_u32(raw, base + i * 4, 0)
    put_u32(raw, end + 30, NEW_CUR)
    # full left at 80 — capacity unchanged; array now has only 30 nonzero slots.

    # Sanity: count nonzero soldier slots
    nz = sum(1 for i in range(old_full) if u32(raw, base + i * 4) != 0)
    print("nonzero soldier slots now", nz, "current field", u32(raw, end + 30), "full", u32(raw, end + 34))

    dst = SAVES / "proba_slots30.sav"
    if dst.name in PROTECTED or dst.exists():
        raise SystemExit("refusing %s" % dst)
    tmp = str(dst) + ".tmp"
    with open(tmp, "wb") as f:
        f.write(raw)
    os.rename(tmp, str(dst))
    print("wrote", dst)
    print(
        "LOAD MENU: proba_slots30 | expect Hastati card **30** if UI counts "
        "soldier slots; still **80** if it uses full/EDU only. "
        "Look at the same formerly-62 Hastati (Roman stack near Brutii)."
    )


if __name__ == "__main__":
    main()
