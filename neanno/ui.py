import os
import re

import config
from neanno.custom_ui_controls import (
    CategoriesSelectorWidget,
    QDataWidgetMapperWithHistory,
)
from PyQt5 import QtCore
from PyQt5.QtCore import QByteArray, QRegularExpression, Qt
from PyQt5.QtGui import (
    QColor,
    QFont,
    QIcon,
    QKeySequence,
    QSyntaxHighlighter,
    QTextCharFormat,
    QPalette,
)
from PyQt5.QtWidgets import (
    QApplication,
    QDataWidgetMapper,
    QDesktopWidget,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLayout,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QShortcut,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

SHORTCUT_SUBMIT_NEXT_BEST = "Ctrl+Return"
SHORTCUT_BACKWARD = "Ctrl+Left"
SHORTCUT_FORWARD = "Ctrl+Right"
SHORTCUT_FIRST = "Ctrl+F"
SHORTCUT_PREVIOUS = "Ctrl+P"
SHORTCUT_NEXT = "Ctrl+N"
SHORTCUT_LAST = "Ctrl+L"
SHORTCUT_GOTO = "Ctrl+G"
SHORTCUT_UNDO = "Ctrl+Z"
SHORTCUT_REDO = "Ctrl+Y"
SHORTCUT_REMOVE = "Ctrl+R"
SHORTCUT_REMOVE_ALL = "Ctrl+D"

ABOUT_TEXT = """neanno is yet another text annotation tool.

There are already several other annotation tools out there but none
of them really matched my requirements. Hence, I created my own.

This is NOT an official Microsoft product, hence does not come with
any support or obligations for Microsoft.

Feel free to use but don't blame me if things go wrong.

Get the most updated version from GitHub.

Written in 2018 by Timo Klimmer, timo.klimmer@microsoft.com.
"""


class AnnotationDialog(QMainWindow):
    """ The dialog shown to the user to do the annotation/labeling."""

    def __init__(self, textmodel):
        print("Showing annotation dialog...")
        app = QApplication([])
        super().__init__()
        self.setWindowIcon(self.get_icon("icon.ico"))
        self.textmodel = textmodel
        self.layout_controls()
        self.wire_textmodel()
        self.wire_shortcuts()
        self.show()
        app.exec_()

    @staticmethod
    def get_icon(file):
        return QIcon(
            os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "resources/{}".format(file)
            )
        )

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
        self.text_edit_entity_highlighter = EntityHighlighter(
            self.text_edit.document(), config.named_entity_definitions
        )
        self.text_edit.textChanged.connect(self.update_tag_monitor)

        # tag monitor
        self.tag_monitor = QPlainTextEdit()
        self.tag_monitor.setStyleSheet(
            "font-size: 14pt; font-family: Consolas; color: lightgrey; background-color: black"
        )
        self.tag_monitor_entity_highlighter = EntityHighlighter(
            self.tag_monitor.document(), config.named_entity_definitions
        )

        # navigation / about / shortcuts buttons
        self.backward_button = QPushButton(self.get_icon("backward.png"), None)
        self.forward_button = QPushButton(self.get_icon("forward.png"), None)
        self.first_button = QPushButton(self.get_icon("first.png"), None)
        self.previous_button = QPushButton(self.get_icon("previous.png"), None)
        self.next_button = QPushButton(self.get_icon("next.png"), None)
        self.last_button = QPushButton(self.get_icon("last.png"), None)
        self.goto_button = QPushButton(self.get_icon("goto.png"), None)
        self.submit_next_best_button = QPushButton(
            self.get_icon("submit_next_best.png"), None
        )
        about_button = QPushButton("About")
        about_button.clicked.connect(self.handle_about_button_clicked)
        shortcuts_button = QPushButton("Shortcuts")
        shortcuts_button.clicked.connect(self.handle_shortcuts_button_clicked)
        navigation_buttons_layout = QHBoxLayout()
        navigation_buttons_layout.addWidget(self.backward_button)
        navigation_buttons_layout.addWidget(self.forward_button)
        navigation_buttons_layout.addStretch()
        navigation_buttons_layout.addWidget(self.first_button)
        navigation_buttons_layout.addWidget(self.previous_button)
        navigation_buttons_layout.addWidget(self.next_button)
        navigation_buttons_layout.addWidget(self.last_button)
        navigation_buttons_layout.addWidget(self.goto_button)
        navigation_buttons_layout.addWidget(self.submit_next_best_button)
        navigation_buttons_layout.addStretch()
        navigation_buttons_layout.addWidget(about_button)
        navigation_buttons_layout.addWidget(shortcuts_button)

        # progress bar
        self.progressbar = QProgressBar()
        self.progressbar.setValue(0)

        # categories
        # note: CategoriesSelectorWidget populates itself (mostly due to the QTableWidget control, might be improved in future)
        if config.is_categories_enabled:
            self.text_categories_selector = CategoriesSelectorWidget(
                config, self.textmodel
            )
            self.text_categories_selector.selectionModel().selectionChanged.connect(
                self.update_tag_monitor
            )
            text_categories_groupbox_layout = QHBoxLayout()
            text_categories_groupbox_layout.addWidget(self.text_categories_selector)
            text_categories_groupbox_layout.setSizeConstraint(QLayout.SetFixedSize)
            text_categories_groupbox = QGroupBox("Categories")
            text_categories_groupbox.setLayout(text_categories_groupbox_layout)

        # tagging
        if config.is_tagging_enabled:
            tags_layout = QHBoxLayout()
            tags_layout.addWidget(
                QLabel(
                    "{} to highlight the selected term.\n{} to tag the selected term with something.".format(
                        config.tagging_shortcut_anonymous, config.tagging_shortcut_named
                    )
                )
            )
            tags_groupbox = QGroupBox("Tags")
            tags_groupbox.setLayout(tags_layout)

        # entity shortcuts / counts
        if config.is_named_entities_enabled:
            entity_infos_layout = QHBoxLayout()
            self.entity_infos_markup_control = QLabel()
            self.entity_infos_markup_control.setTextFormat(Qt.RichText)
            entity_infos_layout.addWidget(self.entity_infos_markup_control)
            entities_groupbox = QGroupBox("Entities")
            entities_groupbox.setLayout(entity_infos_layout)

        # spacy model
        if config.is_spacy_enabled:
            spacy_grid = QGridLayout()
            spacy_grid.addWidget(QLabel("Source"), 0, 0)
            self.spacy_model_source_label = QLabel(config.spacy_model_source)
            spacy_grid.addWidget(self.spacy_model_source_label, 0, 1)
            retrain_model_button = QPushButton("Retrain")
            retrain_model_button.clicked.connect(self.handle_retrain_button_clicked)
            spacy_grid.addWidget(retrain_model_button, 2, 0)

            if config.spacy_model_target is not None:
                spacy_grid.addWidget(QLabel("Target"), 1, 0)
                self.spacy_model_target_label = QLabel(config.spacy_model_target)
                spacy_grid.addWidget(self.spacy_model_target_label, 1, 1)
            spacy_groupbox = QGroupBox("Spacy")
            spacy_groupbox.setLayout(spacy_grid)

        # dataset
        dataset_grid = QGridLayout()
        dataset_grid.addWidget(QLabel("Annotated"), 0, 0)
        dataset_grid.addWidget(self.progressbar, 0, 1)
        dataset_grid.addWidget(QLabel("Annotated Texts"), 1, 0)
        self.annotated_texts_label = QLabel()
        dataset_grid.addWidget(self.annotated_texts_label, 1, 1)
        dataset_grid.addWidget(QLabel("Total Texts"), 2, 0)
        self.total_texts_label = QLabel()
        dataset_grid.addWidget(self.total_texts_label, 2, 1)
        dataset_grid.addWidget(QLabel("Current Index"), 3, 0)
        self.current_text_index_label = QLabel()
        dataset_grid.addWidget(self.current_text_index_label, 3, 1)
        dataset_grid.addWidget(QLabel("Is Annotated"), 4, 0)
        self.is_annotated_label = QLabel()
        dataset_grid.addWidget(self.is_annotated_label, 4, 1)
        if config.dataset_source_friendly:
            dataset_grid.addWidget(QLabel("Source"), 5, 0)
            self.dataset_source_friendly_label = QLabel(config.dataset_source_friendly)
            dataset_grid.addWidget(self.dataset_source_friendly_label, 5, 1)
        if config.dataset_target_friendly:
            dataset_grid.addWidget(QLabel("Target"), 6, 0)
            self.dataset_target_friendly_label = QLabel(config.dataset_target_friendly)
            dataset_grid.addWidget(self.dataset_target_friendly_label, 6, 1)
        dataset_groupbox = QGroupBox("Dataset")
        dataset_groupbox.setLayout(dataset_grid)

        # close
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)

        # remaining layouts
        # left panel
        left_panel_layout = QVBoxLayout()
        left_panel_layout_splitter = QSplitter(Qt.Vertical)
        left_panel_layout_splitter.addWidget(self.text_edit)
        left_panel_layout_splitter.addWidget(self.tag_monitor)
        left_panel_layout_splitter.setSizes([400, 100])
        left_panel_layout.addWidget(left_panel_layout_splitter)
        # right panel
        right_panel_layout = QVBoxLayout()
        if config.is_categories_enabled:
            right_panel_layout.addWidget(text_categories_groupbox)
        if config.is_tagging_enabled:
            right_panel_layout.addWidget(tags_groupbox)
        if config.is_named_entities_enabled:
            right_panel_layout.addWidget(entities_groupbox)
        right_panel_layout.addWidget(dataset_groupbox)
        if config.is_spacy_enabled:
            right_panel_layout.addWidget(spacy_groupbox)
        right_panel_layout.addStretch()
        right_buttons_layout = QHBoxLayout()
        right_buttons_layout.addStretch()
        right_buttons_layout.addWidget(close_button)
        # main
        main_grid = QGridLayout()
        main_grid.setSpacing(10)
        main_grid.setColumnStretch(0, 1)
        main_grid.setColumnStretch(1, 0)
        main_grid.addLayout(left_panel_layout, 0, 0)
        main_grid.addLayout(right_panel_layout, 0, 1)
        main_grid.addLayout(navigation_buttons_layout, 1, 0)
        main_grid.addLayout(right_buttons_layout, 1, 1)
        central_widget = QWidget()
        central_widget.setLayout(main_grid)
        self.setCentralWidget(central_widget)

        # update the dataset-related controls so they show up
        self.update_dataset_related_controls()

    def wire_shortcuts(self):
        # tagging
        shortcut_tag_named = QShortcut(
            QKeySequence(config.tagging_shortcut_named), self
        )
        shortcut_tag_named.activated.connect(self.place_named_tag)
        shortcut_tag_anonymous = QShortcut(
            QKeySequence(config.tagging_shortcut_anonymous), self
        )
        shortcut_tag_anonymous.activated.connect(self.place_anonymous_tag)
        # named entities
        for named_entity_definition in config.named_entity_definitions:
            shortcut = QShortcut(
                QKeySequence(named_entity_definition.key_sequence), self
            )
            shortcut.activated.connect(self.annotate_entity)

        # submit / next best
        shortcut_submit_next_best = QShortcut(
            QKeySequence(SHORTCUT_SUBMIT_NEXT_BEST),
            self,
            context=Qt.ApplicationShortcut,
        )
        shortcut_submit_next_best.activated.connect(self.submit_and_go_to_next_best)

        # backward
        shortcut_backward = QShortcut(
            QKeySequence(SHORTCUT_BACKWARD), self, context=Qt.ApplicationShortcut
        )
        shortcut_backward.activated.connect(self.text_navigator.backward)

        # forward
        shortcut_forward = QShortcut(
            QKeySequence(SHORTCUT_FORWARD), self, context=Qt.ApplicationShortcut
        )
        shortcut_forward.activated.connect(self.text_navigator.forward)

        # first
        shortcut_first = QShortcut(
            QKeySequence(SHORTCUT_FIRST), self, context=Qt.ApplicationShortcut
        )
        shortcut_first.activated.connect(self.text_navigator.toFirst)

        # previous
        shortcut_previous = QShortcut(
            QKeySequence(SHORTCUT_PREVIOUS), self, context=Qt.ApplicationShortcut
        )
        shortcut_previous.activated.connect(self.text_navigator.toPrevious)

        # next
        shortcut_next = QShortcut(
            QKeySequence(SHORTCUT_NEXT), self, context=Qt.ApplicationShortcut
        )
        shortcut_next.activated.connect(self.text_navigator.toNext)

        # last
        shortcut_last = QShortcut(
            QKeySequence(SHORTCUT_LAST), self, context=Qt.ApplicationShortcut
        )
        shortcut_last.activated.connect(self.text_navigator.toLast)

        # goto
        shortcut_goto = QShortcut(
            QKeySequence(SHORTCUT_GOTO), self, context=Qt.ApplicationShortcut
        )
        shortcut_goto.activated.connect(self.handle_shortcut_goto)

        # remove
        shortcut_last = QShortcut(
            QKeySequence(SHORTCUT_REMOVE), self, context=Qt.ApplicationShortcut
        )
        shortcut_last.activated.connect(self.remove_annotation)

        # remove all
        shortcut_last = QShortcut(
            QKeySequence(SHORTCUT_REMOVE_ALL), self, context=Qt.ApplicationShortcut
        )
        shortcut_last.activated.connect(self.remove_all_annotations)

    def wire_textmodel(self):
        self.text_navigator = QDataWidgetMapperWithHistory(self)
        self.text_navigator.setSubmitPolicy(QDataWidgetMapper.ManualSubmit)
        self.text_navigator.setModel(self.textmodel)
        self.text_navigator.addMapping(self.text_edit, 0)
        self.text_navigator.addMapping(
            self.is_annotated_label, 1, QByteArray().insert(0, "text")
        )
        if config.is_categories_enabled:
            self.text_navigator.addMapping(
                self.text_categories_selector,
                2,
                QByteArray().insert(0, "selected_categories_text"),
            )
        self.text_navigator.currentIndexChanged.connect(
            self.update_navigation_related_controls
        )
        self.text_navigator.setCurrentIndex(self.textmodel.get_next_best_row_index(-1))
        self.backward_button.clicked.connect(self.text_navigator.backward)
        self.forward_button.clicked.connect(self.text_navigator.forward)
        self.first_button.clicked.connect(self.text_navigator.toFirst)
        self.previous_button.clicked.connect(self.text_navigator.toPrevious)
        self.next_button.clicked.connect(self.text_navigator.toNext)
        self.last_button.clicked.connect(self.text_navigator.toLast)
        self.goto_button.clicked.connect(self.handle_shortcut_goto)
        self.submit_next_best_button.clicked.connect(self.submit_and_go_to_next_best)

    def update_tag_monitor(self):
        new_tags = []
        # categories
        if config.is_categories_enabled:
            new_tags.extend(self.text_categories_selector.get_selected_categories())

        # entities
        # TODO: sort by configuration sequence
        if config.is_named_entities_enabled:
            entities = []
            for match in re.findall(
                r"\([^()]+?\|E [^()]*?\)", self.text_edit.toPlainText(), flags=re.DOTALL
            ):
                entities.append(match)
            if len(entities) > 0:
                entities = sorted(set(entities))
                new_tags.extend(entities)
        # named tags (highlighted term)
        if config.is_tagging_enabled:
            named_tags = []
            for match in re.finditer(
                r"\([^()]+?\|T (?P<tagName>[^()]*?)\)",
                self.text_edit.toPlainText(),
                flags=re.DOTALL,
            ):
                named_tags.append("({}|A)".format(match.group("tagName")))
            if len(named_tags) > 0:
                named_tags = sorted(set(named_tags))
                new_tags.extend(named_tags)
            # anonymous tags (tagged term)
            anonymous_tags = []
            for match in re.findall(
                r"\([^()]+?\|A\)", self.text_edit.toPlainText(), flags=re.DOTALL
            ):
                anonymous_tags.append(match)
            if len(anonymous_tags) > 0:
                anonymous_tags = sorted(set(anonymous_tags))
                new_tags.extend(anonymous_tags)
        self.tag_monitor.setPlainText(", ".join(new_tags))

    def submit_and_go_to_next_best(self):
        # submit changes of old text
        self.text_navigator.submit()
        # update controls
        self.update_dataset_related_controls()
        self.update_navigation_related_controls()
        # show "all messages annotated" if all texts are annotated
        if not self.textmodel.is_texts_left_for_annotation():
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
            self.textmodel.get_next_best_row_index(self.text_navigator.currentIndex())
        )

    def handle_shortcut_goto(self):
        new_index, is_not_canceled = QInputDialog.getInt(
            self, "Goto Index", "Enter an index:"
        )
        if is_not_canceled:
            self.text_navigator.setCurrentIndex(new_index)

    def handle_about_button_clicked(self):
        QMessageBox.information(self, "About neanno", ABOUT_TEXT, QMessageBox.Ok)

    @staticmethod
    def handle_shortcuts_button_clicked():
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
        message += shortcut_fragment("Undo", SHORTCUT_UNDO)
        message += shortcut_fragment("Redo", SHORTCUT_REDO)
        message += shortcut_fragment("Remove label", SHORTCUT_REMOVE)
        message += shortcut_fragment("Remove all labels", SHORTCUT_REMOVE_ALL)
        message += "</table>"

        msg = QMessageBox()
        msg.setTextFormat(Qt.RichText)
        msg.setIcon(QMessageBox.Information)
        msg.setText(message)
        msg.setWindowTitle("Shortcuts")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def handle_retrain_button_clicked(self):
        self.textmodel.retrain_spacy_model()

    def update_navigation_related_controls(self):
        # current index
        self.current_text_index_label.setText(str(self.text_navigator.currentIndex()))
        # remove focus from controls
        # text_edit
        self.text_edit.clearFocus()
        # text_categories_selector
        if config.is_categories_enabled:
            self.text_categories_selector.clearFocus()

    def update_dataset_related_controls(self):
        # annotated texts count
        annotated_texts_count = self.textmodel.get_annotated_texts_count()
        self.annotated_texts_label.setText(str(annotated_texts_count))
        # total texts count
        total_texts_count = self.textmodel.rowCount()
        self.total_texts_label.setText(str(total_texts_count))
        # categories frequency
        if config.is_categories_enabled:
            self.text_categories_selector.update_categories_distribution()
        # entity infos markup
        if config.is_named_entities_enabled:
            entity_infos_markup = "<table style='font-size: 10pt;' width='100%'>"
            for named_entity_definition in config.named_entity_definitions:
                entity_infos_markup += "<tr>"
                entity_infos_markup += "<td style='background-color:{}; padding-left: 5'> </td>".format(
                    named_entity_definition.maincolor
                )
                entity_infos_markup += "<td style='padding-left: 5'>{}</td>".format(
                    named_entity_definition.code
                )
                entity_infos_markup += "<td style='padding-left: 5'>{}</td>".format(
                    named_entity_definition.key_sequence
                )
                entity_infos_markup += "<td style='width: 100%; text-align: right'>{}</td>".format(
                    str(
                        self.textmodel.entity_distribution[named_entity_definition.code]
                    )
                    if named_entity_definition.code
                    in self.textmodel.entity_distribution
                    else "0"
                )
                entity_infos_markup += "</tr>"
            entity_infos_markup += "</table>"
            self.entity_infos_markup_control.setText(entity_infos_markup)
        # progress
        new_progress_value = (
            self.textmodel.get_annotated_texts_count() * 100 / self.textmodel.rowCount()
        )
        self.progressbar.setValue(new_progress_value)

    def annotate_entity(self):
        text_cursor = self.text_edit.textCursor()
        if text_cursor.hasSelection():
            key_sequence = self.sender().key().toString()
            code = ""
            for named_entity_definition in config.named_entity_definitions:
                if named_entity_definition.key_sequence == key_sequence:
                    code = named_entity_definition.code
                    break
            text_cursor.insertText(
                "(" + text_cursor.selectedText() + "|E " + code + ")"
            )

    def place_named_tag(self):
        text_cursor = self.text_edit.textCursor()
        if text_cursor.hasSelection():
            key_sequence = self.sender().key().toString()
            text_cursor.insertText(
                "("
                + text_cursor.selectedText()
                + "|T "
                + "add_your_tags_here_separated_by_comma"
                + ")"
            )

    def place_anonymous_tag(self):
        text_cursor = self.text_edit.textCursor()
        if text_cursor.hasSelection():
            key_sequence = self.sender().key().toString()
            text_cursor.insertText("(" + text_cursor.selectedText() + "|A)")

    def remove_annotation(self):
        current_cursor_pos = self.text_edit.textCursor().position()
        new_text = re.sub(
            "\((.*?)\|(([ET] .+?)|(A))\)",
            lambda match: match.group(1)
            if match.start() < current_cursor_pos < match.end()
            else match.group(0),
            self.text_edit.toPlainText(),
            flags=re.DOTALL,
        )
        self.text_edit.setPlainText(new_text)

    def remove_all_annotations(self):
        new_text = re.sub(
            "\((.*?)\|(([ET] .+?)|(A))\)",
            lambda match: match.group(1),
            self.text_edit.toPlainText(),
            flags=re.DOTALL,
        )
        self.text_edit.setPlainText(new_text)


class EntityHighlighter(QSyntaxHighlighter):
    """Used to highlight the entities in the text field."""

    highlighting_rules = []

    def __init__(self, parent, named_definitions):
        super(EntityHighlighter, self).__init__(parent)
        postfix_format = self.get_text_char_format(QColor("lightgrey"), Qt.black)
        postfix_format.setFontFamily("Segoe UI")
        postfix_format.setFontWeight(QFont.Bold)
        postfix_format.setFontPointSize(9)
        postfix_format_blank = self.get_text_char_format(
            QColor("lightgrey"), QColor("lightgrey")
        )

        # append highlighting rules
        # tags
        tag_text_format = self.get_text_char_format(
            config.tagging_backcolor, config.tagging_forecolor
        )
        tag_text_format_blank = self.get_text_char_format(
            config.tagging_backcolor, config.tagging_backcolor
        )
        # named tag
        self.highlighting_rules.append(
            (
                QRegularExpression(
                    r"(?<openParen>\()"
                    + r"(?<text>[^|()]+?)"
                    + r"(?<pipeAndType>\|T)"
                    + r"(?<postfix> "
                    + r".*?"
                    + r")(?<closingParen>\))"
                ),
                tag_text_format,
                tag_text_format_blank,
                postfix_format,
                postfix_format_blank,
            )
        )
        # anonymous tag
        self.highlighting_rules.append(
            (
                QRegularExpression(
                    r"(?<openParen>\()"
                    + r"(?<text>[^|()]+?)"
                    + r"(?<pipeAndType>\|A)"
                    + r"(?<closingParen>\))"
                ),
                tag_text_format,
                tag_text_format_blank,
                tag_text_format_blank,
                tag_text_format_blank,
            )
        )
        # named entities
        for named_definition in named_definitions:
            entity_text_format = self.get_text_char_format(
                named_definition.backcolor, named_definition.forecolor
            )
            entity_text_format_blank = self.get_text_char_format(
                named_definition.backcolor, named_definition.backcolor
            )
            self.highlighting_rules.append(
                (
                    QRegularExpression(
                        r"(?<openParen>\()"
                        + r"(?<text>[^|()]+?)"
                        + r"(?<pipeAndType>\|E)"
                        + r"(?<postfix> "
                        + named_definition.code
                        + r")(?<closingParen>\))"
                    ),
                    entity_text_format,
                    entity_text_format_blank,
                    postfix_format,
                    postfix_format_blank,
                )
            )

    def get_text_char_format(self, backcolor, forecolor):
        result = QTextCharFormat()
        result.setBackground(QColor(backcolor))
        result.setForeground(QColor(forecolor))
        return result

    def highlightBlock(self, text):
        for (
            pattern,
            text_format,
            text_format_blank,
            postfix_format,
            postfix_format_blank,
        ) in self.highlighting_rules:
            expression = QRegularExpression(pattern)
            offset = 0
            while offset >= 0:
                match = expression.match(text, offset)
                self.setFormat(match.capturedStart("openParen"), 1, text_format_blank)
                self.setFormat(
                    match.capturedStart("text"),
                    match.capturedLength("text"),
                    text_format,
                )
                self.setFormat(
                    match.capturedStart("pipeAndType"),
                    match.capturedLength("pipeAndType"),
                    text_format_blank,
                )
                self.setFormat(
                    match.capturedStart("postfix"),
                    match.capturedLength("postfix"),
                    postfix_format,
                )
                self.setFormat(
                    match.capturedStart("closingParen"), 1, postfix_format_blank
                )
                offset = match.capturedEnd("closingParen")
