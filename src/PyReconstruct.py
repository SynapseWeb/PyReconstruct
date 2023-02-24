import sys
from PySide6.QtWidgets import QApplication
from modules.gui.main_window import MainWindow

# STOPGAP FOR WAYLAND QT ISSUE
# https://stackoverflow.com/questions/68417682/qt-and-opencv-app-not-working-in-virtual-environment

import os
import PySide6
from pathlib import Path

ps6_fp = PySide6.__file__
plugin_path = os.fspath(Path(ps6_fp).resolve().parent / "Qt" / "plugins")
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path

# END STOPGAP

# Create and run applications
app = QApplication(sys.argv)
main_window = MainWindow(sys.argv)
app.exec()
