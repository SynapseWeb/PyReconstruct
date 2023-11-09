import os
import sys
import PySide6
import importlib
from pathlib import Path
from PySide6.QtWidgets import QApplication

if __name__ == "__main__":
    # necessary to import correctly given run.py location
    here_dir = os.path.dirname(os.path.realpath(__file__))
    sys.path.append(
        os.path.dirname(here_dir)
    )

import PyReconstruct.modules.gui.main as main

def runPyReconstruct(filename=None):
    print("Hello Andrea :)")
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
        main_window = main.MainWindow(filename)
        app.exec()

        # user has closed the main window
        if main_window.restart_mainwindow:
            if not main_window.series.isWelcomeSeries():
                filename = main_window.series.jser_fp
            # reload all of the written code
            for module_name, module in list(sys.modules.items()):
                if module_name.startswith("modules"):
                    importlib.reload(module)
        else:
            run = False

if __name__ == "__main__":
    # get filename from argv
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = None
    runPyReconstruct(filename)