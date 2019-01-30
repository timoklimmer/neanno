import config
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QPlainTextEdit,
)


class WorkerMessagesDialog(QDialog):
    """ A dialog to show messages from a parallel worker."""

    def __init__(self, parent=None, window_title="Messages"):
        super(WorkerMessagesDialog, self).__init__(parent)
        self.setWindowTitle(window_title)
        self.setWindowModality(Qt.ApplicationModal)
        layout = QVBoxLayout(self)

        # text edit
        self.textedit = QPlainTextEdit()
        layout.addWidget(self.textedit)

        # buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def acceptNewMessage(self, message):
        self.textedit.appendPlainText(message)

    @staticmethod
    def show(parent=None, window_title="Messages"):
        dialog = WorkerMessagesDialog(parent, window_title)
        result = dialog.exec_()
