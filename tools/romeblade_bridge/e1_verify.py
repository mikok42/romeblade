"""Automated E1 attempt: confirm most_proba.sav is a clean patch, launch RTW, try Load.

Does not overwrite player saves. Reports what still needs human eyes.
"""
from __future__ import print_function

import argparse
import os
import sys
import time

from . import config
from . import launchers
from . import save_io
from . import win_input


def ensure_most_proba():
    src = os.path.join(config.RTW_SAVES, "RomaAroma.sav")
    dst = os.path.join(config.RTW_SAVES, config.E1_SAVE_NAME)
    if not os.path.isfile(src):
        raise SystemExit("missing %s" % src)
    if not os.path.isfile(dst):
        print("creating %s ..." % dst)
        n = save_io.set_current_for_type(
            src, dst, "roman hastati", 30, config.PROTECTED_SAVES
        )
        print("patched %d hastati units -> 30" % n)
    report = save_io.byte_diff_report(src, dst)
    print("diff:", report)
    rows = list(
        save_io.iter_units_of_type(open(dst, "rb").read(), "roman hastati")
    )
    bad = [r for r in rows if r["current"] != 30]
    print("hastati_in_copy=%d not_30=%d" % (len(rows), len(bad)))
    # Meta: no filesize u32 in file
    data = open(dst, "rb").read()
    import struct

    needle = struct.pack("<I", len(data))
    print("filesize_u32_count=%d" % data.count(needle))
    return dst


def try_drive_load(save_stem="most_proba", shots_dir=None):
    shots_dir = shots_dir or os.path.join(config.REPO_ROOT, "out", "e1_shots")
    os.makedirs(shots_dir, exist_ok=True)

    if launchers.process_running("RomeTW.exe"):
        print("RomeTW.exe already running — not starting a second copy")
        proc = None
    else:
        print("starting RTW (-ne -show_err)...")
        proc = launchers.start_rtw_windowed()
        time.sleep(8)

    # Skip intros / movies with Escape a few times
    for i in range(10):
        wins = win_input.find_windows("Rome")
        if not wins:
            wins = win_input.find_windows("Total War")
        if wins:
            win_input.focus_window(wins[0][0])
            break
        time.sleep(1)
    else:
        print("NO_WINDOW: RTW window title not found")
        path = os.path.join(shots_dir, "no_window.bmp")
        win_input.screenshot_window_bmp(path)
        print("screenshot", path)
        return {"ok": False, "reason": "no_window", "shot": path}

    for _ in range(8):
        win_input.tap_vk(win_input.VK_ESCAPE, pause=0.4)
    shot1 = os.path.join(shots_dir, "01_after_esc.bmp")
    win_input.screenshot_window_bmp(shot1)
    print("screenshot", shot1)

    # Heuristic menu walk (English UI): Single Player Enter, then Load-ish.
    # This is best-effort; coordinates/order vary with language and resolution.
    win_input.tap_vk(win_input.VK_RETURN, pause=1.0)  # Single Player?
    win_input.tap_vk(win_input.VK_DOWN, pause=0.3)
    win_input.tap_vk(win_input.VK_DOWN, pause=0.3)
    win_input.tap_vk(win_input.VK_RETURN, pause=1.5)  # Load Game?
    shot2 = os.path.join(shots_dir, "02_load_list.bmp")
    win_input.screenshot_window_bmp(shot2)
    print("screenshot", shot2)

    # Type save name filter is not available; arrow through list is unreliable.
    # Open console and note: there is no documented load_game <file> command.
    win_input.tap_vk(win_input.VK_OEM_3, pause=0.5)
    win_input.tap_text_unicode("toggle_tow")
    win_input.tap_vk(win_input.VK_RETURN, pause=0.5)
    shot3 = os.path.join(shots_dir, "03_console.bmp")
    win_input.screenshot_window_bmp(shot3)
    print("screenshot", shot3)

    alive = launchers.process_running("RomeTW.exe")
    print("RomeTW_alive=%s" % alive)
    return {
        "ok": alive,
        "reason": "drove_keys_best_effort",
        "shots": [shot1, shot2, shot3],
        "proc": proc.pid if proc else None,
        "note": (
            "Could not confirm hastati=30 in-UI without a reliable load_game CLI. "
            "Load '%s' manually once if screenshots show the main menu." % save_stem
        ),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-launch", action="store_true", help="only check the save bytes")
    ap.add_argument("--launch", action="store_true", help="also launch RTW and try keys")
    args = ap.parse_args(argv)
    ensure_most_proba()
    if args.launch and not args.no_launch:
        result = try_drive_load()
        print("E1_LAUNCH_RESULT", result)
        return 0 if result.get("ok") else 2
    print(
        "E1 byte proof ready: %s (hastati current=30). "
        "In-game acceptance still needs a successful Load of that slot."
        % config.E1_SAVE_NAME
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
