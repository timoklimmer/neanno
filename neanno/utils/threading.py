import sys
import time
import traceback

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class ParallelWorkerSignals(QObject):
    """
    Defines the signals (callbacks) available from a running worker thread.

    Supported callbacks are:

    message
        `str` indicating a message from the worker while it works

    progress
        `float` indicating % progress

    completed
        has no parameters

    success
        `object` data returned from processing, anything

    failure
        `tuple` (exctype, value, traceback.format_exc())

    """

    completed = pyqtSignal()
    failure = pyqtSignal(tuple)
    success = pyqtSignal(object)
    progress = pyqtSignal(int)
    message = pyqtSignal(str)

    @pyqtSlot(str)
    def default_message_handler(message):
        print(message)

    @pyqtSlot(float)
    def default_progress_handler(percent_completed):
        print("{:.2%}".format(percent_completed))

    @pyqtSlot()
    def default_completed_handler():
        print("Done.")

    @pyqtSlot(object)
    def default_success_handler(result):
        print("=> Success")

    @pyqtSlot(tuple)
    def default_failure_handler(exception_info):
        print("=> Failed to run a parallel job.")
        print(exception_info[0])
        print(exception_info[1])
        print(exception_info[2])

    def default_slots():
        result = ParallelWorkerSignals()
        result.message.connect(
            ParallelWorkerSignals.default_message_handler, type=Qt.DirectConnection
        )
        result.progress.connect(
            ParallelWorkerSignals.default_progress_handler, type=Qt.DirectConnection
        )
        result.completed.connect(
            ParallelWorkerSignals.default_completed_handler, type=Qt.DirectConnection
        )
        result.success.connect(
            ParallelWorkerSignals.default_success_handler, type=Qt.DirectConnection
        )
        result.failure.connect(
            ParallelWorkerSignals.default_failure_handler, type=Qt.DirectConnection
        )
        return result


class ParallelWorker(QRunnable):
    def __init__(self, fn, signals, *args, **kwargs):
        super(ParallelWorker, self).__init__()

        self.fn = fn
        self.signals = signals
        self.args = args
        self.kwargs = kwargs
        self.kwargs["signals"] = self.signals

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
