"""Paths and tunables for the RomeBlade bridge."""
from __future__ import print_function

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

RTW_ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold"
RTW_EXE = os.path.join(RTW_ROOT, "RomeTW.exe")
RTW_SAVES = os.path.join(RTW_ROOT, "saves")

MB_ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\Mount and Blade"
MB_EXE = os.path.join(MB_ROOT, "mount&blade.exe")
MB_LOG = os.path.join(MB_ROOT, "rgl_log.txt")
MB_MODULE = "RomeBladeRTS"
MB_MODULE_DIR = os.path.join(MB_ROOT, "Modules", MB_MODULE)

# Trigger save: user / bridge writes or overwrites only this NEW name.
# Never touch RomaAroma / Autosave / niunia / other player saves.
BRIDGE_SAVE_NAME = "romeblade_fight.sav"
RESULT_SAVE_NAME = "romeblade_result.sav"
E1_SAVE_NAME = "most_proba.sav"

# Global hotkey (virtual-key). F5 = 0x74. Used when the bridge process is running.
HOTKEY_VK = 0x74
HOTKEY_ID = 1

# Polling
SAVE_POLL_SEC = 0.5
LOG_POLL_SEC = 0.5

# Result line written by RomeBladeRTS into rgl_log.txt (spaces may be underscores).
RESULT_TAG = "ROME BLADE RESULT|"
RESULT_TAG_ALT = "ROME_BLADE_RESULT|"

# Protected saves — bridge must never overwrite / delete these.
PROTECTED_SAVES = frozenset(
    {
        "RomaAroma.sav",
        "Autosave.sav",
        "niunia.sav",
    }
)
