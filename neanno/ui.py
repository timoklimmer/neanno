import os
import re
import sys

from PyQt5 import QtCore
from PyQt5.QtCore import QByteArray, QRegularExpression, Qt, pyqtSlot
from PyQt5.QtGui import (
    QColor,
    QFont,
    QIcon,
    QKeySequence,
    QSyntaxHighlighter,
    QTextCharFormat,
)
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDataWidgetMapper,
    QDesktopWidget,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QShortcut,
    QVBoxLayout,
    QWidget,
)

if hasattr(QtCore.Qt, "AA_UseHighDpiPixmaps"):
    QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

SHORTCUT_SUBMIT_NEXT_BEST_KEYSEQUENCE = "Ctrl+Return"
SHORTCUT_BACKWARD_KEYSEQUENCE = "Ctrl+Left"
SHORTCUT_FORWARD_KEYSEQUENCE = "Ctrl+Right"
SHORTCUT_FIRST_KEYSEQUENCE = "Ctrl+F"
SHORTCUT_PREVIOUS_KEYSEQUENCE = "Ctrl+P"
SHORTCUT_NEXT_KEYSEQUENCE = "Ctrl+N"
SHORTCUT_LAST_KEYSEQUENCE = "Ctrl+L"
SHORTCUT_GOTO_KEYSEQUENCE = "Ctrl+G"
SHORTCUT_UNDO_KEYSEQUENCE = "Ctrl+Z"
SHORTCUT_REDO_KEYSEQUENCE = "Ctrl+Y"
SHORTCUT_REMOVE_KEYSEQUENCE = "Ctrl+R"
SHORTCUT_REMOVE_ALL_KEYSEQUENCE = "Ctrl+T"

ABOUT_TEXT = """
neanno is yet another text annotation tool.

There are already several other annotation tools out there but none
of them really matched my requirements. Hence, I created my own.

This is NOT an official Microsoft product, hence does not come with
any support or obligations for Microsoft.

Feel free to use but don't blame me if things go wrong.

Get the most updated version from GitHub.

Written in 2018 by Timo Klimmer, timo.klimmer@microsoft.com.
"""


class AnnotationDialog(QMainWindow):
    def __init__(self, textmodel):
        app = QApplication([])
        super().__init__()
        self.setWindowIcon(
            QIcon(
                os.path.join(
                    os.path.abspath(os.path.dirname(__file__)), "resources/icon.ico"
                )
            )
        )
        self.textmodel = textmodel
        self.layout_controls()
        self.wire_textmodel()
        self.wire_shortcuts()
        self.show()
        app.exec_()

    def layout_controls(self):
        # window
        self.setWindowTitle("neanno")
        screen = QDesktopWidget().screenGeometry()
        self.setGeometry(0, 0, screen.width() * 0.75, screen.height() * 0.75)
        mysize = self.geometry()
        horizontal_position = (screen.width() - mysize.width()) / 2
        vertical_position = (screen.height() - mysize.height()) / 2
        self.move(horizontal_position, vertical_position)

        # text edit
        self.text_edit = QPlainTextEdit()
        self.text_edit.setStyleSheet(
            "font-size: 14pt; font-family: Consolas; color: lightgrey; background-color: black"
        )
        self.entity_highlighter = _EntityHighlighter(
            self.text_edit.document(), self.textmodel.named_entity_definitions
        )

        # text categories
        text_categories_grid = QGridLayout()
        text_categories_list = QListWidget()
        text_categories_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        text_categories_list.addItem("Option 1")
        text_categories_list.addItem("Option 2")
        text_categories_list.addItem("Option 3")
        text_categories_list.addItem("Option 4")
        text_categories_list.addItem("Option 5")
        text_categories_grid.addWidget(text_categories_list)
        text_categories_groupbox = QGroupBox("Text Categories")
        text_categories_groupbox.setLayout(text_categories_grid)

        # shortcuts
        shortcut_legend_grid = QGridLayout()
        row = 0
        for named_entity_definition in self.textmodel.named_entity_definitions:
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

        # statistics
        statistics_grid = QGridLayout()
        statistics_grid.addWidget(QLabel("Current Index"), 0, 0)
        self.current_text_index_label = QLabel()
        statistics_grid.addWidget(self.current_text_index_label, 0, 1)
        statistics_grid.addWidget(QLabel("Is Annotated"), 1, 0)
        self.is_annotated_label = QLabel()
        statistics_grid.addWidget(self.is_annotated_label, 1, 1)
        statistics_grid.addWidget(QLabel("Annotated Texts"), 2, 0)
        self.annotated_texts_label = QLabel()
        statistics_grid.addWidget(self.annotated_texts_label, 2, 1)
        statistics_grid.addWidget(QLabel("Total Texts"), 3, 0)
        self.total_texts_label = QLabel()
        statistics_grid.addWidget(self.total_texts_label, 3, 1)
        statistics_grid.addWidget(QLabel("Annotated"), 4, 0)
        self.annotated_percent_label = QLabel()
        statistics_grid.addWidget(self.annotated_percent_label, 4, 1)
        statistics_groupbox = QGroupBox("Statistics")
        statistics_groupbox.setLayout(statistics_grid)

        # Dataset
        if self.textmodel.hasDatasetMetadata():
            dataset_grid = QGridLayout()
            if self.textmodel.dataset_source_friendly is not None:
                dataset_grid.addWidget(QLabel("Source"), 0, 0)
                self.dataset_source_friendly_label = QLabel(
                    self.textmodel.dataset_source_friendly
                )
                dataset_grid.addWidget(self.dataset_source_friendly_label, 0, 1)
            if self.textmodel.dataset_target_friendly is not None:
                dataset_grid.addWidget(QLabel("Target"), 1, 0)
                self.dataset_target_friendly_label = QLabel(
                    self.textmodel.dataset_target_friendly
                )
                dataset_grid.addWidget(self.dataset_target_friendly_label, 1, 1)
            dataset_groupbox = QGroupBox("Dataset")
            dataset_groupbox.setLayout(dataset_grid)

        # spacy model
        if self.textmodel.hasSpacyModel():
            model_grid = QGridLayout()
            model_grid.addWidget(QLabel("Source"), 0, 0)
            self.spacy_model_source_label = QLabel(self.textmodel.spacy_model_source)
            model_grid.addWidget(self.spacy_model_source_label, 0, 1)
            retrain_model_button = QPushButton("Retrain")
            retrain_model_button.clicked.connect(self.handle_retrain_button_clicked)
            model_grid.addWidget(retrain_model_button, 2, 0)

            if self.textmodel.spacy_model_target is not None:
                model_grid.addWidget(QLabel("Target"), 1, 0)
                self.spacy_model_target_label = QLabel(self.textmodel.spacy_model_target)
                model_grid.addWidget(self.spacy_model_target_label, 1, 1)
            model_groupbox = QGroupBox("Spacy Model")
            model_groupbox.setLayout(model_grid)

        # progress bar
        self.progressbar = QProgressBar()
        self.progressbar.setValue(0)

        # about
        about_button = QPushButton("About")
        about_button.clicked.connect(self.handle_about_button_clicked)

        # shortcuts button
        shortcuts_button = QPushButton("Shortcuts")
        shortcuts_button.clicked.connect(self.handle_shortcuts_button_clicked)

        # close
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)

        # grid and box layouts
        grid = QGridLayout()
        grid.setSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        grid.addWidget(self.text_edit, 1, 0, 2, 1)
        right_column_layout = QVBoxLayout()
        right_column_layout.addWidget(text_categories_groupbox)
        right_column_layout.addWidget(entities_groupbox)
        right_column_layout.addWidget(statistics_groupbox)
        if self.textmodel.hasDatasetMetadata():
            right_column_layout.addWidget(dataset_groupbox)
        if self.textmodel.hasSpacyModel():
            right_column_layout.addWidget(model_groupbox)
        right_column_layout.addStretch()
        grid.addLayout(right_column_layout, 1, 1)
        vbox = QVBoxLayout()
        vbox.addLayout(grid)
        hbox = QHBoxLayout()
        hbox.addWidget(self.progressbar)
        hbox.addWidget(about_button)
        hbox.addWidget(shortcuts_button)
        hbox.addWidget(close_button)
        vbox.addLayout(hbox)
        central_widget = QWidget()
        central_widget.setLayout(vbox)
        self.setCentralWidget(central_widget)

    def wire_shortcuts(self):
        # named entities
        for named_entity_definition in self.textmodel.named_entity_definitions:
            shortcut = QShortcut(
                QKeySequence(named_entity_definition.key_sequence), self
            )
            shortcut.activated.connect(self.annotate_entity)

        # submit / next best
        shortcut_submit_next_best = QShortcut(
            QKeySequence(SHORTCUT_SUBMIT_NEXT_BEST_KEYSEQUENCE),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_submit_next_best.activated.connect(
            self.handle_shortcut_submit_next_best
        )

        # backward
        shortcut_backward = QShortcut(
            QKeySequence(SHORTCUT_BACKWARD_KEYSEQUENCE),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_backward.activated.connect(self.text_navigator.backward)

        # forward
        shortcut_forward = QShortcut(
            QKeySequence(SHORTCUT_FORWARD_KEYSEQUENCE),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_forward.activated.connect(self.text_navigator.forward)

        # first
        shortcut_first = QShortcut(
            QKeySequence(SHORTCUT_FIRST_KEYSEQUENCE),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_first.activated.connect(self.text_navigator.toFirst)

        # previous
        shortcut_previous = QShortcut(
            QKeySequence(SHORTCUT_PREVIOUS_KEYSEQUENCE),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_previous.activated.connect(self.text_navigator.toPrevious)

        # next
        shortcut_next = QShortcut(
            QKeySequence(SHORTCUT_NEXT_KEYSEQUENCE),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_next.activated.connect(self.text_navigator.toNext)

        # last
        shortcut_last = QShortcut(
            QKeySequence(SHORTCUT_LAST_KEYSEQUENCE),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_last.activated.connect(self.text_navigator.toLast)

        # goto
        shortcut_goto = QShortcut(
            QKeySequence(SHORTCUT_GOTO_KEYSEQUENCE),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_goto.activated.connect(self.handle_shortcut_goto)

        # remove
        shortcut_last = QShortcut(
            QKeySequence(SHORTCUT_REMOVE_KEYSEQUENCE),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_last.activated.connect(self.remove_entity)

        # remove all
        shortcut_last = QShortcut(
            QKeySequence(SHORTCUT_REMOVE_ALL_KEYSEQUENCE),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_last.activated.connect(self.remove_all_entities)

    def wire_textmodel(self):
        self.text_navigator = _QDataWidgetMapperWithHistory(self)
        self.text_navigator.setSubmitPolicy(QDataWidgetMapper.ManualSubmit)
        self.text_navigator.setModel(self.textmodel)
        self.text_navigator.addMapping(self.text_edit, 0)
        self.text_navigator.addMapping(
            self.is_annotated_label, 1, QByteArray().insert(0, "text")
        )
        self.text_navigator.currentIndexChanged.connect(
            self.update_statistics_and_progress
        )
        self.text_navigator.setCurrentIndex(self.textmodel.nextBestRowIndex(-1))

    def handle_shortcut_submit_next_best(self):
        # submit changes of old text
        self.text_navigator.submit()
        # update statistics and progress bar
        self.update_statistics_and_progress()
        # show "all messages annotated" if all texts are annotated
        if not self.textmodel.isTextToAnnotateLeft():
            QMessageBox.information(
                self,
                "Congratulations",
                "You have annotated all {} texts. There are no more texts to annotate.".format(
                    self.textmodel.rowCount()
                ),
                QMessageBox.Ok,
            )
        # identify and go to next best text
        self.text_navigator.setCurrentIndex(
            self.textmodel.nextBestRowIndex(self.text_navigator.currentIndex())
        )

    def handle_shortcut_goto(self):
        new_index, is_not_canceled = QInputDialog.getInt(
            self, "Goto Index", "Enter an index:"
        )
        if is_not_canceled:
            self.text_navigator.setCurrentIndex(new_index)

    def handle_about_button_clicked(self):
        QMessageBox.information(
            self,
            "About neanno",
            ABOUT_TEXT,
            QMessageBox.Ok,
        )

    def handle_shortcuts_button_clicked(self):
        def shortcut_fragment(label, shortcut):
            return "<tr><td style=""padding-right:20"">{}</td><td>{}</td></tr>".format(label, shortcut)
        message = "<table>"
        message += shortcut_fragment("Submit/Next Best", SHORTCUT_SUBMIT_NEXT_BEST_KEYSEQUENCE)
        message += shortcut_fragment("Backward", SHORTCUT_BACKWARD_KEYSEQUENCE)
        message += shortcut_fragment("Forward", SHORTCUT_FORWARD_KEYSEQUENCE)
        message += shortcut_fragment("First", SHORTCUT_FIRST_KEYSEQUENCE)
        message += shortcut_fragment("Previous", SHORTCUT_PREVIOUS_KEYSEQUENCE)
        message += shortcut_fragment("Next", SHORTCUT_NEXT_KEYSEQUENCE)
        message += shortcut_fragment("Last", SHORTCUT_LAST_KEYSEQUENCE)
        message += shortcut_fragment("Goto", SHORTCUT_GOTO_KEYSEQUENCE)
        message += shortcut_fragment("Undo", SHORTCUT_UNDO_KEYSEQUENCE)
        message += shortcut_fragment("Redo", SHORTCUT_REDO_KEYSEQUENCE)
        message += shortcut_fragment("Remove label", SHORTCUT_REMOVE_KEYSEQUENCE)
        message += shortcut_fragment("Remove all labels", SHORTCUT_REMOVE_ALL_KEYSEQUENCE)
        message += "</table>"


        msg = QMessageBox()
        msg.setTextFormat(Qt.RichText)
        msg.setIcon(QMessageBox.Information)
        msg.setText(message)
        msg.setWindowTitle("Shortcuts")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

        #QMessageBox.information(
        #    self,
        #    "Shortcuts",
        #    message,
        #    QMessageBox.Ok,
        #)

    def handle_retrain_button_clicked(self):
        self.textmodel.retrain_spacy_model()

    def update_statistics_and_progress(self):
        # progress
        new_progress_value = (
            self.textmodel.annotatedTextsCount() * 100 / self.textmodel.rowCount()
        )
        self.progressbar.setValue(new_progress_value)
        # current index
        self.current_text_index_label.setText(str(self.text_navigator.currentIndex()))
        # annotated texts count
        annotated_texts_count = self.textmodel.annotatedTextsCount()
        self.annotated_texts_label.setText(str(annotated_texts_count))
        # total texts count
        total_texts_count = self.textmodel.rowCount()
        self.total_texts_label.setText(str(total_texts_count))
        # annotated percent
        self.annotated_percent_label.setText(
            "{0:.0%}".format(annotated_texts_count / total_texts_count)
        )
        # remove focus from text control
        self.text_edit.clearFocus()

    def annotate_entity(self):
        text_cursor = self.text_edit.textCursor()
        if text_cursor.hasSelection():
            key_sequence = self.sender().key().toString()
            code = ""
            for named_entity_definition in self.textmodel.named_entity_definitions:
                if named_entity_definition.key_sequence == key_sequence:
                    code = named_entity_definition.code
                    break
            text_cursor.insertText("(" + text_cursor.selectedText() + "| " + code + ")")

    def remove_entity(self):
        current_cursor_pos = self.text_edit.textCursor().position()
        new_text = re.sub(
            "\((.*?)\| .+?\)",
            lambda match: match.group(1)
            if current_cursor_pos > match.start() and current_cursor_pos < match.end()
            else match.group(0),
            self.text_edit.toPlainText(),
            flags=re.DOTALL,
        )
        self.text_edit.setPlainText(new_text)

    def remove_all_entities(self):
        new_text = re.sub(
            "\((.*?)\| .+?\)",
            lambda match: match.group(1),
            self.text_edit.toPlainText(),
            flags=re.DOTALL,
        )
        self.text_edit.setPlainText(new_text)


class _EntityHighlighter(QSyntaxHighlighter):
    highlighting_rules = []
    named_entity_code_format = QTextCharFormat()
    named_entity_code_format_no_text = QTextCharFormat()

    def __init__(self, parent, named_entity_definitions):
        super(_EntityHighlighter, self).__init__(parent)
        named_entity_code_background_color = QColor("lightgrey")
        self.named_entity_code_format.setForeground(Qt.black)
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
                        + r"(?<text>[^|(]+?)"
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


class _QDataWidgetMapperWithHistory(QDataWidgetMapper):
    backward_stack = []
    forward_stack = []
    is_forward_or_backward = False

    def __init__(self, parent=None):
        super().__init__(parent)

    def setCurrentIndex(self, index):
        if self.currentIndex() != index:
            if not self.is_forward_or_backward:
                self.forward_stack = []
                self.backward_stack.append(self.currentIndex())
            super().setCurrentIndex(index)

    def backward(self):
        if len(self.backward_stack) > 0:
            self.forward_stack.append(self.currentIndex())
            self.is_forward_or_backward = True
            self.setCurrentIndex(self.backward_stack.pop())
            self.is_forward_or_backward = False

    def forward(self):
        if len(self.forward_stack) > 0:
            self.backward_stack.append(self.currentIndex())
            self.is_forward_or_backward = True
            self.setCurrentIndex(self.forward_stack.pop())
            self.is_forward_or_backward = False
