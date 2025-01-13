import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QPlainTextEdit, QVBoxLayout, QWidget, QLabel
from PySide6.QtCore import QProcess


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.p = None

        self.setWindowTitle("Zarr converter")
        self.setGeometry(100, 100, 600, 800)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)

        l = QVBoxLayout()
        self.heading = QLabel("Do not close this window until the process is done.", self)
        l.addWidget(self.heading)
        l.addWidget(self.text)

        w = QWidget()
        w.setLayout(l)

        self.setCentralWidget(w)

    def message(self, s):
        self.text.appendPlainText(s)

    def start_process(self, cmd, args):
        
        if self.p is None:  # No process running.

            self.p = QProcess()
            
            self.p.readyReadStandardOutput.connect(self.handle_stdout)
            self.p.readyReadStandardError.connect(self.handle_stderr)
            self.p.stateChanged.connect(self.handle_state)
            self.p.finished.connect(self.process_finished)
            
            self.p.start(cmd, args)

    def handle_stderr(self):
        
        data = self.p.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        self.message(stderr)

    def handle_stdout(self):
        
        data = self.p.readAllStandardOutput()
        stdout = bytes(data).decode("utf8").strip()
        self.message(stdout)
        
    def handle_state(self, state):
        
        states = {
            QProcess.NotRunning : 'Not running',
            QProcess.Starting   : 'Starting',
            QProcess.Running    : 'Running',
        }
        state_name = states[state]
        #self.message(f"State changed: {state_name}")

    def process_finished(self):
        
        self.message("Zarr processing finished.")

        if sys.platform == "linux":

            self.message("Changing file permissions...")

            zarr = sys.argv[3]

            os.system(f"find {zarr} -type d -exec chmod g+rwx {{}} +")
            os.system(f"find {zarr} -type f -exec chmod g+rw {{}} +")
        
        self.message("You can close this window.")
        self.heading.setText("Zarr processing done. You can safely close this window now.")
        
        self.p = None


if __name__ == "__main__":

    args = sys.argv
    python_bin = sys.executable
    dir_scripts = Path(__file__).parent
    
    if sys.argv[1] == "convert_zarr":

        zarr_converter = str(dir_scripts / "convert_zarr/zarree-2.py")
        
    elif args[1] == "create_ng_zarr":

        zarr_converter = str(dir_scripts / "create_ng_zarr/create_ng_zarr.py")
    
    zarr_args = [zarr_converter] + args[2:]
    
    app = QApplication(args)
    window = MainWindow()
    window.show()
    window.start_process(python_bin, zarr_args)
    app.exec()
