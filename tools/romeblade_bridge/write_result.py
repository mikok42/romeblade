"""Apply M&B survivor totals onto a new RTW result save (additive only)."""
from __future__ import print_function

import os
import re
import struct

from . import battle_select
from . import config
from . import save_io


# Module strings.txt stores spaces as underscores; rgl_log may show either form.
RESULT_RE = re.compile(
    r"ROME[ _]BLADE[ _]RESULT\|winner=(attacker|defender)\|a_left=(\d+)\|b_left=(\d+)"
)


def parse_result_line(line):
    m = RESULT_RE.search(line)
    if not m:
        return None
    return {
        "winner": m.group(1),
        "a_left": int(m.group(2)),
        "b_left": int(m.group(3)),
    }


def parse_result_log(log_path, start_size=0):
    if not os.path.isfile(log_path):
        return None
    with open(log_path, "rb") as f:
        f.seek(start_size)
        text = f.read().decode("utf-8", errors="ignore")
    found = None
    for line in text.splitlines():
        parsed = parse_result_line(line)
        if parsed:
            found = parsed
            found["line"] = line
    return found


def _distribute(unit_rows, new_total):
    """Scale each unit's current so the side sums to new_total (integers)."""
    old_total = sum(int(u["current"]) for u in unit_rows)
    if old_total <= 0:
        return [(u["cur_off"], 0) for u in unit_rows]
    # Largest-remainder method
    raw = []
    for u in unit_rows:
        exact = new_total * float(u["current"]) / old_total
        floor = int(exact)
        raw.append([u, floor, exact - floor])
    assigned = sum(r[1] for r in raw)
    remain = int(new_total) - assigned
    raw.sort(key=lambda r: -r[2])
    for i in range(max(0, remain)):
        raw[i % len(raw)][1] += 1
    patches = []
    for u, val, _frac in raw:
        val = max(0, min(int(u["full"]), val))
        patches.append((int(u["cur_off"]), val))
    return patches


def write_result_save(spec, a_left, b_left, dest_name=None):
    """Copy source_save -> dest with patched currents for both armies."""
    dest_name = dest_name or config.RESULT_SAVE_NAME
    src = spec["source_save"]
    dst = os.path.join(config.RTW_SAVES, dest_name)
    if os.path.basename(dst) in config.PROTECTED_SAVES:
        raise RuntimeError("protected dest")
    if os.path.exists(dst):
        # only allow replacing our own previous result file
        if os.path.basename(dst) != config.RESULT_SAVE_NAME:
            raise RuntimeError("dest exists: %s" % dst)
        os.remove(dst)

    patches = []
    patches.extend(_distribute(spec["army_a"]["unit_rows"], int(a_left)))
    patches.extend(_distribute(spec["army_b"]["unit_rows"], int(b_left)))
    save_io.patch_currents_in_copy(src, dst, patches, config.PROTECTED_SAVES)
    return {"dest": dst, "patches": len(patches), "a_left": a_left, "b_left": b_left}


def write_result_from_log(spec, log_path=None, start_size=0):
    log_path = log_path or config.MB_LOG
    parsed = parse_result_log(log_path, start_size=start_size)
    if not parsed:
        raise RuntimeError("no ROME BLADE RESULT line in %s" % log_path)
    return write_result_save(spec, parsed["a_left"], parsed["b_left"]), parsed
