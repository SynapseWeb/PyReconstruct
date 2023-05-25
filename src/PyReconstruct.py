import os
import sys
import PySide6
from pathlib import Path
from PySide6.QtWidgets import QApplication

# STOPGAP FOR WAYLAND QT ISSUE
# https://stackoverflow.com/questions/68417682/qt-and-opencv-app-not-working-in-virtual-environment

ps6_fp = PySide6.__file__
plugin_path = os.fspath(Path(ps6_fp).resolve().parent / "Qt" / "plugins")
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path

# END STOPGAP

# create the Qt Application
app = QApplication(sys.argv)

# run program until user closes without restart
run = True
while run:
    from modules.gui.main import MainWindow
    main_window = MainWindow(sys.argv)
    app.exec()
    if main_window.restart_mainwindow:
        if not main_window.series.isWelcomeSeries():
            if len(sys.argv) < 2:
                sys.argv.append("")
            sys.argv[1] = main_window.series.jser_fp  # load the series being worked on
    else:
        run = False
