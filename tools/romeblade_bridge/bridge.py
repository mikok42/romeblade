#!/usr/bin/env python3
"""RomeBlade bridge - intercept RTW Begin Battle, fight in M&B, apply result.

Trigger (chosen design):
  1) Detect the pre-battle scroll via on-screen match of prebattle_*.tga art.
  2) Arm a low-level mouse hook. When the user left-clicks the Begin Battle
     hitbox, SWALLOW that click so RTW does not start its own tactical battle.
  3) Read both armies from the newest campaign save (M1 heuristic / manifest).
  4) Launch Mount & Blade module RomeBladeRTS.
  5) After a result line in rgl_log.txt (or --simulate-result), write
     romeblade_result.sav, install it as quicksave.sav (backing up any
     existing quicksave first), and send Ctrl+L - no Load Game menu.

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
from . import blog
from . import config
from . import detect_prebattle
from . import hotkey_arm
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
  Prefer Rome -ne (windowed): exclusive FS often yields black GDI.
* Mouse hook ONLY while armed (GDI scroll match, or F5 backup), then removed.
* No Arm panel / external UZBRÓJ window in the default starter.
* Armies from newest .sav (+34 display); prepare_mb patches wave totals + role mix.
* M&B: user Graj -> Nowa gra; module INIT enters Wave Battle (no UI clicks by bridge).
* Result: rgl_log.txt; return via quicksave + Ctrl+L (UNVERIFIED mid-scroll).
* Never overwrites RomaAroma / Autosave / niunia. Bridge exits when RTW closes.
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
            "BRIDGE: WARNING using men-ranked hostile pair - not map-adjacent proof"
        )
    state.army_a, state.army_b = a, b
    state.battle_spec = battle_select.battle_spec(path, a, b)
    try:
        meta_mb = prepare_mb.prepare_from_spec(state.battle_spec)
        patched = meta_mb.get("menus_patched") or {}
        print("BRIDGE: prepare_mb", patched)
        ra = meta_mb.get("roles_a") or {}
        rb = meta_mb.get("roles_b") or {}
        print(
            "BRIDGE: wave roles A inf/mis/cav=%s/%s/%s  B=%s/%s/%s"
            % (
                ra.get("infantry"),
                ra.get("missile"),
                ra.get("cavalry"),
                rb.get("infantry"),
                rb.get("missile"),
                rb.get("cavalry"),
            )
        )
        blog.event(
            "prepare_mb",
            ok=bool(patched.get("ok")),
            men_a=meta_mb.get("army_a_men"),
            men_b=meta_mb.get("army_b_men"),
            roles_a=ra,
            roles_b=rb,
            reason=patched.get("reason"),
        )
    except Exception as e:
        print("BRIDGE: prepare_mb failed:", e)
        blog.event("prepare_mb", ok=False, reason=str(e))
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
    print("BRIDGE: starting M&B (%s) - no UI clicks; user: Graj then Nowa gra" % config.MB_MODULE)
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
        print("BRIDGE: no battle_spec - skip result save")
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


def _set_low_priority():
    """Keep the bridge below games so detect passes do not fight the GPU/CPU."""
    try:
        import ctypes

        IDLE = 0x00000040
        BELOW = 0x00004000
        kernel32 = ctypes.windll.kernel32
        kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), BELOW)
    except Exception as e:
        print("BRIDGE: priority warn:", e)


def _install_hook(hook, box=None, swallow_any=False):
    hook.start()
    if swallow_any:
        hook.set_swallow_any()
    else:
        hook.set_hitbox(*box)
    hook.arm()


def _remove_hook(hook):
    if hook is None:
        return
    hook.disarm()
    hook.stop()


def _battle_rpy_mtime():
    path = config.RTW_BATTLE_RPY
    try:
        return os.path.getmtime(path) if os.path.isfile(path) else None
    except OSError:
        return None


def _start_battle_worker(state, x, y, box):
    blog.event("click_swallowed", x=x, y=y, box=box)

    def worker():
        try:
            time.sleep(0.2)
            win_input.tap_vk(win_input.VK_ESCAPE, pause=0.2)
            if not prepare_armies(state):
                blog.event("army_prep_failed")
                return
            blog.event(
                "mb_start",
                module=config.MB_MODULE,
                men_a=state.army_a["summary"]["men"] if state.army_a else None,
                men_b=state.army_b["summary"]["men"] if state.army_b else None,
            )
            launch_mb_for_armies(state)
            result = wait_mb_result(simulate=state.simulate_result)
            if not result:
                blog.event("mb_result_timeout")
                return
            blog.event("mb_result", **{k: result.get(k) for k in ("winner", "a_left", "b_left", "source")})
            on_mb_done(state, result)
            blog.event("return_done")
        finally:
            with state.lock:
                state.busy = False
                state.arm_source = None

    threading.Thread(target=worker, name="rb-battle", daemon=True).start()


def run_loop(simulate_result=None, once_demo=False, watch_rtw=True):
    global _active_hook
    _set_low_priority()
    print(DIFFERENCES)
    blog.rotate_for_new_run()
    blog.event("bridge_start", event_log=blog.log_path())
    print("BRIDGE: building prebattle fingerprints...")
    fps = detect_prebattle.build_fingerprints()
    blog.event(
        "fingerprints_ready",
        templates=len(fps),
        poll_sec=config.DETECT_POLL_SEC,
        crop_w=config.DETECT_CROP_W,
        crop_h=config.DETECT_CROP_H,
    )
    state = BridgeState()
    state.simulate_result = simulate_result
    state.arm_source = None  # "gdi" | "hotkey"
    hook = mouse_hook.MouseHook()
    hotkey = hotkey_arm.HotkeyArm()
    _active_hook = hook
    atexit.register(_cleanup_hook)
    hotkey.start()
    time.sleep(0.2)
    blog.event(
        "hotkey_listen",
        vk="F5",
        register_ok=hotkey.register_ok,
        register_err=hotkey.register_err,
        note="F5 backup; prefer GDI arm under Rome -ne",
    )
    print("BRIDGE: idle - open pre-battle scroll (GDI arms) or press F5. Next click swallowed.")
    print("BRIDGE: Recommended: start_romeblade.bat (Rome -ne, no Arm panel).")

    seen_rtw = False
    gone_since = None
    hook_up = False
    rpy_baseline = _battle_rpy_mtime()
    last_detect = 0.0
    import ctypes

    user32 = ctypes.windll.user32

    def arm_now(source, panel, swallow_any=True):
        nonlocal hook_up
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)
        box = detect_prebattle.begin_battle_hitbox(sw, sh, panel)
        if not swallow_any:
            box = (0, int(sh * 0.40), sw, sh)
        state.panel = panel
        state.armed = True
        state.arm_source = source
        _install_hook(hook, box=box, swallow_any=swallow_any)
        hook_up = True
        blog.event(
            "hook_armed",
            source=source,
            swallow_any=int(swallow_any),
            box=box if not swallow_any else "ANY",
        )

    def disarm_now(reason):
        nonlocal hook_up
        state.armed = False
        state.arm_source = None
        state.panel = None
        if hook_up:
            _remove_hook(hook)
            hook_up = False
            blog.event("hook_removed", reason=reason)

    def try_manual_arm(source):
        with state.lock:
            busy = state.busy
            armed = state.armed
        if busy:
            return
        blog.event("arm_request", source=source)
        if armed and hook_up:
            hook.set_swallow_any()
            hook.arm()
            state.arm_source = source
            blog.event("hook_rearmed", source=source, swallow_any=1)
        else:
            arm_now(
                source,
                {"detected": True, "x": 0, "y": 0, "tw": 0, "th": 0},
                swallow_any=True,
            )

    try:
        while True:
            # Arm paths: GDI scroll (below) or F5. No Arm panel UI.
            hotkey.poll_f5_async()
            if hotkey.take_press():
                try_manual_arm("hotkey_f5")

            # Swallow first; only then log a non-swallowed click (narrow box miss).
            if hook_up:
                swallowed = hook.take_swallow()
                if swallowed is None:
                    seen = hook.take_seen_click()
                    if seen is not None:
                        blog.event(
                            "click_seen_not_swallowed",
                            x=seen[0],
                            y=seen[1],
                            hint="press F5 for swallow-any, or use windowed -ne",
                        )
            else:
                swallowed = None

            if swallowed is not None:
                x, y = swallowed
                with state.lock:
                    if state.busy:
                        swallowed = None
                    else:
                        state.busy = True
                        state.armed = False
                        panel = state.panel
                if swallowed is not None:
                    _remove_hook(hook)
                    hook_up = False
                    state.arm_source = None
                    sw = user32.GetSystemMetrics(0)
                    sh = user32.GetSystemMetrics(1)
                    box = detect_prebattle.begin_battle_hitbox(sw, sh, panel)
                    _start_battle_worker(state, x, y, box)

            # Late signal: RTW started its own battle (Begin Battle not swallowed).
            rpy_now = _battle_rpy_mtime()
            if (
                rpy_now is not None
                and (rpy_baseline is None or rpy_now > rpy_baseline + 0.5)
                and not state.busy
            ):
                blog.event(
                    "MISS_rtw_battle_started",
                    battle_rpy_mtime=rpy_now,
                    armed=int(bool(state.armed)),
                    hook_up=int(hook_up),
                    hint="RTW got Begin Battle; F5+click or windowed bat next time",
                )
                rpy_baseline = rpy_now
                disarm_now("rtw_started_own_battle")

            rtw_alive = launchers.process_running("RomeTW.exe")
            if rtw_alive:
                if not seen_rtw:
                    blog.event("rtw_seen")
                    rpy_baseline = _battle_rpy_mtime()
                seen_rtw = True
                gone_since = None
                with state.lock:
                    busy = state.busy
                now = time.time()
                if not busy and (now - last_detect) >= config.DETECT_POLL_SEC:
                    last_detect = now
                    t0 = time.perf_counter()
                    match = detect_prebattle.poll_prebattle(fps)
                    dt = time.perf_counter() - t0
                    blog.event(
                        "detect",
                        ms=int(dt * 1000),
                        detected=bool(match.get("detected")),
                        score=round(float(match.get("score", 1e9)), 1),
                        gdi=match.get("gdi"),
                        mean=match.get("gdi_stats", {}).get("mean_rgb_sum"),
                    )
                    with state.lock:
                        if match.get("detected"):
                            if not state.armed and not state.busy:
                                # Swallow-any even on GDI hit - Begin Battle must not miss.
                                arm_now("gdi", match, swallow_any=True)
                            elif state.armed and hook_up and state.arm_source == "gdi":
                                state.panel = match
                        else:
                            if (
                                state.armed
                                and not state.busy
                                and state.arm_source == "gdi"
                            ):
                                disarm_now("gdi_lost")
            elif watch_rtw and seen_rtw:
                if gone_since is None:
                    gone_since = time.time()
                    blog.event("rtw_gone")
                    disarm_now("rtw_gone")
                elif time.time() - gone_since >= config.RTW_GONE_EXIT_SEC:
                    blog.event("bridge_exit", reason="rtw_closed")
                    break
            if once_demo:
                break
            # Fast poll for F5; detect stays on DETECT_POLL_SEC.
            time.sleep(0.05)
    except KeyboardInterrupt:
        blog.event("bridge_exit", reason="keyboard")
    finally:
        try:
            hotkey.stop()
        except Exception:
            pass
        _remove_hook(hook)
        _cleanup_hook()
        blog.event("cleanup_done")



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
