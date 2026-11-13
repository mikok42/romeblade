"""Append-only bridge event log with timestamps (one line per step)."""
from __future__ import print_function

import os
import threading
import time
from datetime import datetime

from . import config

_lock = threading.Lock()
_path = None


def log_path():
    global _path
    if _path is None:
        d = os.path.join(config.REPO_ROOT, "out")
        os.makedirs(d, exist_ok=True)
        _path = os.path.join(d, "bridge_events.log")
    return _path


def event(kind, **fields):
    """Write `YYYY-mm-dd HH:MM:SS.mmm KIND key=val ...` and mirror to stdout."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.") + "%03d" % (
        int(time.time() * 1000) % 1000
    )
    parts = ["%s=%s" % (k, fields[k]) for k in sorted(fields)]
    line = "%s %s %s" % (ts, kind, " ".join(parts) if parts else "")
    line = line.rstrip()
    with _lock:
        with open(log_path(), "a", encoding="utf-8") as f:
            f.write(line + "\n")
    print("BRIDGE_EVT:", line)
    return line
