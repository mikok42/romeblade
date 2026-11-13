"""Paths and tunables for the RomeBlade bridge."""
from __future__ import print_function

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

RTW_ROOT = r"C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold"
RTW_EXE = os.path.join(RTW_ROOT, "RomeTW.exe")
RTW_SAVES = os.path.join(RTW_ROOT, "saves")
# Appears only AFTER Begin Battle reaches RTW — late miss signal, not a pre-arm cue.
RTW_BATTLE_RPY = os.path.join(RTW_ROOT, "temp", "battle.rpy")

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

# RTW campaign quicksave slot (community + hotseat docs: quicksave.sav).
# keys.dat binds save_stratmap / load_stratmap on strat_ui; FAQ: Ctrl+S / Ctrl+L.
# In-game reload-after-replace is UNVERIFIED — see quicksave.py.
QUICKSAVE_NAME = "quicksave.sav"
QUICKSAVE_BACKUP_PREFIX = "rb_qs_backup_"

# Global hotkey (virtual-key). F5 = 0x74. Used when the bridge process is running.
HOTKEY_VK = 0x74
HOTKEY_ID = 1

# Polling
SAVE_POLL_SEC = 0.5
LOG_POLL_SEC = 0.5
# Pre-battle scroll detect — keep rare; full GDI grabs stutter the machine.
DETECT_POLL_SEC = 1.5
# Center crop for detect (scroll sits mid-screen). Smaller = cheaper BitBlt/match.
DETECT_CROP_W = 960
DETECT_CROP_H = 540
DETECT_TEMPLATES = 2
DETECT_STRIDE = 24
DETECT_FP_STEP = 12
# After RTW has been seen once, exit bridge this many seconds after it vanishes.
RTW_GONE_EXIT_SEC = 3.0

# Result line written by RomeBladeRTS into rgl_log.txt (spaces may be underscores).
RESULT_TAG = "ROME BLADE RESULT|"
RESULT_TAG_ALT = "ROME_BLADE_RESULT|"

# Protected saves — bridge must never overwrite / delete these.
# quicksave.sav is NOT listed: bridge may replace it only after copying aside.
PROTECTED_SAVES = frozenset(
    {
        "RomaAroma.sav",
        "Autosave.sav",
        "niunia.sav",
    }
)
