import pathlib
import random
import re
import string

import spacy
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant, pyqtSignal
from spacy.util import compounding, minibatch

import config


class TextModel(QAbstractTableModel):
    random_categories_column_name = None
    saveStarted = pyqtSignal()
    saveCompleted = pyqtSignal()
    spacy_model = None

    def __init__(self):
        super().__init__(parent=None)
        config.dataframe_to_edit = config.dataframe_to_edit

        # get column indexes and ensure that the data frame has the required columns
        # text
        self.text_column_index = config.dataframe_to_edit.columns.get_loc(config.text_column)
        # categories
        # note: if no category column is given, we will create a random column
        #       to make the code below easier but will drop the column before
        #       we save the dataframe
        if not config.categories_column:
            self.random_categories_column_name = "".join(
                random.choice(string.ascii_uppercase + string.digits) for _ in range(16)
            )
            config.categories_column = self.random_categories_column_name
        if config.categories_column not in config.dataframe_to_edit:
            config.dataframe_to_edit[config.categories_column] = ""
        self.categories_column_index = config.dataframe_to_edit.columns.get_loc(
            config.categories_column
        )
        # is annotated
        if config.is_annotated_column not in config.dataframe_to_edit:
            config.dataframe_to_edit[config.is_annotated_column] = False
        self.is_annotated_column_index = config.dataframe_to_edit.columns.get_loc(
            config.is_annotated_column
        )

        # load and prepare spacy model
        if self.has_spacy_model():
            self.spacy_model = self.load_and_prepare_spacy_model(
                config.spacy_model_source
            )

    def load_and_prepare_spacy_model(self, spacy_model_source):
        print("Loading spacy model...")
        return (
            spacy.blank(spacy_model_source.replace("blank:", "", 1))
            if spacy_model_source.startswith("blank:")
            else spacy.load(self.spacy_model_source)
        )

    @staticmethod
    def extract_entities_from_nerded_text(text):
        # TODO: check if label is actually a configured label
        result = (re.sub("\((?P<text>.+?)\| .+?\)", "\g<text>", text), {"entities": []})
        working_text = text
        while True:
            match = re.search("\((?P<text>.+?)\| (?P<label>.+?)\)", working_text)
            if match is not None:
                entity_text = match.group(1)
                entity_label = match.group(2)
                result[1]["entities"].append(
                    (match.start(1) - 1, match.end(1) - 1, entity_label)
                )
                working_text = re.sub("\(.+?\| .+?\)", entity_text, working_text, 1)
            else:
                break
        return result

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
            config.dataframe_to_edit[config.dataframe_to_edit[config.is_annotated_column] == True][
                config.text_column
            ]
            .map(lambda text: self.extract_entities_from_nerded_text(text))
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
            print("Retraining completed. Saved model to folder '{}'".format(output_dir))
        else:
            print("Retraining completed.")

    def data(self, index, role=Qt.DisplayRole):
        # ensure index is valid
        if not index.isValid():
            return QVariant()

        # get is_annotated
        is_annotated = config.dataframe_to_edit.ix[index.row(), self.is_annotated_column_index]
        is_annotated = str(is_annotated if is_annotated is not None else False)

        # return data for respective columns
        # column 0: text
        if index.column() == 0:
            result = str(config.dataframe_to_edit.ix[index.row(), self.text_column_index])
            # add predicted entities if needed
            if (
                not is_annotated
                and self.has_named_entities()
                and self.has_spacy_model()
            ):
                doc = self.spacy_model(result)
                shift = 0
                for ent in doc.ents:
                    old_result_length = len(result)
                    result = "{}{}{}".format(
                        result[: ent.start_char + shift],
                        "({}| {})".format(ent.text, ent.label_),
                        result[ent.end_char + shift :],
                    )
                    shift += len(result) - old_result_length
            return result
        # column 1: is_annotated
        if index.column() == 1:
            return is_annotated
        # column 2: categories
        if index.column() == 2:
            return str(config.dataframe_to_edit.ix[index.row(), self.categories_column_index])

    def setData(self, index, value, role):
        row = index.row()
        col = index.column()
        # skip writing is_annotated
        if col == 1:
            return True
        # update _df and save if needed
        if (
            self.data(index) != value
            or not config.dataframe_to_edit.ix[row, self.is_annotated_column_index]
        ):
            if index.column() == 0:
                # text
                config.dataframe_to_edit.iat[row, self.text_column_index] = value
            if index.column() == 2:
                # categories
                config.dataframe_to_edit.iat[row, self.categories_column_index] = value
            config.dataframe_to_edit.iat[row, self.is_annotated_column_index] = True
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
        return len(config.dataframe_to_edit.index)

    def columnCount(self, parent=QModelIndex()):
        return 3

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsEditable

    def save(self):
        if config.save_callback is not None:
            self.saveStarted.emit()
            config.save_callback(
                config.dataframe_to_edit
                if not self.random_categories_column_name
                else config.dataframe_to_edit.drop([self.random_categories_column_name], axis=1)
            )
            self.saveCompleted.emit()

    def get_annotated_texts_count(self):
        return config.dataframe_to_edit[config.is_annotated_column].sum()

    def get_next_best_row_index(self, current_index):
        if self.is_texts_left_for_annotation():
            # return the next text which is not annotated yet
            return config.dataframe_to_edit[config.is_annotated_column].idxmin()
        else:
            # there is no text that is not annotated yet
            # return the next text (might start at the beginning if end of available texts is reads)
            return (current_index + 1) % self.rowCount()

    def is_texts_left_for_annotation(self):
        return False in config.dataframe_to_edit[config.is_annotated_column].values

    def has_spacy_model(self):
        return bool(config.spacy_model_source)

    def has_named_entities(self):
        return bool(config.named_entity_definitions)

    def has_categories(self):
        return bool(config.categories_column) and len(
            config.category_definitions
        )

