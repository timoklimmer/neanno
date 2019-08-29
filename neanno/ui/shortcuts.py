from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QMessageBox, QShortcut

# TODO: add Mac shortcuts

SHORTCUT_SUBMIT_NEXT_BEST = "Ctrl+Return"
SHORTCUT_SUBMIT_NEXT = "Ctrl+Shift+Return"
SHORTCUT_MARK_ALL_AS_ANNOTATED = "Ctrl+M"
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
SHORTCUT_REVERT_CHANGES = "Ctrl+E"
SHORTCUT_REMOVE_ANNOTATION_AT_CURSOR = "Ctrl+R"
SHORTCUT_REMOVE_ALL_ANNOTATIONS_OF_CURRENT_TEXT = "Ctrl+D"
SHORTCUT_REMOVE_ALL_ANNOTATIONS_FROM_DATASET = "Ctrl+I"


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
    message += shortcut_fragment("Submit/Next", SHORTCUT_SUBMIT_NEXT)
    message += shortcut_fragment("Mark all texts as annotated", SHORTCUT_MARK_ALL_AS_ANNOTATED)
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
        "Remove all annotations of current text",
        SHORTCUT_REMOVE_ALL_ANNOTATIONS_OF_CURRENT_TEXT,
    )
    message += shortcut_fragment(
        "Remove all annotations from the dataset", SHORTCUT_REMOVE_ALL_ANNOTATIONS_FROM_DATASET
    )
    message += shortcut_fragment(
        "Revert annotation changes", SHORTCUT_REVERT_CHANGES
    )
    message += "</table>"

    msg = QMessageBox(parent)
    msg.setTextFormat(Qt.RichText)
    msg.setIcon(QMessageBox.Information)
    msg.setText(message)
    msg.setWindowTitle("Shortcuts")
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()
