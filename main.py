import sys

from PyQt5 import QtCore
from PyQt5.QtCore import QRegularExpression, Qt, pyqtSlot
from PyQt5.QtGui import (QColor, QFont, QKeySequence, QSyntaxHighlighter,
                         QTextCharFormat)
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QGridLayout,
                             QGroupBox, QLabel, QMainWindow, QPlainTextEdit,
                             QProgressBar, QPushButton, QShortcut, QVBoxLayout,
                             QWidget)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


class AnnotationDialog(QMainWindow):
    def __init__(self, named_entity_definitions):
        super().__init__()
        self.named_entity_definitions = named_entity_definitions
        self.layout_controls()
        self.wire_shortcuts()
        self.show()

    def layout_controls(self):
        # window
        self.setWindowTitle('Annotate entities')
        screen = QDesktopWidget().screenGeometry()
        self.setGeometry(0, 0, screen.width() * .75, screen.height() * .75)
        mysize = self.geometry()
        hpos = (screen.width() - mysize.width()) / 2
        vpos = (screen.height() - mysize.height()) / 2
        self.move(hpos, vpos)

        # progress bar
        progress_bar = QProgressBar()
        progress_bar.setValue(0)

        # text edit
        text_edit = QPlainTextEdit()
        text_edit.setStyleSheet("font-size: 14pt; font-family: Times New Roman")
        self.entity_highlighter = EntityHighlighter(text_edit.document(), self.named_entity_definitions)
        text_edit.setPlainText("Lorem ipsum dolor sit amet, consectetur adipisici elit, sed eiusmod tempor incidunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquid ex ea commodi consequat. Quis aute iure reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint obcaecat cupiditat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.")
        self.text_edit = text_edit

        # shortcuts
        shortcut_legend_grid = QGridLayout()
        row = 0
        for named_entity_definition in self.named_entity_definitions:
            color_widget = QLabel(" " + named_entity_definition.code)
            color_widget.setStyleSheet("font-size: 10pt; color: white; background-color: %s" % named_entity_definition.backcolor)
            label_widget = QLabel(named_entity_definition.key_sequence)
            label_widget.setStyleSheet("font-size: 10pt;")
            shortcut_legend_grid.addWidget(color_widget, row, 0)
            shortcut_legend_grid.addWidget(label_widget, row, 1)
            row += 1
        entities_groupbox = QGroupBox("Entities")
        entities_groupbox.setLayout(shortcut_legend_grid)
        control_shortcuts_grid = QGridLayout()
        control_shortcuts_grid.addWidget(QLabel("Next"), 0, 0)
        control_shortcuts_grid.addWidget(QLabel("Ctrl+Enter"), 0, 1)
        control_shortcuts_grid.addWidget(QLabel("Undo"), 1, 0)
        control_shortcuts_grid.addWidget(QLabel("Ctrl+Z"), 1, 1)
        control_shortcuts_grid.addWidget(QLabel("Redo"), 2, 0)
        control_shortcuts_grid.addWidget(QLabel("Ctrl+Y"), 2, 1)
        controls_groupbox = QGroupBox("Controls")
        controls_groupbox.setLayout(control_shortcuts_grid)

        # done
        done_button = QPushButton("Done")
        done_button.clicked.connect(self.close)

        # grid
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        grid.addWidget(progress_bar, 0, 0, 1, 2)
        grid.addWidget(text_edit, 1, 0, 2, 1)
        right_column_layout = QVBoxLayout()
        right_column_layout.addWidget(entities_groupbox)
        right_column_layout.addWidget(controls_groupbox)
        right_column_layout.addStretch()
        grid.addLayout(right_column_layout, 1, 1)
        grid.addWidget(done_button, 3, 1)
        central_widget = QWidget()
        central_widget.setLayout(grid)
        self.setCentralWidget(central_widget)

    def wire_shortcuts(self):
        for named_entity_definition in self.named_entity_definitions:
            shortcut = QShortcut(QKeySequence(
                named_entity_definition.key_sequence), self)
            shortcut.activated.connect(self.on_annotate_entity)

    @pyqtSlot()
    def on_annotate_entity(self):
        text_cursor = self.text_edit.textCursor()
        if text_cursor.hasSelection():
            key_sequence = self.sender().key().toString()
            code = ""
            for named_entity_definition in self.named_entity_definitions:
                if named_entity_definition.key_sequence == key_sequence:
                    code = named_entity_definition.code
                    break
            text_cursor.insertText(
                "(" + text_cursor.selectedText() + "| " + code + ")")

class NamedEntityDefinition:
    def __init__(self, code, key_sequence, backcolor):
        self.code = code
        self.key_sequence = key_sequence
        self.backcolor = backcolor

class EntityHighlighter(QSyntaxHighlighter):
    highlighting_rules = []
    named_entity_code_format = QTextCharFormat()
    named_entity_code_format_no_text = QTextCharFormat()

    def __init__(self, parent, named_entity_definitions):
        super(EntityHighlighter, self).__init__(parent)
        named_entity_code_background_color = QColor("lightgrey")
        self.named_entity_code_format.setBackground(named_entity_code_background_color)
        self.named_entity_code_format.setFontWeight(QFont.Bold)
        self.named_entity_code_format.setFontPointSize(9)
        self.named_entity_code_format_no_text.setBackground(named_entity_code_background_color)
        self.named_entity_code_format_no_text.setForeground(named_entity_code_background_color)
        for named_entity_definition in named_entity_definitions:
            named_entity_text_format = QTextCharFormat()
            named_entity_text_format.setBackground(
                QColor(named_entity_definition.backcolor))
            named_entity_text_format.setForeground(Qt.white)
            named_entity_text_format_no_text = QTextCharFormat()
            named_entity_text_format_no_text.setBackground(
                QColor(named_entity_definition.backcolor))
            named_entity_text_format_no_text.setForeground(
                QColor(named_entity_definition.backcolor))
            self.highlighting_rules.append((QRegularExpression(
                r"(?<openParen>\()" +
                r"(?<text>[^|]+)" +
                r"(?<pipe>\|)" +
                r"(?<entityCode> " +
                named_entity_definition.code +
                r")(?<closingParen>\))"), named_entity_text_format, named_entity_text_format_no_text))

    def highlightBlock(self, text):
        for pattern, entity_text_format, entity_text_format_no_text in self.highlighting_rules:
            expression = QRegularExpression(pattern)
            offset = 0
            while offset >= 0:
                match = expression.match(text, offset)
                self.setFormat(match.capturedStart(
                    "openParen"), 1, entity_text_format_no_text)
                self.setFormat(match.capturedStart("text"),
                               match.capturedLength("text"), entity_text_format)
                self.setFormat(match.capturedStart("pipe"),
                               match.capturedLength("pipe"), entity_text_format_no_text)
                self.setFormat(match.capturedStart("entityCode"),
                               match.capturedLength("entityCode"), self.named_entity_code_format)
                self.setFormat(match.capturedStart(
                    "closingParen"), 1, self.named_entity_code_format_no_text)
                offset = match.capturedEnd("closingParen")


def main():
    app = QApplication(sys.argv) 
    named_entity_definitions = [
        NamedEntityDefinition("BLU", "Alt+B", "#153465"),
        NamedEntityDefinition("RED", "Alt+R", "#67160e"),
        NamedEntityDefinition("GRN", "Alt+G", "#135714"),
        NamedEntityDefinition("PRP", "Alt+P", "#341b4d"),
        NamedEntityDefinition("ORG", "Alt+O", "#b45c18"),
        NamedEntityDefinition("YLW", "Alt+Y", "#b0984f")
    ]
    annotation_dialog = AnnotationDialog(named_entity_definitions)
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
