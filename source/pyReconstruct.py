import sys
from PySide2.QtWidgets import QApplication
from PySide2.QtCore import Qt

from mainwindow import MainWindow

# adjust dpi scaling for high resolution monitors
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

# create and run applications
app = QApplication(sys.argv)
main_window = MainWindow()
app.exec_()