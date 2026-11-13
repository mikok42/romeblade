#!/usr/bin/env python3
"""RomeBlade bridge — intercept RTW Begin Battle, fight in M&B, apply result.

Trigger (chosen design):
  1) Detect the pre-battle scroll via on-screen match of prebattle_*.tga art.
  2) Arm a low-level mouse hook. When the user left-clicks the Begin Battle
     hitbox, SWALLOW that click so RTW does not start its own tactical battle.
  3) Read both armies from the newest campaign save (M1 heuristic / manifest).
  4) Launch Mount & Blade module RomeBladeRTS.
  5) After a result line in rgl_log.txt (or --simulate-result), write
     romeblade_result.sav, install it as quicksave.sav (backing up any
     existing quicksave first), and send Ctrl+L — no Load Game menu.

The starter .bat launches this bridge then Rome in the player's normal
fullscreen mode. This module does not start RTW itself unless asked.
"""
from __future__ import print_function

import argparse
import atexit
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
* Detects the scroll by matching prebattle_*.tga art on a GDI desktop grab.
  Fullscreen exclusive DirectX may yield a black capture — UNVERIFIED on desk.
* Intercepts the Begin Battle click with a mouse hook and swallows it so RTW
  should stay on the scroll. If the hook loses the race, Escape is a fallback.
* Armies come from the newest .sav (often Autosave / last save) unless a
  pending-battle manifest is present. Pairing is not map-adjacency proof.
* M&B module RomeBladeRTS; wave sizes via prepare_mb (menus.txt patch).
* Result channel: rgl_log.txt 'ROME BLADE RESULT|' (or --simulate-result).
* Return path: NEW romeblade_result.sav -> backup existing quicksave.sav ->
  overwrite quicksave.sav -> Ctrl+L. No Load Game menu.
  Ctrl+L effect mid-scroll is UNVERIFIED. auto_win + Auto Resolve remain as
  scroll-dismiss fallback (Auto Resolve hitbox still a guess).
* Never overwrites RomaAroma.sav / Autosave.sav / niunia.sav.
* Existing quicksave.sav is copied to rb_qs_backup_<stamp>.sav before replace.
* Bridge exits and unhooks when RTW closes (or on Ctrl+C / atexit).
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


_active_hook = None


def _cleanup_hook():
    global _active_hook
    hook = _active_hook
    _active_hook = None
    if hook is not None:
        try:
            hook.stop()
        except Exception as e:
            print("BRIDGE: hook stop error:", e)


def prepare_armies(state):
    from . import battle_select
    from . import prepare_mb

    path = armies.latest_readable_save()
    state.last_save = path
    if not path:
        print("BRIDGE: no saves found")
        return False
    try:
        a, b, meta = battle_select.select_battle_pair(path)
        method = meta.get("method")
    except LookupError as e:
        print("BRIDGE: pair from manifest failed (%s); hostile candidates fallback" % e)
        from . import army_move

        cand = army_move.select_hostile_pair_near_player(path)
        if not cand["candidates"]:
            print("BRIDGE: no hostile pair candidates")
            return False
        top = cand["candidates"][0]
        blocks = battle_select.list_battle_armies(path)
        by = {x["index"]: x for x in blocks}
        a, b = by[top["index_a"]], by[top["index_b"]]
        method = "hostile_men_rank"
        print(
            "BRIDGE: WARNING using men-ranked hostile pair — not map-adjacent proof"
        )
    state.army_a, state.army_b = a, b
    state.battle_spec = battle_select.battle_spec(path, a, b)
    try:
        meta_mb = prepare_mb.prepare_from_spec(state.battle_spec)
        print("BRIDGE: prepare_mb", meta_mb.get("menus_patched"))
    except Exception as e:
        print("BRIDGE: prepare_mb failed:", e)
    print(
        "BRIDGE: save=%s method=%s men %s vs %s factions %s vs %s"
        % (
            os.path.basename(path),
            method,
            a["summary"]["men"],
            b["summary"]["men"],
            a.get("faction_guess"),
            b.get("faction_guess"),
        )
    )
    return True


def launch_mb_for_armies(state):
    launchers.set_mb_module(config.MB_MODULE)
    print("BRIDGE: starting M&B (%s)" % config.MB_MODULE)
    if state.army_a and state.army_b:
        print(
            "BRIDGE: intended A=%d men B=%d men"
            % (state.army_a["summary"]["men"], state.army_b["summary"]["men"])
        )
    return launchers.start_mb()


def wait_mb_result(timeout=3600, simulate=None):
    from . import write_result

    if simulate is not None:
        time.sleep(1)
        return {"winner": simulate, "source": "simulate", "a_left": None, "b_left": None}
    path = config.MB_LOG
    start_size = os.path.getsize(path) if os.path.isfile(path) else 0
    t0 = time.time()
    while time.time() - t0 < timeout:
        parsed = write_result.parse_result_log(path, start_size=start_size)
        if parsed:
            return parsed
        time.sleep(config.LOG_POLL_SEC)
    return None


def on_mb_done(state, result):
    from . import write_result

    print("BRIDGE: M&B result", result)
    spec = getattr(state, "battle_spec", None)
    if not spec:
        print("BRIDGE: no battle_spec — skip result save")
        return
    a_left = result.get("a_left")
    b_left = result.get("b_left")
    if a_left is None or b_left is None:
        a_left = max(1, state.army_a["summary"]["men"] // 2)
        b_left = max(0, state.army_b["summary"]["men"] // 10)
        print("BRIDGE: simulate survivors a=%s b=%s" % (a_left, b_left))
    try:
        info = write_result.write_result_save(spec, a_left, b_left)
        print("BRIDGE: wrote", info)
    except Exception as e:
        print("BRIDGE: write_result failed:", e)
        return

    # Primary return: quicksave slot + Ctrl+L (no menu).
    try:
        qs = apply_result.return_via_quicksave(info["dest"])
        print("BRIDGE: quicksave return", qs)
    except Exception as e:
        print("BRIDGE: quicksave return failed:", e)

    # Fallback: dismiss scroll without fighting RTW's battle.
    ok = apply_result.send_auto_win(result["winner"])
    print("BRIDGE: auto_win sent=%s (fallback dismiss)" % ok)
    time.sleep(0.5)
    pos = apply_result.click_auto_resolve_guess()
    print("BRIDGE: Auto Resolve guess at %s (fallback)" % (pos,))


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


def run_loop(simulate_result=None, once_demo=False, watch_rtw=True):
    global _active_hook
    print(DIFFERENCES)
    print("BRIDGE: building prebattle fingerprints...")
    fps = detect_prebattle.build_fingerprints()
    print("BRIDGE: templates=%d" % len(fps))
    state = BridgeState()
    state.simulate_result = simulate_result
    hook = mouse_hook.MouseHook(make_click_handler(state, fps))
    _active_hook = hook
    atexit.register(_cleanup_hook)
    hook.start()
    print("BRIDGE: mouse hook on. Load your campaign yourself, open a pre-battle")
    print("BRIDGE: scroll, click Begin Battle — click is intercepted, M&B starts.")
    print("BRIDGE: no RTW menu automation; result returns via quicksave + Ctrl+L.")

    seen_rtw = False
    gone_since = None
    try:
        while True:
            rtw_alive = launchers.process_running("RomeTW.exe")
            if rtw_alive:
                seen_rtw = True
                gone_since = None
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
            elif watch_rtw and seen_rtw:
                if gone_since is None:
                    gone_since = time.time()
                    print("BRIDGE: RomeTW.exe gone — will exit after cleanup")
                elif time.time() - gone_since >= config.RTW_GONE_EXIT_SEC:
                    print("BRIDGE: exiting (RTW closed, no leftover hook)")
                    break
            if once_demo:
                break
            time.sleep(0.75)
    except KeyboardInterrupt:
        print("BRIDGE: stop (KeyboardInterrupt)")
    finally:
        _cleanup_hook()
        print("BRIDGE: hook cleared; process exiting")


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
    ap.add_argument(
        "--no-watch-rtw",
        action="store_true",
        help="do not exit when RomeTW.exe closes",
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

    run_loop(
        simulate_result=args.simulate_result,
        watch_rtw=not args.no_watch_rtw,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
