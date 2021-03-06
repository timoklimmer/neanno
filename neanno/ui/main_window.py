import base64
import os
from abc import abstractmethod

import config
from PyQt5.QtCore import *
from PyQt5.QtCore import QByteArray
from PyQt5.QtGui import QIcon, QTextCursor
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDataWidgetMapper,
    QDesktopWidget,
    QDockWidget,
    QGridLayout,
    QGroupBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLayout,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QTextEdit,
)

from neanno.configuration.configmanager import ConfigManager
from neanno.models.textmodel import TextModel
from neanno.ui.about import show_about_dialog
from neanno.ui.category_selection import CategoriesSelectorWidget
from neanno.ui.predictor_management import ManagePredictorsDialog
from neanno.ui.shortcuts import *
from neanno.ui.syntax_highlighting import TextEditHighlighter
from neanno.ui.text_navigation import TextNavigator
from neanno.utils.multithreading import ParallelWorker, ParallelWorkerSignals
from neanno.utils.text import *

DEFAULT_PARENT_KEY_TERM = "<add your consolidating terms here, separated by commas>"


class MainWindow(QMainWindow):
    """ The dialog shown to the user to do the annotation/labeling."""

    def __init__(self):
        """Constructor."""

        app = QApplication([])
        super().__init__()

        self.setWindowIcon(self.get_icon("icon.ico"))
        screen = QDesktopWidget().screenGeometry()
        self.setGeometry(0, 0, screen.width() * 0.75, screen.height() * 0.85)
        window_size = self.geometry()
        horizontal_position = (screen.width() - window_size.width()) / 2
        vertical_position = (screen.height() - window_size.height()) / 6
        self.move(horizontal_position, vertical_position)

        ConfigManager.init()
        self.textmodel = TextModel()
        self.layout_controls()
        self.setup_and_wire_navigator_incl_buttons()
        self.setup_and_wire_shortcuts()

        self.show()
        app.exec_()

    @staticmethod
    def get_icon(file):
        return QIcon(
            os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                "../resources/{}".format(file),
            )
        )

    def layout_controls(self):
        # window
        self.setWindowTitle("neanno")
        # text edit
        self.textedit = QPlainTextEdit()
        self.textedit.setStyleSheet(
            """QPlainTextEdit {
                font-size: 14pt;
                font-family: Consolas;Monospace;
                color: lightgrey;
                background-color: black
            }"""
        )
        self.textedit_highlighter = TextEditHighlighter(
            self.textedit.document(), config.named_entity_definitions
        )
        self.textedit.textChanged.connect(self.textedit_text_changed)

        # annotation monitor
        self.annotation_monitor = QPlainTextEdit()
        self.annotation_monitor.setReadOnly(True)
        self.annotation_monitor.setStyleSheet(
            """
                font-size: 14pt;
                font-family: Consolas;
                color: lightgrey;
                background-color: black
            """
        )

        # navigation / about / shortcuts buttons
        navigation_buttons_layout = QHBoxLayout()
        self.backward_button = QPushButton(self.get_icon("backward.png"), None)
        self.backward_button.setToolTip("Backward")
        navigation_buttons_layout.addWidget(self.backward_button)
        self.forward_button = QPushButton(self.get_icon("forward.png"), None)
        self.forward_button.setToolTip("Forward")
        navigation_buttons_layout.addWidget(self.forward_button)
        navigation_buttons_layout.addStretch()
        self.first_button = QPushButton(self.get_icon("first.png"), None)
        self.first_button.setToolTip("First")
        navigation_buttons_layout.addWidget(self.first_button)
        self.previous_button = QPushButton(self.get_icon("previous.png"), None)
        self.previous_button.setToolTip("Previous")
        navigation_buttons_layout.addWidget(self.previous_button)
        self.next_button = QPushButton(self.get_icon("next.png"), None)
        self.next_button.setToolTip("Next")
        navigation_buttons_layout.addWidget(self.next_button)
        self.last_button = QPushButton(self.get_icon("last.png"), None)
        self.last_button.setToolTip("Last")
        navigation_buttons_layout.addWidget(self.last_button)
        self.goto_button = QPushButton(self.get_icon("goto.png"), None)
        self.goto_button.setToolTip("Go to index")
        navigation_buttons_layout.addWidget(self.goto_button)
        self.search_button = QPushButton(self.get_icon("search.png"), None)
        self.search_button.setToolTip("Search a text")
        navigation_buttons_layout.addWidget(self.search_button)
        self.submit_next_best_button = QPushButton(
            self.get_icon("submit_next_best.png"), None
        )
        self.submit_next_best_button.setToolTip("Submit and go to next best text")
        navigation_buttons_layout.addWidget(self.submit_next_best_button)
        navigation_buttons_layout.addStretch()
        if config.has_instructions:
            instructions_button = QPushButton("Instructions")
            instructions_button.setToolTip("Instructions")
            navigation_buttons_layout.addWidget(instructions_button)
            instructions_button.clicked.connect(
                lambda: QMessageBox.information(
                    self, "Instructions", config.instructions, QMessageBox.Ok
                )
            )
        shortcuts_button = QPushButton("Shortcuts")
        shortcuts_button.setToolTip("Show general shortcuts")
        shortcuts_button.clicked.connect(lambda: show_shortcuts_dialog(self))
        navigation_buttons_layout.addWidget(shortcuts_button)
        about_button = QPushButton("About")
        about_button.setToolTip("About")
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
                self.update_annotation_monitor
            )
            categories_groupbox_layout = QHBoxLayout()
            categories_groupbox_layout.addWidget(self.categories_selector)
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
            named_entity_infos_layout = QHBoxLayout()
            self.named_entity_infos_markup_control = QLabel()
            self.named_entity_infos_markup_control.setTextFormat(Qt.RichText)
            named_entity_infos_layout.addWidget(self.named_entity_infos_markup_control)
            named_entities_groupbox = QGroupBox("Named Entities")
            named_entities_groupbox.setLayout(named_entity_infos_layout)

        # language
        if config.uses_languages:
            language_layout = QHBoxLayout()
            self.language_combobox = QComboBox()
            self.language_combobox.addItems(config.languages_available_for_selection)
            language_layout.addWidget(self.language_combobox)
            language_groupbox = QGroupBox("Language")
            language_groupbox.setLayout(language_layout)

        # predictors
        if config.prediction_pipeline.has_predictors():
            predictors_from_vertical_layout = QVBoxLayout()

            # Train Batch Models
            self.train_batch_models_button = QPushButton("Train Batch Models")
            self.train_batch_models_button.clicked.connect(self.train_batch_models)
            predictors_from_vertical_layout.addWidget(self.train_batch_models_button)

            # Test Models
            self.test_models_button = QPushButton("Test Models")
            self.test_models_button.clicked.connect(self.test_models)
            self.test_models_button.setEnabled(False)
            predictors_from_vertical_layout.addWidget(self.test_models_button)

            # Export Pipeline Model
            # export_pipeline_model_button = QPushButton("Export Pipeline Model")
            # export_pipeline_model_button.clicked.connect(self.export_pipeline_model)
            # predictors_from_vertical_layout.addWidget(export_pipeline_model_button)

            # Manage Predictors
            self.manage_predictors_button = QPushButton("Manage Predictors")
            self.manage_predictors_button.clicked.connect(self.manage_predictors)
            predictors_from_vertical_layout.addWidget(self.manage_predictors_button)

            # Predictors groupbox
            predictors_from_groupbox = QGroupBox("Predictors")
            predictors_from_groupbox.setLayout(predictors_from_vertical_layout)

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
        close_button.setToolTip("Close")
        close_button.clicked.connect(self.close)

        # left top/bottom splitter
        left_top_bottom_splitter = QSplitter(Qt.Vertical)
        left_top_bottom_splitter.addWidget(self.textedit)
        left_top_bottom_splitter.setCollapsible(0, False)
        left_top_bottom_splitter.addWidget(self.annotation_monitor)
        left_top_bottom_splitter.setCollapsible(1, False)
        left_top_bottom_splitter.setSizes([400, 100])

        # left panel
        left_panel_layout = QVBoxLayout()
        left_panel_layout.addWidget(left_top_bottom_splitter)
        left_panel_layout.addLayout(navigation_buttons_layout)

        # right panel
        right_panel_layout = QVBoxLayout()
        if config.is_categories_enabled:
            right_panel_layout.addWidget(categories_groupbox)
        if config.is_key_terms_enabled:
            right_panel_layout.addWidget(key_terms_groupbox)
        if config.is_named_entities_enabled:
            right_panel_layout.addWidget(named_entities_groupbox)
        if config.uses_languages:
            right_panel_layout.addWidget(language_groupbox)
        if config.prediction_pipeline.has_predictors():
            right_panel_layout.addWidget(predictors_from_groupbox)
        right_panel_layout.addWidget(dataset_groupbox)
        right_panel_layout.addStretch()
        right_buttons_layout = QHBoxLayout()
        right_buttons_layout.addStretch()
        right_buttons_layout.addWidget(close_button)
        right_panel_layout.addLayout(right_buttons_layout)

        # left/right splitter
        left_right_splitter = QSplitter(Qt.Horizontal)
        left_panel_layout_as_widget = QWidget()
        left_panel_layout_as_widget.setLayout(left_panel_layout)
        left_right_splitter.addWidget(left_panel_layout_as_widget)
        left_right_splitter.setCollapsible(0, False)
        right_panel_layout_as_widget = QWidget()
        right_panel_layout_as_widget.setLayout(right_panel_layout)
        left_right_splitter.addWidget(right_panel_layout_as_widget)
        left_right_splitter.setCollapsible(1, False)
        left_right_splitter.setSizes([100000, -1])

        # main
        self.setCentralWidget(left_right_splitter)

        # output
        self.output_pane_text_edit = QTextBrowser()
        self.output_pane_text_edit.setStyleSheet(
            """QTextBrowser {
                font-size: 10pt;
                font-family: Consolas;Monospace;
            }"""
        )
        self.output_pane_text_edit.setReadOnly(True)
        self.output_pane_text_edit.setOpenLinks(False)
        self.output_pane_text_edit.setLineWrapMode(QTextEdit.NoWrap)

        self.output_pane_text_edit.anchorClicked.connect(
            self.handle_anchorClicked_from_output_pane_text_edit
        )
        self.output_pane = QDockWidget("Output", self)
        self.output_pane.setFeatures(
            QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable
            | QDockWidget.DockWidgetFloatable
        )
        self.output_pane.setWidget(self.output_pane_text_edit)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.output_pane)
        self.output_pane.setHidden(True)

        # update the dataset-related controls so they show up
        self.update_dataset_related_controls()

    def setup_and_wire_shortcuts(self):
        # annotate key terms shortcuts
        if config.is_key_terms_enabled:
            register_shortcut(
                self,
                config.key_terms_shortcut_mark_parented,
                self.annotate_parented_key_term,
            )
            register_shortcut(
                self,
                config.key_terms_shortcut_mark_standalone,
                self.annotate_standalone_key_term,
            )
        # named entity shortcuts
        for named_entity_definition in config.named_entity_definitions:
            # standalone
            register_shortcut(
                self,
                named_entity_definition.key_sequence,
                self.annotate_standalone_named_entity,
            )
            # parented
            register_shortcut(
                self,
                "Shift+{}".format(named_entity_definition.key_sequence),
                self.annotate_parented_named_entity,
            )
        # submit next
        register_shortcut(self, SHORTCUT_SUBMIT_NEXT, self.submit_and_go_to_next)
        # submit next best
        register_shortcut(
            self, SHORTCUT_SUBMIT_NEXT_BEST, self.submit_and_go_to_next_best
        )
        # mark all text as annotated
        register_shortcut(
            self, SHORTCUT_MARK_ALL_AS_ANNOTATED, self.mark_all_texts_as_annotated
        )
        # navigation shortcuts
        register_shortcut(self, SHORTCUT_BACKWARD, self.navigator.backward)
        register_shortcut(self, SHORTCUT_FORWARD, self.navigator.forward)
        register_shortcut(self, SHORTCUT_FIRST, self.navigator.toFirst)
        register_shortcut(self, SHORTCUT_PREVIOUS, self.navigator.toPrevious)
        register_shortcut(self, SHORTCUT_NEXT, self.navigator.toNext)
        register_shortcut(self, SHORTCUT_LAST, self.navigator.toLast)
        register_shortcut(self, SHORTCUT_GOTO, self.go_to_index)
        register_shortcut(self, SHORTCUT_SEARCH, self.search)
        # remove/reset/revert/... shortcuts
        register_shortcut(
            self, SHORTCUT_REMOVE_ANNOTATION_AT_CURSOR, self.remove_annotation
        )
        register_shortcut(
            self,
            SHORTCUT_REMOVE_ALL_ANNOTATIONS_OF_CURRENT_TEXT,
            self.remove_all_annotations,
        )
        register_shortcut(
            self,
            SHORTCUT_REMOVE_ALL_ANNOTATIONS_FROM_DATASET,
            self.remove_all_annotations_from_dataset,
        )
        register_shortcut(self, SHORTCUT_REVERT_CHANGES, self.revert_changes)

    def setup_and_wire_navigator_incl_buttons(self):
        self.navigator = TextNavigator(self)
        self.navigator.setSubmitPolicy(QDataWidgetMapper.ManualSubmit)
        self.navigator.setModel(self.textmodel)
        if config.uses_languages:
            self.navigator.addMapping(self.language_combobox, 0)
        self.navigator.addMapping(self.textedit, 1)
        if config.is_categories_enabled:
            self.navigator.addMapping(
                self.categories_selector,
                2,
                QByteArray().insert(0, "selected_categories_text"),
            )
        self.navigator.addMapping(
            self.is_annotated_label, 3, QByteArray().insert(0, "text")
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
        self.search_button.clicked.connect(self.search)
        self.submit_next_best_button.clicked.connect(self.submit_and_go_to_next_best)

    def update_navigation_related_controls(self):
        # current index
        self.current_text_index_label.setText(str(self.navigator.currentIndex()))
        # remove focus from controls
        if config.uses_languages:
            self.language_combobox.clearFocus()
        # textedit
        self.textedit.clearFocus()
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
            entity_infos_markup = "<table width='100%'>"
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
                        self.textmodel.named_entity_distribution[
                            named_entity_definition.code
                        ]
                    )
                    if named_entity_definition.code
                    in self.textmodel.named_entity_distribution
                    else "0"
                )
                entity_infos_markup += "</tr>"
            entity_infos_markup += "</table>"
            entity_infos_markup += "<p>Add Shift key to add consolidating terms.</p>"
            self.named_entity_infos_markup_control.setText(entity_infos_markup)
        # progress
        new_progress_value = (
            self.textmodel.get_annotated_texts_count() * 100 / self.textmodel.rowCount()
        )
        self.progressbar.setValue(new_progress_value)

    def textedit_text_changed(self):
        self.sync_parented_annotations()
        self.update_annotation_monitor()

    def sync_parented_annotations(self):
        # get annotation at current cursor position
        annotation_at_current_cursor_pos = get_annotation_at_position(
            self.textedit.toPlainText(), self.textedit.textCursor().position()
        )
        # update annotation for same parented keyterm
        if annotation_at_current_cursor_pos is not None and annotation_at_current_cursor_pos[
            "type"
        ] in [
            "parented_key_term",
            "parented_named_entity",
        ]:
            if annotation_at_current_cursor_pos["type"] == "parented_key_term":
                text_to_replace_pattern = r"`{}``PK``.*?`´".format(
                    re.escape(annotation_at_current_cursor_pos["term"])
                )
                replace_against_text = "`{}``PK``{}`´".format(
                    annotation_at_current_cursor_pos["term"],
                    annotation_at_current_cursor_pos["parent_terms_raw"],
                )
            if annotation_at_current_cursor_pos["type"] == "parented_named_entity":
                text_to_replace_pattern = r"`{}``PN``{}``.*?`´".format(
                    re.escape(annotation_at_current_cursor_pos["term"]),
                    re.escape(annotation_at_current_cursor_pos["entity_code"]),
                )
                replace_against_text = "`{}``PN``{}``{}`´".format(
                    annotation_at_current_cursor_pos["term"],
                    annotation_at_current_cursor_pos["entity_code"],
                    annotation_at_current_cursor_pos["parent_terms_raw"],
                )
            self.replace_pattern_in_textedit(
                text_to_replace_pattern, replace_against_text
            )

    def update_annotation_monitor(self):
        self.annotation_monitor.setPlainText(
            extract_annotations_as_text(
                self.textedit.toPlainText(),
                entity_codes_to_extract=config.named_entity_codes,
            )
        )

    def go_to_index(self):
        new_index, is_not_canceled = QInputDialog.getInt(
            self, "Goto Index", "Enter an index:"
        )
        if is_not_canceled:
            self.navigator.setCurrentIndex(new_index)

    def search(self):
        searched_text, is_not_canceled = QInputDialog.getText(
            self,
            "Search a text",
            'Enter the substring or regex pattern by which you want to find another text.\n\nIf you prefix with "regex:", your input will be interpreted as a regex pattern.',
        )
        if is_not_canceled:
            new_index = self.textmodel.get_index_of_next_text_which_contains_substring(
                searched_text, self.navigator.currentIndex()
            )
            if new_index is not None:
                self.navigator.setCurrentIndex(new_index)
            else:
                QMessageBox.information(
                    self,
                    "Information",
                    "Could not find a text containing '{}'".format(searched_text),
                    QMessageBox.Ok,
                )

    def annotate_standalone_key_term(self):
        text_cursor = self.textedit.textCursor()
        if text_cursor.hasSelection():
            text_to_replace = text_cursor.selectedText()
            text_to_replace_pattern = r"(?<!`){}(?!``SK`´)".format(
                re.escape(text_to_replace)
            )
            replace_against_text = "`{}``SK`´".format(
                remove_all_annotations_from_text(text_to_replace)
            )
            self.replace_pattern_in_textedit(
                text_to_replace_pattern, replace_against_text
            )

    def annotate_parented_key_term(self):
        text_cursor = self.textedit.textCursor()
        if text_cursor.hasSelection():
            text_to_replace = text_cursor.selectedText()
            text_to_replace_pattern = r"(?<!`){}(?!``PK``.*?`´)".format(
                re.escape(text_to_replace)
            )
            orig_selection_start = text_cursor.selectionStart()
            new_selection_start = orig_selection_start + len(
                "`{}``PK``".format(remove_all_annotations_from_text(text_to_replace))
            )
            new_selection_end = new_selection_start + len(DEFAULT_PARENT_KEY_TERM)
            replace_against_text = "`{}``PK``{}`´".format(
                remove_all_annotations_from_text(text_to_replace),
                DEFAULT_PARENT_KEY_TERM,
            )
            self.replace_pattern_in_textedit(
                text_to_replace_pattern, replace_against_text
            )
            text_cursor.setPosition(new_selection_start)
            text_cursor.setPosition(new_selection_end, QTextCursor.KeepAnchor)
            self.textedit.setTextCursor(text_cursor)

    def annotate_standalone_named_entity(self):
        text_cursor = self.textedit.textCursor()
        if text_cursor.hasSelection():
            selected_text = text_cursor.selectedText()
            term = remove_all_annotations_from_text(selected_text)
            named_entity_definition = ConfigManager.get_named_entity_definition_by_key_sequence(
                self.sender().key().toString()
            )
            entity_code = named_entity_definition.code
            parent_terms_candidate = config.prediction_pipeline.get_parent_terms_for_named_entity(
                term, entity_code
            )
            if parent_terms_candidate:
                text_cursor.insertText(
                    "`{}``PN``{}``{}`´".format(
                        term, named_entity_definition.code, parent_terms_candidate
                    )
                )
            else:
                text_cursor.insertText(
                    "`{}``SN``{}`´".format(term, named_entity_definition.code)
                )

    def annotate_parented_named_entity(self):
        text_cursor = self.textedit.textCursor()
        if text_cursor.hasSelection():
            named_entity_definition = ConfigManager.get_named_entity_definition_by_key_sequence(
                self.sender().key().toString()
            )
            entity_code = named_entity_definition.code
            text_to_replace = text_cursor.selectedText()
            text_to_replace_pattern = r"(?<!`){}(?!``PN``{}``.*?`´)".format(
                re.escape(text_to_replace), re.escape(entity_code)
            )
            orig_selection_start = text_cursor.selectionStart()
            term = remove_all_annotations_from_text(text_to_replace)
            new_selection_start = orig_selection_start + len(
                "`{}``PN``{}``".format(term, entity_code)
            )
            parent_terms_candidate = config.prediction_pipeline.get_parent_terms_for_named_entity(
                term, entity_code
            )
            parent_terms = (
                parent_terms_candidate
                if parent_terms_candidate is not None
                else DEFAULT_PARENT_KEY_TERM
            )
            new_selection_end = new_selection_start + len(parent_terms)
            replace_against_text = "`{}``PN``{}``{}`´".format(
                remove_all_annotations_from_text(text_to_replace),
                named_entity_definition.code,
                parent_terms,
            )
            self.replace_pattern_in_textedit(
                text_to_replace_pattern, replace_against_text
            )
            if not parent_terms_candidate:
                text_cursor.setPosition(new_selection_start)
                text_cursor.setPosition(new_selection_end, QTextCursor.KeepAnchor)
            self.textedit.setTextCursor(text_cursor)

    def mark_annotation_for_removal(self, annotation):
        if annotation["type"] in ["standalone_key_term", "parented_key_term"]:
            config.prediction_pipeline.mark_key_term_for_removal(annotation["term"])
        if annotation["type"] in ["standalone_named_entity", "parented_named_entity"]:
            config.prediction_pipeline.mark_named_entity_term_for_removal(
                annotation["term"], annotation["entity_code"]
            )

    def remove_annotation(self):
        annotation = get_annotation_at_position(
            self.textedit.toPlainText(), self.textedit.textCursor().position()
        )
        # ensure there is an annotation to remove
        if annotation is not None:
            # get the replace pattern and replace against text
            if annotation["type"] in ["standalone_key_term", "parented_key_term"]:
                text_to_replace_pattern = r"`{}``(SK|PK).*?`´".format(
                    re.escape(annotation["term"])
                )
            if annotation["type"] in [
                "standalone_named_entity",
                "parented_named_entity",
            ]:
                text_to_replace_pattern = r"`{}``(SN|PN)``{}.*?`´".format(
                    re.escape(annotation["term"]), re.escape(annotation["entity_code"])
                )
            replace_against_text = annotation["term"]
            # do the replace
            self.replace_pattern_in_textedit(
                text_to_replace_pattern, replace_against_text
            )
            # mark annotation for removal
            self.mark_annotation_for_removal(annotation)

    def remove_all_annotations(self):
        # mark all key terms and named entities for removal
        for annotation in extract_annotations_as_generator(self.textedit.toPlainText()):
            self.mark_annotation_for_removal(annotation)

        # update text
        self.textedit.setPlainText(
            remove_all_annotations_from_text(self.textedit.toPlainText())
        )

        # clear categories if categories are
        if config.is_categories_enabled:
            self.categories_selector.set_selected_categories_by_text("")

    def reset_is_annotated_flag(self):
        self.textmodel.unset_is_annotated_for_index(self.navigator.getCurrentIndex())
        self.is_annotated_label.setText("False")

    def remove_all_annotations_from_dataset(self):
        if (
            QMessageBox.question(
                self,
                "Confirmation",
                "This will reset all Is Annotated flags and save the dataset to its target. You may end up in big trouble if you don't know what you are doing.\n\nAre you sure you want to do the reset and save?",
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            self.textmodel.remove_all_annotations_from_dataset()
            self.navigator.navigate_to_same_index()

    def revert_changes(self):
        self.navigator.revert()

    def submit(self):
        # submit changes of model-bound controls
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

    def submit_and_go_to_next(self):
        # submit
        self.submit()
        # identify and go to next text
        self.navigator.setCurrentIndex(
            self.textmodel.get_next_row_index(self.navigator.currentIndex())
        )

    def submit_and_go_to_next_best(self):
        # submit
        self.submit()
        # identify and go to next best text
        self.navigator.setCurrentIndex(
            self.textmodel.get_next_best_row_index(self.navigator.currentIndex())
        )

    def mark_all_texts_as_annotated(self):
        if (
            QMessageBox.question(
                self,
                "Confirmation",
                "This will mark all texts as annotated and save the dataset. You may end up in big trouble if you don't know what you are doing.\n\nAre you sure you want to set the marks and save?",
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            self.textmodel.mark_all_texts_as_annotated()
            self.navigator.navigate_to_same_index()

    def train_batch_models(self):
        if self.textmodel.get_annotated_texts_count() < 10:
            QMessageBox.information(
                self,
                "Unfortunately...",
                "There are not enough annotated texts for training models. Annotate at least 10 texts to enable this feature.",
                QMessageBox.Ok,
            )
        else:
            trainset = self.textmodel.get_trainset()
            config.prediction_pipeline.train_from_trainset_async(
                trainset=trainset,
                text_column=config.text_column,
                is_annotated_column=config.is_annotated_column,
                language_column=config.language_column,
                categories_column=config.categories_column,
                categories_to_train=config.categories_names_list,
                entity_codes_to_train=config.named_entity_codes,
                signals_handler=BatchTrainingSignalsHandler(self),
            )

    def test_models(self):
        testset, testset_size = self.textmodel.get_testset()
        if testset is None or testset.size < 10:
            QMessageBox.information(
                self,
                "Unfortunately...",
                "There are not enough annotated texts for testing models or there was no model training before. Annotate at least 10 texts and do a batch model training to enable this feature.",
                QMessageBox.Ok,
            )
        else:
            config.prediction_pipeline.test_models_async(
                testset=testset,
                testset_size=testset_size,
                text_column=config.text_column,
                is_annotated_column=config.is_annotated_column,
                language_column=config.language_column,
                categories_column=config.categories_column,
                categories_to_train=config.categories_names_list,
                entity_codes_to_train=config.named_entity_codes,
                signals_handler=ModelValidationSignalsHandler(self),
            )

    def manage_predictors(self):
        ManagePredictorsDialog.show(self)
        self.navigator.navigate_to_same_index()

    def export_pipeline_model(self):
        QMessageBox.information(
            self,
            "Unfortunately...",
            "...this feature has not been implemented yet but some predictors save their own models already. Check back soon.",
            QMessageBox.Ok,
        )

    def replace_pattern_in_textedit(self, replace_pattern, replace_against_text):
        text_cursor = self.textedit.textCursor()
        text_cursor_backup = self.textedit.textCursor()
        compiled_pattern = re.compile(replace_pattern, flags=re.DOTALL)
        current_position = 0
        match = compiled_pattern.search(self.textedit.toPlainText(), current_position)
        while match is not None:
            if match.group() != replace_against_text:
                text_cursor.setPosition(match.start())
                text_cursor.setPosition(match.end(), QTextCursor.KeepAnchor)
                text_cursor.insertText(replace_against_text)
            current_position = match.end()
            match = compiled_pattern.search(
                self.textedit.toPlainText(), current_position
            )
        self.textedit.setTextCursor(text_cursor_backup)

    def insert_text_to_output_pane_text_edit(self, message, end):
        self.output_pane_text_edit.moveCursor(QTextCursor.End)
        self.output_pane_text_edit.insertPlainText(message + end)
        self.output_pane_text_edit.moveCursor(QTextCursor.End)

    def insert_image_to_output_pane_text_edit(self, image_bytes, image_format):
        image_bytes_in_base64 = base64.b64encode(image_bytes)
        image_bytes_in_base64_utf8_decoded = image_bytes_in_base64.decode("utf-8")
        self.output_pane_text_edit.moveCursor(QTextCursor.End)
        self.output_pane_text_edit.insertHtml(
            '<img src="data:image/{};base64,{}"/>'.format(
                image_format, image_bytes_in_base64_utf8_decoded
            )
        )
        self.output_pane_text_edit.insertPlainText("\n")
        self.output_pane_text_edit.moveCursor(QTextCursor.End)

    def insert_export_output_pane_contents_link(self):
        self.insert_text_to_output_pane_text_edit("", "\n")
        self.output_pane_text_edit.insertHtml(
            'Click <a href="neanno:exportOutputPane">here</a> to export the output.'
        )

    def handle_anchorClicked_from_output_pane_text_edit(self, url):
        action = url.toString()
        if action == "neanno:exportOutputPane":
            target_file_name, _ = QFileDialog.getSaveFileName(
                QDesktopWidget(), "Export output", "", "Output (*.html)"
            )
            if target_file_name:
                with open(target_file_name, "w") as target_file:
                    target_file.write(self.output_pane_text_edit.toHtml())
                QMessageBox.information(self, "Success", "Export completed.", QMessageBox.Ok)
        else:
            raise ValueError("There is no handler for action '{}'.".format(action))

    @pyqtSlot()
    def batch_training_started(self):
        self.train_batch_models_button.setEnabled(False)
        self.manage_predictors_button.setEnabled(False)
        self.train_batch_models_button_original_label = (
            self.train_batch_models_button.text()
        )
        self.train_batch_models_button.setText("Training Batch Models...")
        self.output_pane_text_edit.clear()
        self.output_pane.setHidden(False)

    @pyqtSlot(str, str)
    def batch_training_message(self, message, end):
        self.insert_text_to_output_pane_text_edit(message, end)

    @pyqtSlot(bytes, str)
    def batch_training_image(self, image_bytes, image_format):
        self.insert_image_to_output_pane_text_edit(image_bytes, image_format)

    @pyqtSlot()
    def batch_training_completed(self):
        self.train_batch_models_button.setText(
            self.train_batch_models_button_original_label
        )
        self.train_batch_models_button.setEnabled(True)
        self.test_models_button.setEnabled(True)
        self.manage_predictors_button.setEnabled(True)
        self.insert_export_output_pane_contents_link()

    @pyqtSlot()
    def model_testing_started(self):
        self.train_batch_models_button.setEnabled(False)
        self.test_models_button.setEnabled(False)
        self.manage_predictors_button.setEnabled(False)
        self.output_pane_text_edit.clear()
        self.output_pane.setHidden(False)

    @pyqtSlot(str, str)
    def model_testing_message(self, message, end):
        self.insert_text_to_output_pane_text_edit(message, end)

    @pyqtSlot(bytes, str)
    def model_testing_image(self, image_bytes, image_format):
        self.insert_image_to_output_pane_text_edit(image_bytes, image_format)

    @pyqtSlot()
    def model_testing_completed(self):
        self.train_batch_models_button.setEnabled(True)
        self.test_models_button.setEnabled(True)
        self.manage_predictors_button.setEnabled(True)
        self.insert_export_output_pane_contents_link()


class BatchTrainingSignalsHandler(ParallelWorkerSignals):
    """Handles the signals emitted during batch training when triggered from neanno's UI."""

    batch_training_started = pyqtSignal()
    batch_training_message = pyqtSignal(str, str)
    batch_training_image = pyqtSignal(bytes, str)
    batch_training_completed = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.started.connect(self.handle_started, type=Qt.DirectConnection)
        self.message.connect(self.handle_message, type=Qt.DirectConnection)
        self.image.connect(self.handle_image, type=Qt.DirectConnection)
        self.progress.connect(self.handle_progress, type=Qt.DirectConnection)
        self.completed.connect(self.handle_completed, type=Qt.DirectConnection)
        self.success.connect(self.handle_success, type=Qt.DirectConnection)
        self.failure.connect(self.handle_failure, type=Qt.DirectConnection)

        self.batch_training_started.connect(main_window.batch_training_started)
        self.batch_training_message.connect(main_window.batch_training_message)
        self.batch_training_image.connect(main_window.batch_training_image)
        self.batch_training_completed.connect(main_window.batch_training_completed)

    @pyqtSlot()
    def handle_started(self):
        self.batch_training_started.emit()

    @pyqtSlot(str, bool)
    def handle_message(self, message, end_with_newline):
        end = "\n" if end_with_newline == True else ""
        self.batch_training_message.emit(message, end)

    @pyqtSlot(bytes, str)
    def handle_image(self, image_bytes, image_format):
        self.batch_training_image.emit(image_bytes, image_format)

    @pyqtSlot(float)
    def handle_progress(self, percent_completed):
        pass

    @pyqtSlot()
    def handle_completed(self):
        self.batch_training_completed.emit()

    @pyqtSlot(object)
    def handle_success(self, result):
        self.batch_training_message.emit("Done.", "\n")

    @pyqtSlot(tuple)
    def handle_failure(self, exception_info):
        self.batch_training_message.emit("=> Failed to run a parallel job.", "\n")
        self.batch_training_message.emit(str(exception_info[0]), "\n")
        self.batch_training_message.emit(str(exception_info[1]), "\n")
        self.batch_training_message.emit(str(exception_info[2]), "\n")


class ModelValidationSignalsHandler(ParallelWorkerSignals):
    """Handles the signals emitted during model testing when triggered from neanno's UI."""

    model_testing_started = pyqtSignal()
    model_testing_message = pyqtSignal(str, str)
    model_testing_image = pyqtSignal(bytes, str)
    model_testing_completed = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.started.connect(self.handle_started, type=Qt.DirectConnection)
        self.message.connect(self.handle_message, type=Qt.DirectConnection)
        self.image.connect(self.handle_image, type=Qt.DirectConnection)
        self.progress.connect(self.handle_progress, type=Qt.DirectConnection)
        self.completed.connect(self.handle_completed, type=Qt.DirectConnection)
        self.success.connect(self.handle_success, type=Qt.DirectConnection)
        self.failure.connect(self.handle_failure, type=Qt.DirectConnection)

        self.model_testing_started.connect(main_window.model_testing_started)
        self.model_testing_message.connect(main_window.model_testing_message)
        self.model_testing_image.connect(main_window.model_testing_image)
        self.model_testing_completed.connect(main_window.model_testing_completed)

    @pyqtSlot()
    def handle_started(self):
        self.model_testing_started.emit()

    @pyqtSlot(str, bool)
    def handle_message(self, message, end_with_newline):
        end = "\n" if end_with_newline == True else ""
        self.model_testing_message.emit(message, end)

    @pyqtSlot(bytes, str)
    def handle_image(self, image_bytes, image_format):
        self.model_testing_image.emit(image_bytes, image_format)

    @pyqtSlot(float)
    def handle_progress(self, percent_completed):
        pass

    @pyqtSlot()
    def handle_completed(self):
        self.model_testing_completed.emit()

    @pyqtSlot(object)
    def handle_success(self, result):
        self.model_testing_message.emit("Done.", "\n")

    @pyqtSlot(tuple)
    def handle_failure(self, exception_info):
        self.model_testing_message.emit("=> Failed to run a parallel job.", "\n")
        self.model_testing_message.emit(str(exception_info[0]), "\n")
        self.model_testing_message.emit(str(exception_info[1]), "\n")
        self.model_testing_message.emit(str(exception_info[2]), "\n")
