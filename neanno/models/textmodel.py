import math
import pathlib
import random
import re
import string
from collections import Counter
from functools import reduce

import config
import pandas as pd
import spacy
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant, pyqtSignal
from spacy.util import compounding, minibatch

from neanno.configuration.configmanager import ConfigManager
from neanno.utils.dict import mergesum_dict
from neanno.utils.text import (
    extract_annotations_for_spacy_ner,
    compute_categories_distribution_from_column,
    compute_named_entities_distribution_from_column,
    mask_annotations,
    unmask_annotations,
)


class TextModel(QAbstractTableModel):
    """Provides data to the annotation dialog / data widget mapper and triggers the saving of new annotated data."""

    random_categories_column_name = None
    named_entity_distribution = {}
    category_distribution = {}
    saveStarted = pyqtSignal()
    saveCompleted = pyqtSignal()
    spacy_model = None

    def __init__(self):
        super().__init__(parent=None)

        # get column indexes and ensure that the data frame has the required columns
        # text
        self.text_column_index = config.dataset_to_edit.columns.get_loc(
            config.text_column
        )
        # categories
        # note: if no category column is given, we will create a random column
        #       to make the code below easier but will drop the column before
        #       we save the dataframe
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

        # compute required distributions
        self.compute_categories_distribution()
        self.compute_named_entities_distribution()

        # load and prepare spacy model
        if config.is_spacy_enabled:
            self.spacy_model = self.load_and_prepare_spacy_model(
                config.spacy_model_source
            )

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

    def load_and_prepare_spacy_model(self, spacy_model_source):
        print("Loading spacy model...")
        return (
            spacy.blank(config.spacy_model_source.replace("blank:", "", 1))
            if config.spacy_model_source.startswith("blank:")
            else spacy.load(config.spacy_model_source)
        )

    def retrain_spacy_model(self):
        print("Training spacy model...")
        # ensure and get the ner pipe
        if "ner" not in self.spacy_model.pipe_names:
            self.spacy_model.add_pipe(self.spacy_model.create_pipe("ner"), last=True)
        ner = self.spacy_model.get_pipe("ner")
        # ensure we have all configured labels also configured in the model
        for named_entity_definition in config.named_entity_definitions:
            ner.add_label(named_entity_definition.code)
        # prepare the training set
        trainset = (
            config.dataset_to_edit[
                config.dataset_to_edit[config.is_annotated_column] == True
            ][config.text_column]
            .map(
                lambda text: extract_annotations_for_spacy_ner(
                    text,
                    ["standalone_named_entities"],
                    [
                        named_entity_definition.code
                        for named_entity_definition in config.named_entity_definitions
                    ],
                    list_aliases={"standalone_named_entities": "entities"},
                )
            )
            .tolist()
        )

        # do the training
        n_iter = 10
        optimizer = self.spacy_model.begin_training()
        other_pipes = [pipe for pipe in self.spacy_model.pipe_names if pipe != "ner"]
        with self.spacy_model.disable_pipes(*other_pipes):
            for itn in range(n_iter):
                random.shuffle(trainset)
                losses = {}
                batches = minibatch(trainset, size=compounding(4.0, 32.0, 1.001))
                for batch in batches:
                    texts, annotations = zip(*batch)
                    self.spacy_model.update(
                        texts, annotations, sgd=optimizer, drop=0.35, losses=losses
                    )
                print("Iteration: {}, losses: {}".format(itn, losses))

        # test the trained model
        # TODO: complete, precision/recall statistics
        # test_text = "Guten Morgen, bei uns gibt es heute Bifteki mit Schafkäsesoße, dazu Reis und Salat. Schönen Freitag,"
        # doc = self.spacy_model(test_text)
        # print("Entities in '%s'" % test_text)
        # for ent in doc.ents:
        #    print(ent.label_, ent.text)

        # save model to output directory
        if config.spacy_model_target is not None:
            output_dir = pathlib.Path(config.spacy_model_target)
            if not output_dir.exists():
                output_dir.mkdir()
            self.spacy_model.meta["name"] = config.spacy_model_target
            self.spacy_model.to_disk(output_dir)
            print(
                "Retraining completed. Saved model to folder '{}'.".format(output_dir)
            )
        else:
            print("Retraining completed.")

    def data(self, index, role=Qt.DisplayRole):
        # ensure index is valid
        if not index.isValid():
            return QVariant()

        # get is_annotated
        is_annotated = config.dataset_to_edit.ix[
            index.row(), self.is_annotated_column_index
        ]

        # return data for respective columns
        # column 0: text
        if index.column() == 0:
            result = str(config.dataset_to_edit.ix[index.row(), self.text_column_index])
            # mask annotations to avoid that we get nested annotations
            # note: the masking has to be repeated at several places below to avoid double nested annotations
            result = mask_annotations(result)
            # add predicted and/or suggested entities if needed
            if not is_annotated and config.is_named_entities_enabled:
                # note: all transformation below have to ensure that their annotations are masked
                #       to ensure that there are no double annotations
                # entity predictions from spacy
                # TODO: might change in future
                if config.is_spacy_enabled:
                    doc = self.spacy_model(result)
                    shift = 0
                    for ent in doc.ents:
                        old_result_length = len(result)
                        result = "{}{}{}".format(
                            result[: ent.start_char + shift],
                            "`{}``SN``{}`´".format(ent.text, ent.label_),
                            result[ent.end_char + shift :],
                        )
                        shift += len(result) - old_result_length
                    result = mask_annotations(result)

                # autosuggester annotations
                result = config.autosuggester.suggest(result)
                result = mask_annotations(result)

            # return unmask masked annotations
            return unmask_annotations(result)

        # column 1: is_annotated
        if index.column() == 1:
            return str(is_annotated if is_annotated is not None else False)
        # column 2: categories
        if index.column() == 2:
            return str(
                config.dataset_to_edit.ix[index.row(), self.categories_column_index]
            )

    def setData(self, index, value, role):
        row = index.row()
        col = index.column()
        # skip writing is_annotated
        if col == 1:
            return True
        # update dataset and save if needed
        if (
            self.data(index) != value
            or not config.dataset_to_edit.ix[row, self.is_annotated_column_index]
        ):
            config.dataset_to_edit.iat[row, self.is_annotated_column_index] = True
            if index.column() == 0:
                # text
                # update text
                config.dataset_to_edit.iat[row, self.text_column_index] = value
                # update autosuggest key terms collection
                config.autosuggester.update_key_terms_dataset(value)
                # re-compute distributions
                # TODO: might be made more efficient with deltas instead of complete recomputation all the time
                self.compute_named_entities_distribution()
            if index.column() == 2:
                # categories
                config.dataset_to_edit.iat[row, self.categories_column_index] = value
                self.compute_categories_distribution()
            self.save()
            self.dataChanged.emit(index, index)
        return True

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if section == 0:
            return config.text_column
        if section == 1:
            return config.is_annotated_column
        if section == 2:
            return config.categories_column
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(config.dataset_to_edit.index)

    def columnCount(self, parent=QModelIndex()):
        return 3

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsEditable

    def save(self):
        if config.save_callback is not None:
            self.saveStarted.emit()
            config.save_callback(
                config.dataset_to_edit
                if not self.random_categories_column_name
                else config.dataset_to_edit.drop(
                    [self.random_categories_column_name], axis=1
                )
            )
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
        config.dataset_to_edit.ix[row_index, self.is_annotated_column_index] = False

    def reset_is_annotated_flags(self):
        config.dataset_to_edit[config.is_annotated_column] = False
