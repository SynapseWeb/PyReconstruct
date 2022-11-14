import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt


###############################################################
# STOPGAP FOR WAYLAND QT ISSUE
# https://stackoverflow.com/questions/68417682/qt-and-opencv-app-not-working-in-virtual-environment

import os
from pathlib import Path

import PySide6
from PySide6.QtWidgets import QWidget
import cv2

os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.fspath(
    Path(PySide6.__file__).resolve().parent / "Qt" / "plugins"
)
#################################################################


from modules.gui.main_window import MainWindow

# create and run applications
app = QApplication(sys.argv)
main_window = MainWindow()
app.exec()
