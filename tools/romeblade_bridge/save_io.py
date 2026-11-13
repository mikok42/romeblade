"""RTW 1.5 save unit read/patch helpers (E1 / M1 building blocks)."""
from __future__ import print_function

import os
import struct
from collections import Counter

# Infantry often has A0 42 at name_end+28; cavalry/generals use other *42 words.
MARKER_HI = (0x42,)
# Proven: name_end+34 is the number on the unit card (displayed strength).
# name_end+30 is a related but distinct field (see natural 62/80 records).
ALT_OFF = 30
DISPLAY_OFF = 34
# Back-compat aliases (old names assumed current/full; that was wrong for UI).
CUR_OFF = ALT_OFF
FULL_OFF = DISPLAY_OFF
MAX_FULL = 240

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
    if end + DISPLAY_OFF + 4 > len(data):
        return None
    if data[end] != 0 or name_off < 2:
        return None
    declared = struct.unpack_from("<H", data, name_off - 2)[0]
    if declared != name_len + 1:
        return None
    if data[end + 29] not in MARKER_HI:
        return None
    alt = _u32(data, end + ALT_OFF)
    display = _u32(data, end + DISPLAY_OFF)
    # Display may be below alt after loss patches (proba_disp41). Both must be in range;
    # display==0 means wiped-on-card (still a record).
    if not (0 <= display <= MAX_FULL and 0 <= alt <= MAX_FULL):
        return None
    if display == 0 and alt == 0:
        return None
    return {
        "name_off": name_off,
        "alt_off": end + ALT_OFF,
        "display_off": end + DISPLAY_OFF,
        # aliases used by older call sites
        "cur_off": end + ALT_OFF,
        "full_off": end + DISPLAY_OFF,
        "alt": alt,
        "display": display,
        "current": display,
        "full": max(display, alt) if alt else display,
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
    """Group units into army blocks (general starts a new stack)."""
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
    """Men totals use displayed strength (+34), proven by proba_disp41."""
    by = Counter()
    men = 0
    for u in units:
        n = int(u.get("display", u.get("full", 0)))
        by[u["name"]] += n
        men += n
    return {"units": len(units), "men": men, "by_type": dict(by)}


def load_edu_type_names(edu_path):
    names = []
    with open(edu_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line.startswith("type"):
                parts = line.split(None, 1)
                if len(parts) == 2:
                    names.append(parts[1].strip())
    return names


def set_current_for_type(src_path, dst_path, unit_type, new_current, protected):
    """Legacy helper: patches +30 (alt). Prefer patch_displays_in_copy for UI."""
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
        _put_u32(data, r["alt_off"], new_current)
    tmp = dst_path + ".tmp"
    if os.path.exists(tmp):
        raise RuntimeError("temp exists: %s" % tmp)
    with open(tmp, "wb") as f:
        f.write(data)
    os.rename(tmp, dst_path)
    return len(rows)


def patch_u32s_in_copy(src_path, dst_path, patches, protected):
    """patches: list of (offset, u32_value). Additive copy only."""
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


def patch_currents_in_copy(src_path, dst_path, patches, protected):
    """Back-compat name → patch_u32s_in_copy."""
    return patch_u32s_in_copy(src_path, dst_path, patches, protected)


def patch_displays_in_copy(src_path, dst_path, patches, protected):
    """patches: list of (display_off, new_display)."""
    return patch_u32s_in_copy(src_path, dst_path, patches, protected)


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
