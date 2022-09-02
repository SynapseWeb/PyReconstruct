import sys
from PySide2.QtWidgets import QApplication
from PySide2.QtCore import Qt


###############################################################
# STOPGAP FOR WAYLAND QT ISSUE
# https://stackoverflow.com/questions/68417682/qt-and-opencv-app-not-working-in-virtual-environment

import os
from pathlib import Path

import PySide2
from PySide2.QtWidgets import QWidget
import cv2

os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.fspath(
    Path(PySide2.__file__).resolve().parent / "Qt" / "plugins"
)
#################################################################


from modules.gui.mainwindow import MainWindow

# adjust dpi scaling for high resolution monitors
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

# create and run applications
app = QApplication(sys.argv)
main_window = MainWindow()
app.exec_()
