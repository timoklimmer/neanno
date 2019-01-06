from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QMessageBox, QShortcut


SHORTCUT_SUBMIT_NEXT_BEST = "Ctrl+Return"
SHORTCUT_BACKWARD = "Ctrl+Left"
SHORTCUT_FORWARD = "Ctrl+Right"
SHORTCUT_FIRST = "Ctrl+B"
SHORTCUT_PREVIOUS = "Ctrl+P"
SHORTCUT_NEXT = "Ctrl+N"
SHORTCUT_LAST = "Ctrl+L"
SHORTCUT_GOTO = "Ctrl+G"
SHORTCUT_SEARCH = "Ctrl+F"
SHORTCUT_UNDO = "Ctrl+Z"
SHORTCUT_REDO = "Ctrl+Y"
SHORTCUT_REMOVE_ANNOTATION_AT_CURSOR = "Ctrl+R"
SHORTCUT_REMOVE_ALL_FOR_CURRENT_TEXT = "Ctrl+D"
SHORTCUT_RESET_IS_ANNOTATED_FLAG = "Ctrl+K"
SHORTCUT_RESET_ALL_IS_ANNOTATED_FLAGS = "Ctrl+I"


def register_shortcut(parent, key_sequence, function):
    shortcut = QShortcut(
        QKeySequence(key_sequence), parent, context=Qt.ApplicationShortcut
    )
    shortcut.activated.connect(function)


def show_shortcuts_dialog(parent):
    def shortcut_fragment(label, shortcut):
        return (
            "<tr><td style="
            "padding-right:20"
            ">{}</td><td>{}</td></tr>".format(label, shortcut)
        )

    message = "<table>"
    message += shortcut_fragment("Submit/Next Best", SHORTCUT_SUBMIT_NEXT_BEST)
    message += shortcut_fragment("Backward", SHORTCUT_BACKWARD)
    message += shortcut_fragment("Forward", SHORTCUT_FORWARD)
    message += shortcut_fragment("First", SHORTCUT_FIRST)
    message += shortcut_fragment("Previous", SHORTCUT_PREVIOUS)
    message += shortcut_fragment("Next", SHORTCUT_NEXT)
    message += shortcut_fragment("Last", SHORTCUT_LAST)
    message += shortcut_fragment("Goto", SHORTCUT_GOTO)
    message += shortcut_fragment("Search", SHORTCUT_SEARCH)
    message += shortcut_fragment("Undo", SHORTCUT_UNDO)
    message += shortcut_fragment("Redo", SHORTCUT_REDO)
    message += shortcut_fragment(
        "Remove annotation at cursor", SHORTCUT_REMOVE_ANNOTATION_AT_CURSOR
    )
    message += shortcut_fragment(
        "Remove all annotations/labels for current text",
        SHORTCUT_REMOVE_ALL_FOR_CURRENT_TEXT,
    )
    message += shortcut_fragment(
        "Reset Is Annotated flag", SHORTCUT_RESET_IS_ANNOTATED_FLAG
    )
    message += shortcut_fragment(
        "Reset all Is Annotated flags", SHORTCUT_RESET_ALL_IS_ANNOTATED_FLAGS
    )
    message += "</table>"

    msg = QMessageBox(parent)
    msg.setTextFormat(Qt.RichText)
    msg.setIcon(QMessageBox.Information)
    msg.setText(message)
    msg.setWindowTitle("Shortcuts")
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()
