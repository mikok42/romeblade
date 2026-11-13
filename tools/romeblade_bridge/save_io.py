"""RTW 1.5 save unit read/patch helpers (E1 / M1 building blocks)."""
from __future__ import print_function

import os
import struct
from collections import Counter

# Infantry often has A0 42 at name_end+28; cavalry/generals use other *42 / *43
# words there. Treat the high byte of that u16 as the family marker.
MARKER_HI = (0x42,)
CUR_OFF = 30
FULL_OFF = 34
MAX_FULL = 240

# EDU name substrings that mark a command unit (starts a new army block).
GENERAL_NAME_PARTS = (
    "generals guard",
    "general's",
    "generals cavalry",
    "general ",
    "chieftain cavalry",
    "warlord",
    "pharaohs guard",
    "rebel general",
)


def _u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


def _put_u32(buf, off, value):
    struct.pack_into("<I", buf, off, value)


def _looks_like_unit(data, name_off, name_len):
    end = name_off + name_len
    if end + FULL_OFF + 4 > len(data):
        return None
    if data[end] != 0 or name_off < 2:
        return None
    declared = struct.unpack_from("<H", data, name_off - 2)[0]
    if declared != name_len + 1:
        return None
    if data[end + 29] not in MARKER_HI:
        return None
    current = _u32(data, end + CUR_OFF)
    full = _u32(data, end + FULL_OFF)
    if not (full > 0 and full <= MAX_FULL and 0 <= current <= MAX_FULL):
        return None
    # Infantry: current <= full. Generals/cavalry sometimes store current > full.
    if current > full and current > full + 16:
        return None
    return {
        "name_off": name_off,
        "cur_off": end + CUR_OFF,
        "full_off": end + FULL_OFF,
        "current": current,
        "full": full,
    }


def is_general_unit(unit_type):
    n = unit_type.lower()
    return any(p in n for p in GENERAL_NAME_PARTS)


def iter_units_of_type(data, unit_type):
    name = unit_type.encode("ascii")
    start = 0
    while True:
        i = data.find(name, start)
        if i < 0:
            break
        start = i + 1
        hit = _looks_like_unit(data, i, len(name))
        if not hit:
            continue
        hit["name"] = unit_type
        yield hit


def iter_all_units(data, edu_names):
    """Scan for every EDU type name supplied (sorted longest-first)."""
    names = sorted(set(edu_names), key=len, reverse=True)
    # Mark covered ranges so a shorter name cannot match inside a longer one.
    covered = bytearray(len(data))
    for unit_type in names:
        name = unit_type.encode("ascii")
        start = 0
        while True:
            i = data.find(name, start)
            if i < 0:
                break
            end = i + len(name)
            start = i + 1
            if any(covered[i:end]):
                continue
            hit = _looks_like_unit(data, i, len(name))
            if not hit:
                continue
            for k in range(i, end):
                covered[k] = 1
            hit["name"] = unit_type
            yield hit


def cluster_armies(units, gap=2000, max_units=20):
    """Group units into army blocks.

    A general/command EDU starts a new stack. Otherwise units that sit within
    ``gap`` bytes of each other stay together, capped at ``max_units`` (RTW
    field army size including the general).
    """
    units = sorted(units, key=lambda u: u["name_off"])
    if not units:
        return []
    armies = []
    cur = []
    for u in units:
        if not cur:
            cur = [u]
            continue
        gap_ok = u["name_off"] - cur[-1]["name_off"] <= gap
        if is_general_unit(u["name"]):
            armies.append(cur)
            cur = [u]
        elif gap_ok and len(cur) < max_units:
            cur.append(u)
        else:
            armies.append(cur)
            cur = [u]
    if cur:
        armies.append(cur)
    return armies


def summarize_army(units):
    by = Counter()
    men = 0
    for u in units:
        by[u["name"]] += u["current"]
        men += u["current"]
    return {"units": len(units), "men": men, "by_type": dict(by)}


def load_edu_type_names(edu_path):
    names = []
    with open(edu_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("type"):
                # type roman hastati
                parts = line.split(None, 1)
                if len(parts) == 2:
                    names.append(parts[1].strip())
    return names


def set_current_for_type(src_path, dst_path, unit_type, new_current, protected):
    """Copy src -> dst (dst must not exist / not protected) and patch currents."""
    base = os.path.basename(dst_path)
    if base in protected:
        raise RuntimeError("refusing protected save name: %s" % base)
    if os.path.exists(dst_path):
        raise RuntimeError("refusing to overwrite existing file: %s" % dst_path)
    data = bytearray(open(src_path, "rb").read())
    rows = list(iter_units_of_type(data, unit_type))
    if not rows:
        raise RuntimeError("no units %r in %s" % (unit_type, src_path))
    for r in rows:
        if new_current > r["full"]:
            raise RuntimeError("current > full at %d" % r["name_off"])
        _put_u32(data, r["cur_off"], new_current)
    tmp = dst_path + ".tmp"
    if os.path.exists(tmp):
        raise RuntimeError("temp exists: %s" % tmp)
    with open(tmp, "wb") as f:
        f.write(data)
    os.rename(tmp, dst_path)
    return len(rows)


def patch_currents_in_copy(src_path, dst_path, patches, protected):
    """patches: list of (cur_off, new_current). Same-length in-place copy."""
    base = os.path.basename(dst_path)
    if base in protected:
        raise RuntimeError("refusing protected save name: %s" % base)
    if os.path.exists(dst_path):
        raise RuntimeError("refusing to overwrite existing file: %s" % dst_path)
    data = bytearray(open(src_path, "rb").read())
    for off, value in patches:
        _put_u32(data, off, int(value))
    tmp = dst_path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.rename(tmp, dst_path)
    return len(patches)


def byte_diff_report(a_path, b_path):
    a = open(a_path, "rb").read()
    b = open(b_path, "rb").read()
    if len(a) != len(b):
        return {"equal_length": False, "len_a": len(a), "len_b": len(b)}
    changed = [i for i in range(len(a)) if a[i] != b[i]]
    return {
        "equal_length": True,
        "size": len(a),
        "changed_bytes": len(changed),
        "offsets": changed[:200],
    }
