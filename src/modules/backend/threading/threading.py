import sys
import traceback

from PySide6.QtWidgets import QProgressDialog

from modules.gui.utils import mainwindow

from PySide6.QtCore import (
    QRunnable,
    Slot,
    Signal,
    QObject,
    QThreadPool,
    Qt
)

# THREADING SOURCE: https://www.pythonguis.com/tutorials/multithreading-pyside6-applications-qthreadpool/

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


class Worker(QRunnable):
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
    
    def count(self):
        """Keep track of the number of finished workers."""
        self.n_finished += 1
        if self.n_finished == len(self.workers) and self.finished_fn is not None:
            self.finished_fn(
                *self.finished_fn_args
            )
    
    def startAll(self, finished_fn, *finished_fn_args):
        """Start all of the workers in the threadpool.
        
            Params:
                finished_fn (function): the function to run when all the threads are done
        """
        self.finished_fn = finished_fn
        self.finished_fn_args = finished_fn_args
        for w in self.workers:
            w.signals.finished.connect(self.count)
            self.start(w)

class MemoryInt():

    def __init__(self):
        self.n = 0
    
    def inc(self):
        self.n += 1

class ThreadPoolProgBar(ThreadPool):

    def startAll(self, text):
        final_value = len(self.workers)
        progbar = QProgressDialog(
                text,
                "Cancel",
                0,
                final_value,
                mainwindow
            )
        progbar.setMinimumDuration(1500)
        progbar.setWindowTitle(" ")
        progbar.setWindowModality(Qt.WindowModal)
        progbar.setCancelButton(None)
        counter = MemoryInt()
        for worker in self.workers:
            fn = worker.fn
            def wrapper(*args):
                fn(*args)
                counter.inc()
            worker.fn = wrapper
            self.start(worker)
        
        while counter.n < final_value:
            progbar.setValue(counter.n)
        