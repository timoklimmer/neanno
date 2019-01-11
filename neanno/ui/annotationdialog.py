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

from neanno.ui.about import show_about_dialog
from neanno.configuration.configmanager import ConfigManager
from neanno.ui.categoriesselector import CategoriesSelectorWidget
from neanno.ui.navigator import TextNavigator
from neanno.ui.shortcuts import *
from neanno.ui.syntaxhighlighters import TextEditHighlighter
from neanno.utils.text import *


class AnnotationDialog(QMainWindow):
    """ The dialog shown to the user to do the annotation/labeling."""

    def __init__(self, textmodel):
        print("Showing annotation dialog...")
        app = QApplication([])
        super().__init__()
        self.setWindowIcon(self.get_icon("icon.ico"))
        self.textmodel = textmodel
        self.layout_controls()
        self.setup_and_wire_navigator_incl_buttons()
        self.setup_and_wire_shortcuts()
        self.show()
        app.exec_()

    @staticmethod
    def get_icon(file):
        return QIcon(
            os.path.join(
                os.path.abspath(os.path.dirname(__file__)), "../resources/{}".format(file)
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
        self.textedit = QPlainTextEdit()
        self.textedit.setStyleSheet(
            "font-size: 14pt; font-family: Consolas; color: lightgrey; background-color: black"
        )
        self.textedit_highlighter = TextEditHighlighter(
            self.textedit.document(), config.named_entity_definitions
        )
        self.textedit.textChanged.connect(self.textedit_text_changed)

        # annotation monitor
        self.annotation_monitor = QPlainTextEdit()
        self.annotation_monitor.setReadOnly(True)
        self.annotation_monitor.setStyleSheet(
            "font-size: 14pt; font-family: Consolas; color: lightgrey; background-color: black"
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
        close_button.setToolTip("Close")
        close_button.clicked.connect(self.close)

        # remaining layouts
        # left panel
        left_panel_layout = QVBoxLayout()
        left_panel_layout_splitter = QSplitter(Qt.Vertical)
        left_panel_layout_splitter.addWidget(self.textedit)
        left_panel_layout_splitter.addWidget(self.annotation_monitor)
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
            register_shortcut(
                self, named_entity_definition.key_sequence, self.annotate_entity
            )
        # submit next
        register_shortcut(
            self, SHORTCUT_SUBMIT_NEXT, self.submit_and_go_to_next
        )
        # submit next best
        register_shortcut(
            self, SHORTCUT_SUBMIT_NEXT_BEST, self.submit_and_go_to_next_best
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
        # remove/reset shortcuts
        register_shortcut(
            self, SHORTCUT_REMOVE_ANNOTATION_AT_CURSOR, self.remove_annotation
        )
        register_shortcut(
            self, SHORTCUT_REMOVE_ALL_FOR_CURRENT_TEXT, self.remove_all_annotations
        )
        register_shortcut(
            self, SHORTCUT_RESET_IS_ANNOTATED_FLAG, self.reset_is_annotated_flag
        )
        register_shortcut(
            self,
            SHORTCUT_RESET_ALL_IS_ANNOTATED_FLAGS,
            self.reset_all_is_annotated_flags,
        )

    def setup_and_wire_navigator_incl_buttons(self):
        self.navigator = TextNavigator(self)
        self.navigator.setSubmitPolicy(QDataWidgetMapper.ManualSubmit)
        self.navigator.setModel(self.textmodel)
        self.navigator.addMapping(self.textedit, 0)
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
        self.search_button.clicked.connect(self.search)
        self.submit_next_best_button.clicked.connect(self.submit_and_go_to_next_best)

    def update_navigation_related_controls(self):
        # current index
        self.current_text_index_label.setText(str(self.navigator.currentIndex()))
        # remove focus from controls
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

    def textedit_text_changed(self):
        self.sync_parented_annotations()
        self.update_annotation_monitor()

    def sync_parented_annotations(self):
        # get annotation at current cursor position
        annotation_at_current_cursor_pos = get_annotation_at_position(
            self.textedit.toPlainText(), self.textedit.textCursor().position()
        )
        # update annotation for same parented keyterm
        if (
            annotation_at_current_cursor_pos is not None
            and annotation_at_current_cursor_pos["term_type_long"] == "parented_keyterm"
        ):
            text_to_replace_pattern = r"´\<`{}´\|`PK .*?´\>`".format(
                re.escape(annotation_at_current_cursor_pos["term"])
            )
            replace_against_text = "´<`{}´|`PK {}´>`".format(
                annotation_at_current_cursor_pos["term"],
                annotation_at_current_cursor_pos["parent_terms"],
            )
            self.replace_pattern_in_textedit(
                text_to_replace_pattern, replace_against_text
            )

    def update_annotation_monitor(self):
        self.annotation_monitor.setPlainText(
            extract_annotations_as_text(
                self.textedit.toPlainText(),
                # remove comment to include categories too
                ##self.categories_selector.get_selected_categories(),
                [],
                True,
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
            # TODO: only match if not part of another annotation
            text_to_replace_pattern = r"(?<!´\<`){}(?!´\|`SK´\>`)".format(
                re.escape(text_to_replace)
            )
            replace_against_text = "´<`{}´|`SK´>`".format(
                remove_all_annotations_from_text(text_to_replace)
            )
            self.replace_pattern_in_textedit(
                text_to_replace_pattern, replace_against_text
            )

    def annotate_parented_key_term(self):
        text_cursor = self.textedit.textCursor()
        if text_cursor.hasSelection():
            text_to_replace = text_cursor.selectedText()
            # TODO: only match if not part of another annotation
            text_to_replace_pattern = r"(?<!´\<`){}(?!´\|`PK .*?´\>`)".format(
                re.escape(text_to_replace)
            )
            default_parent_key_term = (
                "<add your consolidating terms here, separated by commas>"
            )
            orig_selection_start = text_cursor.selectionStart()
            new_selection_start = orig_selection_start + len(
                "´<`{}´|`PK ".format(remove_all_annotations_from_text(text_to_replace))
            )
            new_selection_end = new_selection_start + len(default_parent_key_term)
            replace_against_text = "´<`{}´|`PK {}´>`".format(
                remove_all_annotations_from_text(text_to_replace),
                default_parent_key_term,
            )
            self.replace_pattern_in_textedit(
                text_to_replace_pattern, replace_against_text
            )
            text_cursor.setPosition(new_selection_start)
            text_cursor.setPosition(new_selection_end, QTextCursor.KeepAnchor)
            self.textedit.setTextCursor(text_cursor)

    def annotate_entity(self):
        text_cursor = self.textedit.textCursor()
        if text_cursor.hasSelection():
            # change text
            key_sequence = self.sender().key().toString()
            selected_text = text_cursor.selectedText()
            code = ""
            for named_entity_definition in config.named_entity_definitions:
                if named_entity_definition.key_sequence == key_sequence:
                    code = named_entity_definition.code
                    break
            text_cursor.insertText(
                "´<`{}´|`SN {}´>`".format(
                    remove_all_annotations_from_text(selected_text), code
                )
            )

    def remove_annotation(self):
        annotation = get_annotation_at_position(
            self.textedit.toPlainText(), self.textedit.textCursor().position()
        )
        # ensure there is an annotation to remove
        if annotation is not None:
            # get the replace pattern and replace against text
            if annotation["term_type_long"] == "standalone_keyterm":
                text_to_replace_pattern = r"´\<`{}´\|`(SK|PK).*?´\>`".format(
                    annotation["term"]
                )
            if annotation["term_type_long"] == "parented_keyterm":
                text_to_replace_pattern = r"´\<`{}´\|`(SK|PK).*?´\>`".format(
                    annotation["term"]
                )
            if annotation["term_type_long"] == "standalone_named_entity":
                text_to_replace_pattern = r"´\<`{}´\|`SN {}?´\>`".format(
                    annotation["term"], annotation["entity_name"]
                )
            replace_against_text = annotation["term"]
            # do the replace
            self.replace_pattern_in_textedit(
                text_to_replace_pattern, replace_against_text
            )
            # mark key term for removal from autosuggest collection (if it is a key term and not a named entity)
            if annotation["term_type_long"] in [
                "standalone_keyterm",
                "parented_keyterm",
            ]:
                ConfigManager.mark_key_term_for_removal_from_autosuggest_collection(
                    annotation["term"]
                )

    def remove_all_annotations(self):
        # mark all key terms for removal
        for annotation in extract_annotations_as_list(
            self.textedit.toPlainText(),
            term_types_to_extract=["standalone_keyterm", "parented_keyterm"],
        ):
            ConfigManager.mark_key_term_for_removal_from_autosuggest_collection(
                annotation["term"]
            )
        # update text
        self.textedit.setPlainText(
            remove_all_annotations_from_text(self.textedit.toPlainText())
        )

        # clear categories if categories are
        if config.is_categories_enabled:
            self.categories_selector.set_selected_categories_by_text("")

        # reset is annotated flag
        self.reset_is_annotated_flag()

    def reset_is_annotated_flag(self):
        self.textmodel.unset_is_annotated_for_index(self.navigator.getCurrentIndex())
        self.is_annotated_label.setText("False")

    def reset_all_is_annotated_flags(self):
        if (
            QMessageBox.question(
                self,
                "Confirmation",
                "This will reset all Is Annotated flags and save the dataset to its target. You may end up in big trouble if you don't know what you are doing.\n\nAre you sure you want to the reset/save?",
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            self.textmodel.reset_is_annotated_flags()
            self.is_annotated_label.setText("False")
            self.textmodel.save()
            self.navigator.toFirst()

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

    def retrain_model(self):
        self.textmodel.retrain_spacy_model()

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
