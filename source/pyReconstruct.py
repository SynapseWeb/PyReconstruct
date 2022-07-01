import sys
from PySide2.QtWidgets import QApplication
from PySide2.QtCore import Qt

from mainwindow import MainWindow

# adjust dpi scaling
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

app = QApplication(sys.argv)
main_window = MainWindow()
app.exec_()