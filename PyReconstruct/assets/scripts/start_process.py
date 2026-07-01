import sys
import time
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPlainTextEdit, QVBoxLayout, QWidget, QLabel,
    QProgressBar,
)
from PySide6.QtCore import QProcess, Qt


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.p = None
        self._stdout_buf = ""        # buffers partial (unterminated) stdout lines
        self._progress_start = None  # set when the first progress total arrives

        self.setWindowTitle("Zarr converter")
        self.setGeometry(100, 100, 600, 800)

        self.heading = QLabel("Do not close this window until the process is done.", self)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate until a total is reported
        self.progress.setTextVisible(True)

        self.eta = QLabel("", self)
        self.eta.setAlignment(Qt.AlignCenter)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)

        l = QVBoxLayout()
        l.addWidget(self.heading)
        l.addWidget(self.progress)
        l.addWidget(self.eta)
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
        self._stdout_buf += bytes(data).decode("utf8", errors="replace")

        # only act on complete lines; keep any trailing partial line buffered
        *lines, self._stdout_buf = self._stdout_buf.split("\n")

        for line in lines:
            if line.startswith("@@PROGRESS@@"):
                self.update_progress(line)
            elif line.strip():
                self.message(line)

    def update_progress(self, line):
        """Drive the progress bar / ETA from a converter progress marker.

        Markers: '@@PROGRESS@@ TOTAL <n>' and '@@PROGRESS@@ STEP <done> <n>'.
        """
        parts = line.split()
        if len(parts) < 3:
            return

        kind = parts[1]

        if kind == "TOTAL":
            total = int(parts[2])
            self.progress.setRange(0, total)
            self.progress.setValue(0)
            self._progress_start = time.monotonic()
            self.eta.setText(f"0 / {total} — estimating time remaining…")

        elif kind == "STEP" and len(parts) >= 4:
            done, total = int(parts[2]), int(parts[3])
            if self.progress.maximum() != total:
                self.progress.setRange(0, total)
            self.progress.setValue(done)
            self.eta.setText(self._eta_text(done, total))

    def _eta_text(self, done, total):
        if not self._progress_start or done <= 0:
            return f"{done} / {total}"
        elapsed = time.monotonic() - self._progress_start
        remaining = (elapsed / done) * (total - done)
        return f"{done} / {total} — ~{self._format_duration(remaining)} remaining"

    @staticmethod
    def _format_duration(seconds):
        seconds = int(max(0, seconds))
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)
        if hours:
            return f"{hours}h {minutes:02d}m {secs:02d}s"
        if minutes:
            return f"{minutes}m {secs:02d}s"
        return f"{secs}s"
        
    def handle_state(self, state):
        
        states = {
            QProcess.NotRunning : 'Not running',
            QProcess.Starting   : 'Starting',
            QProcess.Running    : 'Running',
        }
        state_name = states[state]
        #self.message(f"State changed: {state_name}")

    def process_finished(self, exit_code=0, exit_status=None):

        # flush any trailing buffered output that lacked a newline
        if self._stdout_buf.strip():
            self.message(self._stdout_buf.strip())
        self._stdout_buf = ""

        if exit_code == 0:

            # show the bar as complete
            if self.progress.maximum() == 0:  # was still indeterminate
                self.progress.setRange(0, 1)
            self.progress.setValue(self.progress.maximum())
            self.eta.setText("Complete.")

            self.message("Zarr processing finished.")
            self.message("You can close this window.")
            self.heading.setText("Zarr processing done. You can safely close this window now.")

        else:

            self.eta.setText("Stopped before completion.")
            self.message(f"Zarr processing exited with code {exit_code}.")
            self.heading.setText("Zarr processing did not finish — see messages above.")

        self.p = None


if __name__ == "__main__":

    args = sys.argv
    python_bin = sys.executable
    dir_scripts = Path(__file__).parent
    
    if sys.argv[1] == "convert_zarr":

        zarr_converter = str(dir_scripts / "convert_zarr/zarree-2.py")
        
    elif args[1] == "create_ng_zarr":

        zarr_converter = str(dir_scripts / "create_ng_zarr/create_ng_zarr.py")
    
    # In a frozen build the exe can't run a .py directly; run.py intercepts the
    # "__run_script__" sentinel and runs the script via runpy.
    if getattr(sys, "frozen", False):
        zarr_args = ["__run_script__", zarr_converter] + args[2:]
    else:
        zarr_args = [zarr_converter] + args[2:]

    app = QApplication(args)
    window = MainWindow()
    window.show()
    window.start_process(python_bin, zarr_args)
    app.exec()
