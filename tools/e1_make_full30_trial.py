"""Create corrected E1 trial saves (offline). Does not touch protected saves."""
from __future__ import print_function

import os
import struct
from pathlib import Path

SAVES = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold\saves")
PROTECTED = {"RomaAroma.sav", "Autosave.sav", "niunia.sav", "most_proba.sav", "proba2.sav"}
NAME = b"roman hastati"
MARKER = b"\xa0\x42"


def u16(d, o):
    return struct.unpack_from("<H", d, o)[0]


def u32(d, o):
    return struct.unpack_from("<I", d, o)[0]


def put_u32(buf, o, v):
    struct.pack_into("<I", buf, o, v)


def find_hastati(data):
    out = []
    start = 0
    while True:
        i = data.find(NAME, start)
        if i < 0:
            break
        end = i + len(NAME)
        start = i + 1
        if end >= len(data) or data[end] != 0 or i < 2:
            continue
        if u16(data, i - 2) != len(NAME) + 1:
            continue
        if bytes(data[end + 28 : end + 30]) != MARKER:
            continue
        cur, ful = u32(data, end + 30), u32(data, end + 34)
        if 0 <= cur <= ful <= 240 and ful > 0:
            out.append({"name_off": i, "end": end, "cur": cur, "full": ful})
    return out


def write_new(path, data):
    name = os.path.basename(path)
    if name in PROTECTED or os.path.exists(path):
        raise SystemExit("refusing to write %s" % path)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.rename(tmp, path)
    print("wrote", path, "len", len(data))


def main():
    src = SAVES / "most_proba.sav"
    raw = bytearray(src.read_bytes())
    units = find_hastati(raw)
    print("hastati", len(units), "from", src.name)

    # Trial A: all hastati current+full -> 30 (no array compaction; pointers assumed).
    a = bytearray(raw)
    for u in units:
        put_u32(a, u["end"] + 30, 30)
        put_u32(a, u["end"] + 34, 30)
    write_new(str(SAVES / "proba_full30.sav"), a)

    # Trial B: single distinctive unit (the ex-62 slot @418618): current+full -> 7
    b = bytearray(raw)
    target = [u for u in units if u["name_off"] == 418618][0]
    put_u32(b, target["end"] + 30, 7)
    put_u32(b, target["end"] + 34, 7)
    # leave other hastati as in most_proba (current 30, full 80)
    write_new(str(SAVES / "proba_one7.sav"), b)

    # Verify
    for name in ("proba_full30.sav", "proba_one7.sav"):
        d = (SAVES / name).read_bytes()
        hu = find_hastati(d)
        print(
            name,
            "cur",
            sorted(set(u["cur"] for u in hu)),
            "full",
            sorted(set(u["full"] for u in hu)),
            "unit@418618",
            [(u["cur"], u["full"]) for u in hu if u["name_off"] == 418618],
        )

    print(
        """
LOOK AT:
  Save: proba_full30  (all roman hastati max+current set to 30)
  Or:   proba_one7    (only the formerly 62/80 hastati is 7/7; others still 30/80 in file)

  Army: Brutii-adjacent Roman stack that held the wounded hastati in RomaAroma
        (our cluster army #0 ~1582 men: hastati+archers+principes+mercs).
        On the map: open Roman (Brutii) field armies and inspect a Hastati card.
        If the card shows 30 (or 7 on proba_one7) the authoritative field includes 'full'.
        If it still shows 80, the UI is not reading these record fields at all.
"""
    )


if __name__ == "__main__":
    main()
