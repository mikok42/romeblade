#!/usr/bin/env python3
"""RomeBlade bridge — intercept RTW Begin Battle, fight in M&B, apply result.

Trigger (chosen design):
  1) Detect the pre-battle scroll via on-screen match of prebattle_*.tga art.
  2) Arm a low-level mouse hook. When the user left-clicks the Begin Battle
     hitbox, SWALLOW that click so RTW does not start its own tactical battle.
  3) Read both armies from the newest campaign save (M1 heuristic: two largest
     unit-clusters until ownership is solved).
  4) Launch Mount & Blade module RomeBladeRTS.
  5) After a result line appears in rgl_log.txt (or --simulate-result), send
     auto_win + Auto Resolve back in RTW, write romeblade_result.sav, and try
     to open the Load UI.

What still differs from the ideal one-click dream is printed at startup.
"""
from __future__ import print_function

import argparse
import os
import sys
import threading
import time

# Allow `python bridge.py` from this folder.
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    __package__ = "tools.romeblade_bridge"

from . import apply_result
from . import armies
from . import config
from . import detect_prebattle
from . import launchers
from . import mouse_hook
from . import win_input


DIFFERENCES = """
Closest-automatic vs ideal
--------------------------
IDEAL: click Begin Battle on the RTW scroll -> M&B wave fight with those two
armies -> RTW continues with losses applied and no RTW tactical battle.

THIS BUILD:
* Detects the scroll by matching prebattle_*.tga art on screen (no memory RE).
* Intercepts the Begin Battle click with a mouse hook and swallows it so RTW
  should stay on the scroll (not enter deployment). If the hook loses the race,
  RTW may start loading a battle — Escape is sent as a fallback.
* Armies come from the newest .sav in the saves folder (often Autosave / your
  last save), picking the two largest unit-clusters. That is NOT yet proof of
  which two stacks are on the scroll (M1 ownership/position still open).
* M&B is launched into module RomeBladeRTS; wiring those army sizes into the
  wave mission file is still stubbed (falls back to the menu 300-vs-150 battle
  until the module reads bridge-written sizes).
* Result channel watches rgl_log.txt for a 'ROME BLADE RESULT|' line (module
  must write it — not verified in-battle yet). --simulate-result skips that.
* Return path: auto_win + guessed Auto Resolve click, then a NEW save
  romeblade_result.sav. Fully automatic Load of that save is best-effort.
* Never overwrites RomaAroma.sav / Autosave.sav / niunia.sav.
"""


class BridgeState(object):
    def __init__(self):
        self.panel = None
        self.armed = False
        self.busy = False
        self.last_save = None
        self.army_a = None
        self.army_b = None
        self.lock = threading.Lock()


def prepare_armies(state):
    path = armies.latest_readable_save()
    state.last_save = path
    if not path:
        print("BRIDGE: no saves found")
        return False
    blocks = armies.armies_from_save(path)
    a, b = armies.pick_two_largest(blocks)
    state.army_a, state.army_b = a, b
    print(
        "BRIDGE: save=%s armies=%d picked men %s vs %s"
        % (
            os.path.basename(path),
            len(blocks),
            a["summary"]["men"] if a else None,
            b["summary"]["men"] if b else None,
        )
    )
    return a is not None and b is not None


def launch_mb_for_armies(state):
    # Stub: launch module; army sizes to be patched into module export next.
    launchers.set_mb_module(config.MB_MODULE)
    print(
        "BRIDGE: starting M&B (%s). Placeholder battle sizes until wave wiring lands."
        % config.MB_MODULE
    )
    if state.army_a and state.army_b:
        print(
            "BRIDGE: intended A=%d men (%d types) B=%d men (%d types)"
            % (
                state.army_a["summary"]["men"],
                len(state.army_a["summary"]["by_type"]),
                state.army_b["summary"]["men"],
                len(state.army_b["summary"]["by_type"]),
            )
        )
    return launchers.start_mb()


def wait_mb_result(timeout=3600, simulate=None):
    if simulate is not None:
        time.sleep(1)
        return {"winner": simulate, "source": "simulate"}
    tag = config.RESULT_TAG
    path = config.MB_LOG
    # Seek to end first so old lines do not count.
    start_size = os.path.getsize(path) if os.path.isfile(path) else 0
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not os.path.isfile(path):
            time.sleep(config.LOG_POLL_SEC)
            continue
        with open(path, "rb") as f:
            f.seek(start_size)
            chunk = f.read().decode("utf-8", errors="ignore")
        for line in chunk.splitlines():
            if tag in line:
                # ROME BLADE RESULT|winner=attacker|...
                winner = "attacker"
                if "winner=defender" in line:
                    winner = "defender"
                elif "winner=attacker" in line:
                    winner = "attacker"
                return {"winner": winner, "line": line, "source": "log"}
        time.sleep(config.LOG_POLL_SEC)
    return None


def on_mb_done(state, result):
    print("BRIDGE: M&B result", result)
    ok = apply_result.send_auto_win(result["winner"])
    print("BRIDGE: auto_win sent=%s" % ok)
    time.sleep(0.5)
    pos = apply_result.click_auto_resolve_guess()
    print("BRIDGE: clicked Auto Resolve guess at %s" % (pos,))
    # Result save: for now copy newest save untouched as placeholder name only
    # when we have real per-unit patches from M&B (not yet). Keep additive.
    print(
        "BRIDGE: exact soldier patches from M&B not wired yet — "
        "romeblade_result.sav NOT written (would be identical). "
        "auto_win path is the strategic outcome for now."
    )


def make_click_handler(state, fingerprints):
    def handler(x, y):
        with state.lock:
            if state.busy or not state.armed or not state.panel:
                return False
            import ctypes

            sw = ctypes.windll.user32.GetSystemMetrics(0)
            sh = ctypes.windll.user32.GetSystemMetrics(1)
            box = detect_prebattle.begin_battle_hitbox(sw, sh, state.panel)
            if not detect_prebattle.point_in_box(x, y, box):
                return False
            print("BRIDGE: swallowed Begin Battle click at %d,%d box=%s" % (x, y, box))
            state.busy = True
            state.armed = False

        def worker():
            try:
                # Fallback if RTW still reacts: poke Escape.
                time.sleep(0.2)
                win_input.tap_vk(win_input.VK_ESCAPE, pause=0.2)
                if not prepare_armies(state):
                    print("BRIDGE: army prep failed")
                    return
                launch_mb_for_armies(state)
                result = wait_mb_result(simulate=state.simulate_result)
                if not result:
                    print("BRIDGE: no M&B result in time")
                    return
                on_mb_done(state, result)
            finally:
                with state.lock:
                    state.busy = False

        threading.Thread(target=worker, name="rb-battle", daemon=True).start()
        return True  # swallow

    return handler


def run_loop(simulate_result=None, once_demo=False):
    print(DIFFERENCES)
    print("BRIDGE: building prebattle fingerprints...")
    fps = detect_prebattle.build_fingerprints()
    print("BRIDGE: templates=%d" % len(fps))
    state = BridgeState()
    state.simulate_result = simulate_result
    hook = mouse_hook.MouseHook(make_click_handler(state, fps))
    hook.start()
    print("BRIDGE: mouse hook on. Start RTW campaign, open a pre-battle scroll,")
    print("BRIDGE: click Begin Battle — click is intercepted, M&B should start.")
    try:
        while True:
            if launchers.process_running("RomeTW.exe"):
                match = detect_prebattle.poll_prebattle(fps)
                with state.lock:
                    if match and match.get("detected"):
                        if not state.armed and not state.busy:
                            print(
                                "BRIDGE: pre-battle scroll detected score=%.1f tpl=%s"
                                % (
                                    match["score"],
                                    os.path.basename(match["template"]),
                                )
                            )
                            prepare_armies(state)
                            state.panel = match
                            state.armed = True
                    else:
                        if state.armed and not state.busy:
                            state.armed = False
                            state.panel = None
            if once_demo:
                break
            time.sleep(0.75)
    except KeyboardInterrupt:
        print("BRIDGE: stop")
    finally:
        hook.stop()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--simulate-result",
        choices=["attacker", "defender"],
        help="skip waiting for M&B log; pretend this winner",
    )
    ap.add_argument(
        "--list-armies",
        metavar="SAVE",
        help="print army clusters from a save and exit",
    )
    ap.add_argument(
        "--e1-check",
        action="store_true",
        help="verify most_proba.sav byte patch only",
    )
    args = ap.parse_args(argv)

    if args.e1_check:
        from . import e1_verify

        return e1_verify.main(["--no-launch"])

    if args.list_armies:
        blocks = armies.armies_from_save(args.list_armies)
        for a in blocks[:20]:
            s = a["summary"]
            print(
                "#%d men=%d units=%d off=%d..%d top=%s"
                % (
                    a["index"],
                    s["men"],
                    s["units"],
                    a["name_off0"],
                    a["name_off1"],
                    sorted(s["by_type"].items(), key=lambda kv: -kv[1])[:3],
                )
            )
        print("total_armies", len(blocks))
        return 0

    run_loop(simulate_result=args.simulate_result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
