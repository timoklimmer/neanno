import sys
import time
import traceback

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


class ParallelWorker(QRunnable):
    """Runs a function in parallel to the UI thread."""

    def __init__(self, fn, signals_handler, *args, **kwargs):
        super(ParallelWorker, self).__init__()

        self.fn = fn
        self.signals_handler = signals_handler
        self.args = args
        self.kwargs = kwargs
        self.kwargs["signals"] = self.signals_handler

    @pyqtSlot()
    def run(self):
        try:
            self.signals_handler.started.emit()
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals_handler.failure.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals_handler.success.emit(result)
        finally:
            self.signals_handler.completed.emit()


class ParallelWorkerSignals(QObject):
    """
    Defines the available signals (callbacks) for a function that is run in parallel.

    Supported callbacks are:

    started
        has no parameters

    message
        `str` = a message from the worker while it works

    progress
        `float` = progress so far (value between 0 and 1)

    completed
        has no parameters

    success
        `object` result returned from processing, can be anything

    failure
        `tuple` (exctype, value, traceback.format_exc())

    """

    started = pyqtSignal()
    message = pyqtSignal(str)
    progress = pyqtSignal(float)
    completed = pyqtSignal()
    success = pyqtSignal(object)
    failure = pyqtSignal(tuple)


class ConsoleSignalsHandler(ParallelWorkerSignals):
    """Prints all received signals to the console."""

    def __init__(self):
        super().__init__()
        self.started.connect(
            ConsoleSignalsHandler.handle_started, type=Qt.DirectConnection
        )
        self.message.connect(
            ConsoleSignalsHandler.handle_message, type=Qt.DirectConnection
        )
        self.progress.connect(
            ConsoleSignalsHandler.handle_progress, type=Qt.DirectConnection
        )
        self.completed.connect(
            ConsoleSignalsHandler.handle_completed, type=Qt.DirectConnection
        )
        self.success.connect(
            ConsoleSignalsHandler.handle_success, type=Qt.DirectConnection
        )
        self.failure.connect(
            ConsoleSignalsHandler.handle_failure, type=Qt.DirectConnection
        )

    @pyqtSlot()
    def handle_started():
        pass

    @pyqtSlot(str)
    def handle_message(message):
        print(message)

    @pyqtSlot(float)
    def handle_progress(percent_completed):
        print("{:.2%}".format(percent_completed))

    @pyqtSlot()
    def handle_completed():
        print("Done.")

    @pyqtSlot(object)
    def handle_success(result):
        print("=> Success")

    @pyqtSlot(tuple)
    def handle_failure(exception_info):
        print("=> Failed to run a parallel job.")
        print(exception_info[0])
        print(exception_info[1])
        print(exception_info[2])
