import os
import re

import config
from PyQt5.QtCore import QByteArray, Qt
from PyQt5.QtGui import QIcon, QKeySequence, QTextCursor
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

from neanno.about import show_about_dialog
from neanno.custom_ui_controls import (
    CategoriesSelectorWidget,
    QDataWidgetMapperWithHistory,
)
from neanno.shortcuts import *
from neanno.syntaxhighlighters import TextEditHighlighter


class AnnotationDialog(QMainWindow):
    """ The dialog shown to the user to do the annotation/labeling."""

    def __init__(self, textmodel):
        print("Showing annotation dialog...")
        app = QApplication([])
        super().__init__()
        self.setWindowIcon(self.get_icon("icon.ico"))
        self.textmodel = textmodel
        self.layout_controls()
        self.setup_and_wire_navigator()
        self.setup_and_wire_shortcuts()
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
        self.text_edit_highlighter = TextEditHighlighter(
            self.text_edit.document(), config.named_entity_definitions
        )
        self.text_edit.textChanged.connect(self.update_topic_monitor)

        # topic monitor
        self.topic_monitor = QPlainTextEdit()
        self.topic_monitor.setReadOnly(True)
        self.topic_monitor.setStyleSheet(
            "font-size: 14pt; font-family: Consolas; color: lightgrey; background-color: black"
        )
        self.topic_monitor_entity_highlighter = TextEditHighlighter(
            self.topic_monitor.document(), config.named_entity_definitions
        )

        # navigation / about / shortcuts buttons
        navigation_buttons_layout = QHBoxLayout()
        self.backward_button = QPushButton(self.get_icon("backward.png"), None)
        navigation_buttons_layout.addWidget(self.backward_button)
        self.forward_button = QPushButton(self.get_icon("forward.png"), None)
        navigation_buttons_layout.addWidget(self.forward_button)
        navigation_buttons_layout.addStretch()
        self.first_button = QPushButton(self.get_icon("first.png"), None)
        navigation_buttons_layout.addWidget(self.first_button)
        self.previous_button = QPushButton(self.get_icon("previous.png"), None)
        navigation_buttons_layout.addWidget(self.previous_button)
        self.next_button = QPushButton(self.get_icon("next.png"), None)
        navigation_buttons_layout.addWidget(self.next_button)
        self.last_button = QPushButton(self.get_icon("last.png"), None)
        navigation_buttons_layout.addWidget(self.last_button)
        self.goto_button = QPushButton(self.get_icon("goto.png"), None)
        navigation_buttons_layout.addWidget(self.goto_button)
        self.submit_next_best_button = QPushButton(
            self.get_icon("submit_next_best.png"), None
        )
        navigation_buttons_layout.addWidget(self.submit_next_best_button)
        navigation_buttons_layout.addStretch()
        if config.has_instructions:
            instructions_button = QPushButton("Instructions")
            navigation_buttons_layout.addWidget(instructions_button)
            instructions_button.clicked.connect(
                lambda: QMessageBox.information(
                    self, "Instructions", config.instructions, QMessageBox.Ok
                )
            )
        shortcuts_button = QPushButton("Shortcuts")
        shortcuts_button.clicked.connect(lambda: show_shortcuts_dialog(self))
        navigation_buttons_layout.addWidget(shortcuts_button)
        about_button = QPushButton("About")
        about_button.clicked.connect(lambda: show_about_dialog(self))
        navigation_buttons_layout.addWidget(about_button)

        # progress bar
        self.progressbar = QProgressBar()
        self.progressbar.setValue(0)

        # categories
        # note: CategoriesSelectorWidget populates itself (mostly due to the QTableWidget control, might be improved in future)
        if config.is_categories_enabled:
            self.categories_selector = CategoriesSelectorWidget(config, self.textmodel)
            self.categories_selector.selectionModel().selectionChanged.connect(
                self.update_topic_monitor
            )
            categories_groupbox_layout = QHBoxLayout()
            categories_groupbox_layout.addWidget(self.categories_selector)
            categories_groupbox_layout.setSizeConstraint(QLayout.SetFixedSize)
            categories_groupbox = QGroupBox("Categories")
            categories_groupbox.setLayout(categories_groupbox_layout)

        # key_terms
        if config.is_key_terms_enabled:
            key_terms_layout = QHBoxLayout()
            key_terms_layout.addWidget(
                QLabel(
                    "Select a text and press\n- {} to mark a key term.\n- {} to mark with consolidating terms.".format(
                        config.key_terms_shortcut_mark_standalone,
                        config.key_terms_shortcut_mark_parented,
                    )
                )
            )
            key_terms_groupbox = QGroupBox("Key Terms")
            key_terms_groupbox.setLayout(key_terms_layout)

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
            retrain_model_button.clicked.connect(self.retrain_model)
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
        left_panel_layout_splitter.addWidget(self.topic_monitor)
        left_panel_layout_splitter.setSizes([400, 100])
        left_panel_layout.addWidget(left_panel_layout_splitter)
        # right panel
        right_panel_layout = QVBoxLayout()
        if config.is_categories_enabled:
            right_panel_layout.addWidget(categories_groupbox)
        if config.is_key_terms_enabled:
            right_panel_layout.addWidget(key_terms_groupbox)
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

    def setup_and_wire_shortcuts(self):
        register_shortcut(
            self, config.key_terms_shortcut_mark_parented, self.annotate_parented_key_term
        )
        register_shortcut(
            self,
            config.key_terms_shortcut_mark_standalone,
            self.annotate_standalone_key_term,
        )
        for named_entity_definition in config.named_entity_definitions:
            register_shortcut(
                self, named_entity_definition.key_sequence, self.annotate_entity
            )
        register_shortcut(
            self, SHORTCUT_SUBMIT_NEXT_BEST, self.submit_and_go_to_next_best
        )
        register_shortcut(self, SHORTCUT_BACKWARD, self.navigator.backward)
        register_shortcut(self, SHORTCUT_FORWARD, self.navigator.forward)
        register_shortcut(self, SHORTCUT_FIRST, self.navigator.toFirst)
        register_shortcut(self, SHORTCUT_PREVIOUS, self.navigator.toPrevious)
        register_shortcut(self, SHORTCUT_NEXT, self.navigator.toNext)
        register_shortcut(self, SHORTCUT_LAST, self.navigator.toLast)
        register_shortcut(self, SHORTCUT_GOTO, self.go_to_index)
        register_shortcut(self, SHORTCUT_REMOVE, self.remove_annotation)
        register_shortcut(self, SHORTCUT_REMOVE_ALL, self.remove_all_annotations)

    def setup_and_wire_navigator(self):
        self.navigator = QDataWidgetMapperWithHistory(self)
        self.navigator.setSubmitPolicy(QDataWidgetMapper.ManualSubmit)
        self.navigator.setModel(self.textmodel)
        self.navigator.addMapping(self.text_edit, 0)
        self.navigator.addMapping(
            self.is_annotated_label, 1, QByteArray().insert(0, "text")
        )
        if config.is_categories_enabled:
            self.navigator.addMapping(
                self.categories_selector,
                2,
                QByteArray().insert(0, "selected_categories_text"),
            )
        self.navigator.currentIndexChanged.connect(
            self.update_navigation_related_controls
        )
        self.navigator.setCurrentIndex(self.textmodel.get_next_best_row_index(-1))
        self.backward_button.clicked.connect(self.navigator.backward)
        self.forward_button.clicked.connect(self.navigator.forward)
        self.first_button.clicked.connect(self.navigator.toFirst)
        self.previous_button.clicked.connect(self.navigator.toPrevious)
        self.next_button.clicked.connect(self.navigator.toNext)
        self.last_button.clicked.connect(self.navigator.toLast)
        self.goto_button.clicked.connect(self.go_to_index)
        self.submit_next_best_button.clicked.connect(self.submit_and_go_to_next_best)

    def update_topic_monitor(self):
        new_topics = []
        categories_to_add = []
        if config.is_categories_enabled:
            categories_to_add.extend(self.categories_selector.get_selected_categories())
        # standalone/parented key terms, named entities
        for match in re.finditer(
            r"\((?P<text>[^()]+?)\|(?P<type>(SK|PK|NE))( (?P<postfix>[^()]+?))?\)",
            self.text_edit.toPlainText(),
            flags=re.DOTALL,
        ):
            text = match.group("text")
            type = match.group("type")
            postfix = match.group("postfix")
            # standalone key term
            if type == "SK":
                topic_to_add = text
                if topic_to_add.lower() not in [
                    topic.lower() for topic in new_topics
                ] and topic_to_add.lower() not in [
                    category.lower() for category in categories_to_add
                ]:
                    new_topics.append(topic_to_add)
            # parented key terms
            if type == "PK":
                term_topics = []
                for topic in postfix.split(","):
                    topic_to_add = topic.strip()
                    if topic_to_add.lower() not in [
                        topic.lower() for topic in new_topics
                    ] and topic_to_add.lower() not in [
                        category.lower() for category in categories_to_add
                    ]:
                        term_topics.append(topic_to_add)
                new_topics.extend(sorted(term_topics))
            # named entity
            if type == "NE":
                topic_to_add = "{}:{}".format(postfix.lower(), text)
                if topic_to_add.lower() not in [
                    topic.lower() for topic in new_topics
                ] and topic_to_add.lower() not in [
                    category.lower() for category in categories_to_add
                ]:
                    new_topics.append(topic_to_add)
        ## categories (not sure yet if this should be included)
        ##if config.is_categories_enabled:
        ##    new_topics.extend(categories_to_add)

        # update topics
        self.topic_monitor.setPlainText(", ".join(new_topics))

    def submit_and_go_to_next_best(self):
        # submit changes of old text
        self.navigator.submit()
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
        self.navigator.setCurrentIndex(
            self.textmodel.get_next_best_row_index(self.navigator.currentIndex())
        )

    def go_to_index(self):
        new_index, is_not_canceled = QInputDialog.getInt(
            self, "Goto Index", "Enter an index:"
        )
        if is_not_canceled:
            self.navigator.setCurrentIndex(new_index)

    def retrain_model(self):
        self.textmodel.retrain_spacy_model()

    def update_navigation_related_controls(self):
        # current index
        self.current_text_index_label.setText(str(self.navigator.currentIndex()))
        # remove focus from controls
        # text_edit
        self.text_edit.clearFocus()
        # categories_selector
        if config.is_categories_enabled:
            self.categories_selector.clearFocus()

    def update_dataset_related_controls(self):
        # annotated texts count
        annotated_texts_count = self.textmodel.get_annotated_texts_count()
        self.annotated_texts_label.setText(str(annotated_texts_count))
        # total texts count
        total_texts_count = self.textmodel.rowCount()
        self.total_texts_label.setText(str(total_texts_count))
        # categories frequency
        if config.is_categories_enabled:
            self.categories_selector.update_categories_distribution()
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
            text_cursor.insertText("({}|NE {})".format(text_cursor.selectedText(), code))

    def annotate_parented_key_term(self):
        text_cursor = self.text_edit.textCursor()
        if text_cursor.hasSelection():
            default_parent_key_term = (
                "<add your consolidating terms here, separated by commas>"
            )
            orig_selection_start = text_cursor.selectionStart()
            new_selection_start = orig_selection_start + len(
                "({}|PK ".format(text_cursor.selectedText())
            )
            new_selection_end = new_selection_start + len(default_parent_key_term)
            text_cursor.insertText(
                "({}|PK {})".format(text_cursor.selectedText(), default_parent_key_term)
            )
            text_cursor.setPosition(new_selection_start)
            text_cursor.setPosition(new_selection_end, QTextCursor.KeepAnchor)
            self.text_edit.setTextCursor(text_cursor)

    def annotate_standalone_key_term(self):
        text_cursor = self.text_edit.textCursor()
        if text_cursor.hasSelection():
            text_cursor.insertText("({}|SK)".format(text_cursor.selectedText()))

    def remove_annotation(self):
        current_cursor_pos = self.text_edit.textCursor().position()
        new_text = re.sub(
            r"\((.*?)\|(((PK|NE) .+?)|(SK))\)",
            lambda match: match.group(1)
            if match.start() < current_cursor_pos < match.end()
            else match.group(0),
            self.text_edit.toPlainText(),
            flags=re.DOTALL,
        )
        self.text_edit.setPlainText(new_text)

    def remove_all_annotations(self):
        new_text = re.sub(
            r"\((.*?)\|(((PK|NE) .+?)|(SK))\)",
            lambda match: match.group(1),
            self.text_edit.toPlainText(),
            flags=re.DOTALL,
        )
        self.text_edit.setPlainText(new_text)
        self.categories_selector.set_selected_categories_by_text("")
