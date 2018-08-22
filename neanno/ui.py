import sys

from PyQt5 import QtCore
from PyQt5.QtCore import QRegularExpression, Qt, pyqtSlot
from PyQt5.QtGui import QColor, QFont, QKeySequence, QSyntaxHighlighter, QTextCharFormat
from PyQt5.QtWidgets import (
    QApplication,
    QDataWidgetMapper,
    QDesktopWidget,
    QGridLayout,
    QGroupBox,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QShortcut,
    QVBoxLayout,
    QWidget,
)

if hasattr(QtCore.Qt, "AA_UseHighDpiPixmaps"):
    QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

SHORTCUT_NEXT_KEYSEQUENCE = "Ctrl+Return"
SHORTCUT_PREVIOUS_KEYSEQUENCE = "Ctrl+Backspace"
SHORTCUT_FIRST_KEYSEQUENCE = "Ctrl+F"
SHORTCUT_LAST_KEYSEQUENCE = "Ctrl+L"
SHORTCUT_UNDO_KEYSEQUENCE = "Ctrl+Z"
SHORTCUT_REDO_KEYSEQUENCE = "Ctrl+Y"
SHORTCUT_SAVE_KEYSEQUENCE = "Ctrl+S"

class _AnnotationDialog(QMainWindow):
    def __init__(self, text_model, named_entity_definitions):
        app = QApplication([])
        super().__init__()
        self.text_model = text_model
        self.named_entity_definitions = named_entity_definitions
        self.layout_controls()
        self.set_text_model(self.text_model)
        self.wire_shortcuts()
        self.show()
        app.exec_()

    def layout_controls(self):
        # window
        self.setWindowTitle("Annotate entities")
        screen = QDesktopWidget().screenGeometry()
        self.setGeometry(0, 0, screen.width() * .75, screen.height() * .75)
        mysize = self.geometry()
        horizontal_position = (screen.width() - mysize.width()) / 2
        vertical_position = (screen.height() - mysize.height()) / 2
        self.move(horizontal_position, vertical_position)

        ## progress bar
        # self.progress_bar = QProgressBar()
        # self.progress_bar.setValue(0)

        # text edit
        self.text_edit = QPlainTextEdit()
        self.text_edit.setStyleSheet("font-size: 14pt; font-family: Georgia")
        self.entity_highlighter = _EntityHighlighter(
            self.text_edit.document(), self.named_entity_definitions
        )

        # shortcuts
        shortcut_legend_grid = QGridLayout()
        row = 0
        for named_entity_definition in self.named_entity_definitions:
            color_widget = QLabel(" " + named_entity_definition.code)
            color_widget.setStyleSheet(
                "font-size: 10pt; color: white; background-color: %s"
                % named_entity_definition.backcolor
            )
            label_widget = QLabel(named_entity_definition.key_sequence)
            label_widget.setStyleSheet("font-size: 10pt;")
            shortcut_legend_grid.addWidget(color_widget, row, 0)
            shortcut_legend_grid.addWidget(label_widget, row, 1)
            row += 1
        entities_groupbox = QGroupBox("Entities")
        entities_groupbox.setLayout(shortcut_legend_grid)
        control_shortcuts_grid = QGridLayout()
        control_shortcuts_grid.addWidget(QLabel("Next"), 0, 0)
        control_shortcuts_grid.addWidget(QLabel(SHORTCUT_NEXT_KEYSEQUENCE), 0, 1)
        control_shortcuts_grid.addWidget(QLabel("Previous"), 1, 0)
        control_shortcuts_grid.addWidget(QLabel(SHORTCUT_PREVIOUS_KEYSEQUENCE), 1, 1)
        control_shortcuts_grid.addWidget(QLabel("First"), 2, 0)
        control_shortcuts_grid.addWidget(QLabel(SHORTCUT_FIRST_KEYSEQUENCE), 2, 1)
        control_shortcuts_grid.addWidget(QLabel("Last"), 3, 0)
        control_shortcuts_grid.addWidget(QLabel(SHORTCUT_LAST_KEYSEQUENCE), 3, 1)
        control_shortcuts_grid.addWidget(QLabel("Undo"), 4, 0)
        control_shortcuts_grid.addWidget(QLabel(SHORTCUT_UNDO_KEYSEQUENCE), 4, 1)
        control_shortcuts_grid.addWidget(QLabel("Redo"), 5, 0)
        control_shortcuts_grid.addWidget(QLabel(SHORTCUT_REDO_KEYSEQUENCE), 5, 1)
        control_shortcuts_grid.addWidget(QLabel("Save"), 6, 0)
        control_shortcuts_grid.addWidget(QLabel(SHORTCUT_SAVE_KEYSEQUENCE), 6, 1)
        controls_groupbox = QGroupBox("Controls")
        controls_groupbox.setLayout(control_shortcuts_grid)

        # close
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)

        # grid
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        # grid.addWidget(progress_bar, 0, 0, 1, 2)
        grid.addWidget(self.text_edit, 1, 0, 2, 1)
        right_column_layout = QVBoxLayout()
        right_column_layout.addWidget(entities_groupbox)
        right_column_layout.addWidget(controls_groupbox)
        right_column_layout.addStretch()
        grid.addLayout(right_column_layout, 1, 1)
        grid.addWidget(close_button, 3, 1)
        central_widget = QWidget()
        central_widget.setLayout(grid)
        self.setCentralWidget(central_widget)

    def wire_shortcuts(self):
        # named entities
        for named_entity_definition in self.named_entity_definitions:
            shortcut = QShortcut(
                QKeySequence(named_entity_definition.key_sequence), self
            )
            shortcut.activated.connect(self.on_annotate_entity)

        # next
        shortcut_next = QShortcut(
            QKeySequence(SHORTCUT_NEXT_KEYSEQUENCE),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_next.activated.connect(self.handle_shortcut_next)

        # previous
        shortcut_previous = QShortcut(
            QKeySequence(SHORTCUT_PREVIOUS_KEYSEQUENCE),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_previous.activated.connect(self.handle_shortcut_previous)

        # first
        shortcut_first = QShortcut(
            QKeySequence(SHORTCUT_FIRST_KEYSEQUENCE),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_first.activated.connect(self.handle_shortcut_first)

        # last
        shortcut_last = QShortcut(
            QKeySequence(SHORTCUT_LAST_KEYSEQUENCE),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_last.activated.connect(self.handle_shortcut_last)

        # save
        shortcut_last = QShortcut(
            QKeySequence(SHORTCUT_SAVE_KEYSEQUENCE),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_last.activated.connect(self.handle_shortcut_save)

    def set_text_model(self, text_model):
        self.text_mapper = QDataWidgetMapper(self)
        self.text_mapper.setModel(text_model)
        self.text_mapper.addMapping(self.text_edit, 0)
        self.text_mapper.toFirst()

    def handle_shortcut_next(self):
        self.text_edit.clearFocus()
        self.text_mapper.toNext()

    def handle_shortcut_previous(self):
        self.text_edit.clearFocus()
        self.text_mapper.toPrevious()

    def handle_shortcut_first(self):
        self.text_edit.clearFocus()
        self.text_mapper.toFirst()

    def handle_shortcut_last(self):
        self.text_edit.clearFocus()
        self.text_mapper.toLast()

    def handle_shortcut_save(self):
        self.text_edit.clearFocus()
        self.text_model.save()

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
            text_cursor.insertText("(" + text_cursor.selectedText() + "| " + code + ")")


class _EntityHighlighter(QSyntaxHighlighter):
    highlighting_rules = []
    named_entity_code_format = QTextCharFormat()
    named_entity_code_format_no_text = QTextCharFormat()

    def __init__(self, parent, named_entity_definitions):
        super(_EntityHighlighter, self).__init__(parent)
        named_entity_code_background_color = QColor("lightgrey")
        self.named_entity_code_format.setBackground(named_entity_code_background_color)
        self.named_entity_code_format.setFontFamily("Segoe UI")
        self.named_entity_code_format.setFontWeight(QFont.Bold)
        self.named_entity_code_format.setFontPointSize(9)
        self.named_entity_code_format_no_text.setBackground(
            named_entity_code_background_color
        )
        self.named_entity_code_format_no_text.setForeground(
            named_entity_code_background_color
        )
        for named_entity_definition in named_entity_definitions:
            named_entity_text_format = QTextCharFormat()
            named_entity_text_format.setBackground(
                QColor(named_entity_definition.backcolor)
            )
            named_entity_text_format.setForeground(Qt.white)
            named_entity_text_format_no_text = QTextCharFormat()
            named_entity_text_format_no_text.setBackground(
                QColor(named_entity_definition.backcolor)
            )
            named_entity_text_format_no_text.setForeground(
                QColor(named_entity_definition.backcolor)
            )
            self.highlighting_rules.append(
                (
                    QRegularExpression(
                        r"(?<openParen>\()"
                        + r"(?<text>[^|]+)"
                        + r"(?<pipe>\|)"
                        + r"(?<entityCode> "
                        + named_entity_definition.code
                        + r")(?<closingParen>\))"
                    ),
                    named_entity_text_format,
                    named_entity_text_format_no_text,
                )
            )

    def highlightBlock(self, text):
        for (
            pattern,
            entity_text_format,
            entity_text_format_no_text,
        ) in self.highlighting_rules:
            expression = QRegularExpression(pattern)
            offset = 0
            while offset >= 0:
                match = expression.match(text, offset)
                self.setFormat(
                    match.capturedStart("openParen"), 1, entity_text_format_no_text
                )
                self.setFormat(
                    match.capturedStart("text"),
                    match.capturedLength("text"),
                    entity_text_format,
                )
                self.setFormat(
                    match.capturedStart("pipe"),
                    match.capturedLength("pipe"),
                    entity_text_format_no_text,
                )
                self.setFormat(
                    match.capturedStart("entityCode"),
                    match.capturedLength("entityCode"),
                    self.named_entity_code_format,
                )
                self.setFormat(
                    match.capturedStart("closingParen"),
                    1,
                    self.named_entity_code_format_no_text,
                )
                offset = match.capturedEnd("closingParen")
