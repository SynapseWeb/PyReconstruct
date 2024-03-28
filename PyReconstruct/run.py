import os, sys, importlib
from pathlib import Path

import PySide6
from PySide6.QtWidgets import QApplication


if __name__ == "__main__":
    
    # set up imports for run.py location
    run_script = Path(__file__)
    pypath = str(run_script.parents[1])
    sys.path.append(pypath)


import PyReconstruct.modules.gui.main as main


def runPyReconstruct(filename=None):

    # Stopgap for Wayland Qt issue
    # stackoverflow.com/questions/68417682/qt-and-opencv-app-not-working-in-virtual-environment
    ps6_dir = Path(PySide6.__file__).parent
    qt_plugins = ps6_dir / "Qt/plugins"
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(qt_plugins)

    # create the Qt Application
    app = QApplication(sys.argv)

    # run program until user closes without restart
    run = True

    while run:

        main_window = main.MainWindow(filename)
        app.exec()

        # user has closed the main window
        if main_window.restart_mainwindow:  # restart requested

            if not main_window.series.isWelcomeSeries():
                filename = main_window.series.jser_fp

            # reload PyReconstruct modules
            loaded_modules = list(sys.modules.items())
            for module_name, module in loaded_modules:
                if module_name.startswith("PyReconstruct.modules"):
                    importlib.reload(module)
                    
        else:  # no restart requested

            run = False


if __name__ == "__main__":

    if len(sys.argv) > 1:  # get filename from argv

        filename = sys.argv[1]

    else:
        
        filename = None
        
    runPyReconstruct(filename)
