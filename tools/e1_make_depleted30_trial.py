"""Create Julii-owned hastati depleted to 30/80 with soldier-array trimmed.

Hypothesis after proba_full30: the card tracks how many soldier slots look
'present', not only the +30 current field. We keep full=80 (so retrain/cap
room remains) but mark slots 30..79 dead using templates taken from the known
62-of-80 Brutii hastati, and set current=30.
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
    "proba_slots30.sav",
}
NAME = b"roman hastati"
# Known depleted Brutii hastati — source of dead-slot templates.
DEP_OFF = 418618
# First hastati of a Julii stack (player faction in RomaAroma).
TARGET_OFF = 486554
NEW_CUR = 30


def u32(d, o):
    return struct.unpack_from("<I", d, o)[0]


def put_u32(buf, o, v):
    struct.pack_into("<I", buf, o, v)


def main():
    src = SAVES / "RomaAroma.sav"
    raw = bytearray(src.read_bytes())

    dep_end = DEP_OFF + len(NAME)
    tgt_end = TARGET_OFF + len(NAME)
    assert raw[DEP_OFF:dep_end] == NAME
    assert raw[TARGET_OFF:tgt_end] == NAME
    assert u32(raw, dep_end + 30) == 62
    assert u32(raw, dep_end + 34) == 80
    assert u32(raw, tgt_end + 30) == 80
    assert u32(raw, tgt_end + 34) == 80

    # Dead templates: soldier dwords at indices 62..79 of the depleted unit (+42 base).
    dep_base = dep_end + 42
    dead = [u32(raw, dep_base + i * 4) for i in range(62, 80)]
    print("dead templates", len(dead), [hex(x) for x in dead[:3]], "...")

    tgt_base = tgt_end + 42
    # Keep first NEW_CUR soldier slots; overwrite the rest with cycling dead templates.
    for i in range(NEW_CUR, 80):
        put_u32(raw, tgt_base + i * 4, dead[(i - NEW_CUR) % len(dead)])
    put_u32(raw, tgt_end + 30, NEW_CUR)
    # full stays 80

    nz = sum(1 for i in range(80) if u32(raw, tgt_base + i * 4) != 0)
    # Count slots whose high pattern matches 'alive-ish' b3>=16 from first 30
    alive_like = sum(
        1
        for i in range(80)
        if ((u32(raw, tgt_base + i * 4) >> 24) & 0xFF) >= 16
        and ((u32(raw, tgt_base + i * 4) >> 8) & 0xFF) == 0
    )
    print(
        "target now current=%d full=%d nonzero=%d alive_like_b1eq0_b3ge16=%d"
        % (u32(raw, tgt_end + 30), u32(raw, tgt_end + 34), nz, alive_like)
    )

    dst = SAVES / "proba_depleted30.sav"
    if dst.name in PROTECTED or dst.exists():
        raise SystemExit("refusing %s" % dst)
    tmp = str(dst) + ".tmp"
    with open(tmp, "wb") as f:
        f.write(raw)
    os.rename(tmp, str(dst))
    print("wrote", dst)
    print(
        "LOAD: proba_depleted30 | Julii (your) field army with many Hastati "
        "(~1432 men stack) | unit Roman Hastati | expect **30** men with room "
        "to retrain toward **80**. If still 80, array flags are not what the UI counts."
    )


if __name__ == "__main__":
    main()
