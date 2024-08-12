"""

Threading source:

https://www.pythonguis.com/tutorials/multithreading-pyside6-applications-qthreadpool/

"""

import sys
import traceback

from PySide6.QtWidgets import QProgressDialog, QProgressBar, QApplication, QLabel

from PyReconstruct.modules.gui.utils import getProgbar

from PySide6.QtCore import (
    QRunnable,
    Slot,
    Signal,
    QObject,
    QThreadPool,
    Qt
)


class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    '''
    error = Signal(tuple)
    result = Signal(tuple)
    finished = Signal()


class Worker(QRunnable, QObject):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        '''
        Initialise the runner function with passed args.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()

class ThreadPool(QThreadPool):
    """Extended from QThreadPool class."""

    def __init__(self):
        """Overwritten from parent class.
        
        Params:
            update (function): the update functino for a loading bar
        """
        super().__init__()
        if self.maxThreadCount() > 10:
            self.setMaxThreadCount(10)
        self.workers = []
        self.n_finished = 0
        self.finished_fn = None

    def createWorker(self, fn, *args):
        """Create and return a worker object.
        
            Params:
                fn (function): the function for the worker to run
                *args: the args to be passed into the function"""
        w = Worker(fn, *args)
        self.workers.append(w)
        return w

class MemoryInt():

    def __init__(self):
        self.n = 0
    
    def inc(self):
        self.n += 1

class ThreadPoolProgBar(ThreadPool):

    def startAll(self, text="", status_bar=None):
        final_value = len(self.workers)
        maximum = final_value if final_value >= 4 else 0
        if status_bar is None:
            progbar = getProgbar(text, cancel=False, maximum=maximum)
        else:  # custom progbar for status bar
            lbl = QLabel()
            lbl.setText(text)
            progbar = QProgressBar()
            progbar.setMaximumHeight(status_bar.height() - 6)
            progbar.setMinimum(0)
            progbar.setMaximum(0)
            status_bar.addPermanentWidget(lbl)
            status_bar.addPermanentWidget(progbar)
        
        counter = MemoryInt()
        for worker in self.workers:
            QApplication.processEvents()
            worker.signals.finished.connect(counter.inc)
            worker.signals.finished.connect(lambda : progbar.setValue(counter.n))
            self.start(worker)
        
        while counter.n < final_value:
            QApplication.processEvents()
        
        if maximum == 0:
            progbar.close()
        if status_bar:
            lbl.close()
