"""Always-on-top Arm panel — works when F5 never reaches the bridge.

Exclusive fullscreen RTW eats keyboard focus; RegisterHotKey often never fires
(log proof: long detect loop, zero hotkey_f5). This small window stays visible
after Alt+Tab / beside windowed (-ne) Rome. Clicking UZBRÓJ writes a flag file
the bridge polls, then arms swallow-any for the next left-click.

Run: pythonw -m tools.romeblade_bridge.arm_panel
"""
from __future__ import print_function

import os
import sys
import time

# Allow `python -m tools.romeblade_bridge.arm_panel`
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    __package__ = "tools.romeblade_bridge"

from . import config


def flag_path():
    d = os.path.join(config.REPO_ROOT, "out")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "arm_request.flag")


def write_arm_flag():
    path = flag_path()
    with open(path, "w", encoding="utf-8") as f:
        f.write("%.3f\n" % time.time())
    return path


def main():
    try:
        import tkinter as tk
        from tkinter import font as tkfont
    except ImportError:
        print("tkinter missing — write flag via: echo > out\\arm_request.flag")
        write_arm_flag()
        return 1

    root = tk.Tk()
    root.title("RomeBlade — Uzbrój")
    root.attributes("-topmost", True)
    root.geometry("420x220+40+40")
    root.configure(bg="#1a1a1a")
    status = tk.StringVar(value="1) Zwój w Rome  2) UZBRÓJ  3) Begin Battle")

    def on_arm():
        write_arm_flag()
        status.set("UZBROJONE — wróć do Rome i kliknij Begin Battle\n(następny LPM zostanie połknięty)")
        btn.config(bg="#2d6a2d", text="UZBROJONE ✓")

    fnt = tkfont.Font(family="Segoe UI", size=16, weight="bold")
    btn = tk.Button(
        root,
        text="UZBRÓJ\n(połyka następny klik)",
        font=fnt,
        command=on_arm,
        bg="#6a2d2d",
        fg="white",
        activebackground="#8a3d3d",
        height=3,
    )
    btn.pack(fill="both", expand=True, padx=12, pady=12)
    lbl = tk.Label(
        root, textvariable=status, bg="#1a1a1a", fg="#dddddd", font=("Segoe UI", 10)
    )
    lbl.pack(fill="x", padx=12, pady=(0, 12))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
