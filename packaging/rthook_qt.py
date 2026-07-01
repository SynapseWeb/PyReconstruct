"""PyInstaller runtime hook (runs before app code in the frozen build).

Drop any QT_QPA_PLATFORM_PLUGIN_PATH inherited from the build machine or a
parent process. PyInstaller's PySide6 hook already points Qt at the bundled
plugins; a stale value here would break the platform plugin at launch.
"""

import os

os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
