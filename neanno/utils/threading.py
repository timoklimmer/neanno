from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import time
import traceback, sys


class ParallelWorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.

    Supported signals are:

    completed
        No data

    error
        `tuple` (exctype, value, traceback.format_exc() )

    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress

    message
        `str` indicating a message from the worker while it works

    """

    completed = pyqtSignal()
    failure = pyqtSignal(tuple)
    success = pyqtSignal(object)
    progress = pyqtSignal(int)
    message = pyqtSignal(str)


class ParallelWorker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(ParallelWorker, self).__init__()

        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = ParallelWorkerSignals()

        self.kwargs["progress_callback"] = self.signals.progress
        self.kwargs["message_callback"] = self.signals.message

    @pyqtSlot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.failure.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.success.emit(result)
        finally:
            self.signals.completed.emit()
