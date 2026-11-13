"""Apply M&B survivor totals onto a new RTW result save (additive only).

Proven (proba_disp41): the unit card shows name_end+34 (display).
+30 (alt) is a distinct field; natural 62/80 records still unexplained.
Retrain-to-EDU-max after lowering +34 is UNVERIFIED in-game.
"""
from __future__ import print_function

import os
import re

from . import config
from . import save_io


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


def _unit_display(u):
    return int(u.get("display", u.get("full", u.get("current", 0))))


def _unit_display_off(u):
    return int(u.get("display_off", u.get("full_off")))


def _distribute_display(unit_rows, new_total):
    """Scale each unit's displayed strength (+34) to sum to new_total."""
    old_total = sum(_unit_display(u) for u in unit_rows)
    if old_total <= 0:
        return [(_unit_display_off(u), 0) for u in unit_rows]
    raw = []
    for u in unit_rows:
        exact = new_total * float(_unit_display(u)) / old_total
        floor = int(exact)
        raw.append([u, floor, exact - floor])
    assigned = sum(r[1] for r in raw)
    remain = int(new_total) - assigned
    raw.sort(key=lambda r: -r[2])
    for i in range(max(0, remain)):
        raw[i % len(raw)][1] += 1
    patches = []
    for u, val, _frac in raw:
        # Cap at pre-battle display (do not grow a unit past what it brought).
        cap = _unit_display(u)
        val = max(0, min(cap, val))
        patches.append((_unit_display_off(u), val))
    return patches


def write_result_save(spec, a_left, b_left, dest_name=None):
    """Copy source_save -> dest; patch +34 display on both armies' units.

    Does not rewrite +30 (alt). Does not delete unit records when survivors
    hit 0 — sets display to 0 (closest safe substitute until po_bitwie).
    Retrain after this patch is not proven.
    """
    dest_name = dest_name or config.RESULT_SAVE_NAME
    src = spec["source_save"]
    dst = os.path.join(config.RTW_SAVES, dest_name)
    if os.path.basename(dst) in config.PROTECTED_SAVES:
        raise RuntimeError("protected dest")
    if os.path.exists(dst):
        if os.path.basename(dst) != config.RESULT_SAVE_NAME:
            raise RuntimeError("dest exists: %s" % dst)
        os.remove(dst)

    patches = []
    patches.extend(_distribute_display(spec["army_a"]["unit_rows"], int(a_left)))
    patches.extend(_distribute_display(spec["army_b"]["unit_rows"], int(b_left)))
    save_io.patch_displays_in_copy(src, dst, patches, config.PROTECTED_SAVES)
    wiped = sum(1 for _off, v in patches if v == 0)
    return {
        "dest": dst,
        "patches": len(patches),
        "a_left": a_left,
        "b_left": b_left,
        "wiped_display_zero": wiped,
        "retrain": "unverified",
    }


def write_result_from_log(spec, log_path=None, start_size=0):
    log_path = log_path or config.MB_LOG
    parsed = parse_result_log(log_path, start_size=start_size)
    if not parsed:
        raise RuntimeError("no ROME BLADE RESULT line in %s" % log_path)
    return write_result_save(spec, parsed["a_left"], parsed["b_left"]), parsed
