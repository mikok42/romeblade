"""Pull army blocks from an RTW save (M1 heuristic, not ownership-aware yet)."""
from __future__ import print_function

import os

from . import config
from . import save_io


def default_edu_path():
    return os.path.join(config.RTW_ROOT, "data", "export_descr_unit.txt")


def latest_readable_save(saves_dir=None):
    """Newest .sav that is not a bridge temp .tmp."""
    saves_dir = saves_dir or config.RTW_SAVES
    cands = []
    for name in os.listdir(saves_dir):
        if not name.lower().endswith(".sav"):
            continue
        path = os.path.join(saves_dir, name)
        if not os.path.isfile(path):
            continue
        cands.append((os.path.getmtime(path), path))
    if not cands:
        return None
    cands.sort(reverse=True)
    return cands[0][1]


def armies_from_save(path, edu_path=None, gap=2000):
    edu_path = edu_path or default_edu_path()
    names = save_io.load_edu_type_names(edu_path)
    data = open(path, "rb").read()
    units = list(save_io.iter_all_units(data, names))
    blocks = save_io.cluster_armies(units, gap=gap)
    armies = []
    for i, block in enumerate(blocks):
        summary = save_io.summarize_army(block)
        armies.append(
            {
                "index": i,
                "name_off0": block[0]["name_off"],
                "name_off1": block[-1]["name_off"],
                "units": block,
                "summary": summary,
            }
        )
    armies.sort(key=lambda a: a["summary"]["men"], reverse=True)
    return armies


def pick_two_largest(armies):
    if len(armies) < 2:
        return None, None
    return armies[0], armies[1]


def composition_for_mb(army):
    """Map EDU type -> current soldiers for the wave / spawn side."""
    return dict(army["summary"]["by_type"])
