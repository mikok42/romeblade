"""RTW 1.5 save unit read/patch helpers (E1 / M1 building blocks)."""
from __future__ import print_function

import os
import struct
from collections import Counter

# Re-use the standalone tool's rules.
MARKER = b"\xa0\x42"
CUR_OFF = 30
FULL_OFF = 34
MAX_FULL = 240


def _u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


def _put_u32(buf, off, value):
    struct.pack_into("<I", buf, off, value)


def iter_units_of_type(data, unit_type):
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
        if data[end] != 0:
            continue
        if i < 2:
            continue
        declared = struct.unpack_from("<H", data, i - 2)[0]
        if declared != len(name) + 1:
            continue
        if bytes(data[end + 28 : end + 30]) != MARKER:
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
            if end + FULL_OFF + 4 > len(data) or data[end] != 0 or i < 2:
                continue
            declared = struct.unpack_from("<H", data, i - 2)[0]
            if declared != len(name) + 1:
                continue
            if bytes(data[end + 28 : end + 30]) != MARKER:
                continue
            current = _u32(data, end + CUR_OFF)
            full = _u32(data, end + FULL_OFF)
            if not (0 <= current <= full <= MAX_FULL and full > 0):
                continue
            for k in range(i, end):
                covered[k] = 1
            yield {
                "name": unit_type,
                "name_off": i,
                "cur_off": end + CUR_OFF,
                "full_off": end + FULL_OFF,
                "current": current,
                "full": full,
            }


def cluster_armies(units, gap=2000, max_units=20):
    """Group units whose name offsets lie near each other (rough army blocks).

    RTW field armies cap at 20 units including the general, so a run that
    would exceed max_units starts a new block even if the byte gap is small.
    """
    units = sorted(units, key=lambda u: u["name_off"])
    if not units:
        return []
    armies = []
    cur = [units[0]]
    for u in units[1:]:
        close = u["name_off"] - cur[-1]["name_off"] <= gap
        if close and len(cur) < max_units:
            cur.append(u)
        else:
            armies.append(cur)
            cur = [u]
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
