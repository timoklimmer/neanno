import math
import random
import re
import string

import config
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant, pyqtSignal

from neanno.utils.text import (
    compute_categories_distribution_from_column,
    compute_named_entities_distribution_from_column,
)

from sklearn.model_selection import train_test_split


class TextModel(QAbstractTableModel):
    """Provides data to the main dialog (data widget mapper) and triggers the saving of new annotated data."""

    random_language_column_name = None
    random_categories_column_name = None
    named_entity_distribution = {}
    category_distribution = {}
    saveStarted = pyqtSignal()
    saveCompleted = pyqtSignal()
    trainset = None
    validationset = None

    def __init__(self):
        super().__init__(parent=None)

        # get column indexes and ensure that the data frame has the required columns
        # text
        self.text_column_index = config.dataset_to_edit.columns.get_loc(
            config.text_column
        )
        # language
        # note: if the dataset does not use languages, we will use our own language
        #       column and default language but will remove the column before save
        if not config.uses_languages:
            self.random_language_column_name = "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(16)
            )
            config.language_column = self.random_language_column_name
        if config.language_column not in config.dataset_to_edit:
            config.dataset_to_edit[config.language_column] = ""
        config.dataset_to_edit[config.language_column] = config.dataset_to_edit[
            config.language_column
        ].astype(str)
        self.language_column_index = config.dataset_to_edit.columns.get_loc(
            config.language_column
        )
        # categories
        # note: same as language, we internally create the column if needed but
        #       will drop it before save if none is specified
        if not config.is_categories_enabled:
            self.random_categories_column_name = "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(16)
            )
            config.categories_column = self.random_categories_column_name
        if config.categories_column not in config.dataset_to_edit:
            config.dataset_to_edit[config.categories_column] = ""
        config.dataset_to_edit[config.categories_column] = config.dataset_to_edit[
            config.categories_column
        ].astype(str)
        self.categories_column_index = config.dataset_to_edit.columns.get_loc(
            config.categories_column
        )
        # is annotated
        if config.is_annotated_column not in config.dataset_to_edit:
            config.dataset_to_edit[config.is_annotated_column] = False
        self.is_annotated_column_index = config.dataset_to_edit.columns.get_loc(
            config.is_annotated_column
        )

        # compute distributions
        self.recompute_distributions()

    def compute_named_entities_distribution(self):
        if config.is_named_entities_enabled:
            self.named_entity_distribution = compute_named_entities_distribution_from_column(
                self.get_annotated_data()[config.text_column]
            )

    def compute_categories_distribution(self):
        if config.is_categories_enabled:
            self.category_distribution = compute_categories_distribution_from_column(
                self.get_annotated_data()[config.categories_column]
            )

    def get_annotated_data(self):
        return config.dataset_to_edit[
            config.dataset_to_edit[config.is_annotated_column] == True
        ]

    def data(self, index, role=Qt.DisplayRole):
        # ensure index is valid
        if not index.isValid():
            return QVariant()

        # get is_annotated
        is_annotated = config.dataset_to_edit.iloc[
            index.row(), self.is_annotated_column_index
        ]

        # return data for respective columns
        # column 0: language
        if index.column() == 0:
            language_candidate = str(
                config.dataset_to_edit.iloc[index.row(), self.language_column_index]
            )
            if language_candidate:
                return language_candidate
            else:
                return config.default_language
        # column 1: text
        if index.column() == 1:
            # get text from dataset
            result = str(
                config.dataset_to_edit.iloc[index.row(), self.text_column_index]
            )
            # add predicted/suggested annotations if not annotated yet
            if not is_annotated:
                language = self.data(index.siblingAtColumn(0))
                result = config.prediction_pipeline.predict_inline_annotations(
                    result, language
                )
            # return result
            return result
        # column 2: categories
        if index.column() == 2:
            categories_value_in_dataset = str(
                config.dataset_to_edit.iloc[index.row(), self.categories_column_index]
            )
            if not categories_value_in_dataset:
                # predicted categories if not annotated yet
                language = self.data(index.siblingAtColumn(0))
                return "|".join(
                    config.prediction_pipeline.predict_text_categories(
                        str(
                            config.dataset_to_edit.iloc[
                                index.row(), self.text_column_index
                            ]
                        ),
                        language,
                    )
                )
            else:
                # categories given by annotation
                return categories_value_in_dataset
        # column 3: is_annotated
        if index.column() == 3:
            return str(is_annotated if is_annotated is not None else False)

    def setData(self, index, value, role):
        row = index.row()
        col = index.column()

        # update the corresponding cell in the dataset
        # language
        if index.column() == 0:
            config.dataset_to_edit.iat[row, self.language_column_index] = value
        # text
        if index.column() == 1:
            config.dataset_to_edit.iat[row, self.text_column_index] = value
            language = self.data(index.siblingAtColumn(0))
            config.prediction_pipeline.train_from_annotated_text(value, language)
        # categories
        if index.column() == 2:
            config.dataset_to_edit.iat[row, self.categories_column_index] = value

        # set is annotated flag to true
        config.dataset_to_edit.iat[row, self.is_annotated_column_index] = True

        # re-compute distributions
        if index.column() == 1:
            self.compute_named_entities_distribution()
        if index.column() == 2:
            self.compute_categories_distribution()

        # save the dataset and emit a dataChanged signal
        if index.column() == 3:
            self.save()
            self.dataChanged.emit(index, index)

        # return true
        return True

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if section == 0:
            return config.language_column
        if section == 1:
            return config.text_column
        if section == 2:
            return config.categories_column
        if section == 3:
            return config.is_annotated_column
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(config.dataset_to_edit.index)

    def columnCount(self, parent=QModelIndex()):
        return 4

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsEditable

    def save(self):
        if config.save_callback is not None:
            self.saveStarted.emit()
            df_to_save = config.dataset_to_edit
            if self.random_language_column_name:
                df_to_save = df_to_save.drop(columns=[self.random_language_column_name])
            if self.random_categories_column_name:
                df_to_save = df_to_save.drop(
                    columns=[self.random_categories_column_name]
                )
            config.save_callback(df_to_save)
            self.saveCompleted.emit()

    def get_annotated_texts_count(self):
        return config.dataset_to_edit[config.is_annotated_column].sum()

    def get_next_row_index(self, current_index):
        return (current_index + 1) % self.rowCount()

    def get_next_best_row_index(self, current_index):
        if self.is_texts_left_for_annotation():
            # return the next text which is not annotated yet
            return config.dataset_to_edit[config.is_annotated_column].idxmin()
        else:
            # there is no text that is not annotated yet
            # fallback to just the next index
            return self.get_next_row_index(current_index)

    def get_index_of_next_text_which_contains_substring(self, substring, current_index):
        is_regex = True if substring.startswith("regex:") else False
        if is_regex:
            substring = re.sub(r"^regex:", "", substring)
        result = config.dataset_to_edit[
            (config.dataset_to_edit.index > current_index)
            & config.dataset_to_edit[config.text_column].str.contains(
                substring, regex=is_regex
            )
        ].index.min()
        if math.isnan(result):
            result = config.dataset_to_edit[
                (config.dataset_to_edit.index < current_index)
                & config.dataset_to_edit[config.text_column].str.contains(
                    substring, regex=is_regex
                )
            ].index.min()
        if math.isnan(result):
            result = None
        return result

    def is_texts_left_for_annotation(self):
        return False in config.dataset_to_edit[config.is_annotated_column].values

    def unset_is_annotated_for_index(self, row_index):
        config.dataset_to_edit.iloc[row_index, self.is_annotated_column_index] = False

    def reset_is_annotated_flags(self):
        config.dataset_to_edit[config.is_annotated_column] = False
        self.recompute_distributions()
        self.save()

    def mark_all_texts_as_annotated(self):
        config.dataset_to_edit[config.is_annotated_column] = True
        self.recompute_distributions()
        self.save()

    def recompute_distributions(self):
        self.compute_categories_distribution()
        self.compute_named_entities_distribution()

    def get_trainset(self, test_size=0.25):
        annotated_data = self.get_annotated_data()
        self.trainset, self.validationset = train_test_split(
            annotated_data, test_size=test_size
        )
        return self.trainset

    def get_validationset(self):
        return self.validationset
