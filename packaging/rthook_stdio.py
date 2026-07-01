"""PyInstaller runtime hook: give the windowed (no-console) build real stdio.

In a --windowed / --noconsole PyInstaller build, sys.stdout and sys.stderr are
None, so any library that writes to or flushes them at import time crashes --
e.g. vedo's __init__ calls sys.stdout.flush(), giving
    AttributeError: 'NoneType' object has no attribute 'flush'.

Point the None streams at a log file under the temp dir (so output/tracebacks
are still capturable for debugging), falling back to os.devnull. Only touches
streams that are actually None, so console / source runs are unaffected. This
hook is listed FIRST in the spec's runtime_hooks so it runs before any such
import.
"""

import os
import sys
import tempfile

if sys.stdout is None or sys.stderr is None:
    try:
        _sink = open(
            os.path.join(tempfile.gettempdir(), "pyreconstruct-frozen.log"),
            "a", buffering=1, encoding="utf-8", errors="replace",
        )
    except Exception:
        _sink = open(os.devnull, "w")
    if sys.stdout is None:
        sys.stdout = _sink
    if sys.stderr is None:
        sys.stderr = _sink
