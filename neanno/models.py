import pathlib
import random
import re

import pandas as pd
import spacy
from PyQt5.QtCore import (QAbstractTableModel, QModelIndex, Qt, QVariant,
                          pyqtSignal)
from spacy.util import compounding, minibatch


class TextModel(QAbstractTableModel):
    saveStarted = pyqtSignal()
    saveCompleted = pyqtSignal()
    ner_model = None

    def __init__(
        self,
        pandas_data_frame,
        text_column_name,
        is_annotated_column_name,
        named_entity_definitions,
        save_callback=None,
        ner_model_source=None,
        ner_model_target=None,
        dataset_source_friendly=None,
        dataset_target_friendly=None,
    ):
        super().__init__(parent=None)
        self._df = pandas_data_frame
        self.text_column_name = text_column_name
        self.is_annotated_column_name = is_annotated_column_name
        self.named_entity_definitions = named_entity_definitions
        self.save_callback = save_callback
        self.ner_model_source = ner_model_source
        self.ner_model_target = ner_model_target
        self.dataset_source_friendly = dataset_source_friendly
        self.dataset_target_friendly = dataset_target_friendly

        # load and prepare ner model
        if self.ner_model_source is not None:
            self.ner_model = self.load_and_prepare_ner_model(self.ner_model_source)

        # get column indexes and ensure that the data frame has an is annotated column
        self.text_column_index = self._df.columns.get_loc(text_column_name)
        if self.is_annotated_column_name not in self._df:
            self._df[self.is_annotated_column_name] = False
        self.is_annotated_column_index = self._df.columns.get_loc(
            self.is_annotated_column_name
        )

    def load_and_prepare_ner_model(self, ner_model_source):
        # load model
        if ner_model_source.startswith("blank:"):
            result = spacy.blank(ner_model_source.replace("blank:", "", 1))
        else:
            result = spacy.load(self.ner_model_source)
        return result

    def extract_entities_from_nerded_text(self, text):
        # TODO: check if label is actually a configured label
        result = (re.sub("\((?P<text>.+?)\| .+?\)", "\g<text>", text), {"entities": []})
        workingText = text
        while True:
            match = re.search("\((?P<text>.+?)\| (?P<label>.+?)\)", workingText)
            if match is not None:
                entity_text = match.group(1)
                entity_label = match.group(2)
                result[1]["entities"].append(
                    (match.start(1) - 1, match.end(1) - 1, entity_label)
                )
                workingText = re.sub("\(.+?\| .+?\)", entity_text, workingText, 1)
            else:
                break
        return result

    def retrain_ner_model(self):
        print("Training NER model...")
        # ensure and get the ner pipe
        if "ner" not in self.ner_model.pipe_names:
            self.ner_model.add_pipe(self.ner_model.create_pipe("ner"), last=True)
        ner = self.ner_model.get_pipe("ner")
        # ensure we have all configured labels also configured in the model
        for named_entity_definition in self.named_entity_definitions:
            ner.add_label(named_entity_definition.code)
        # prepare the training set
        trainset = (
            self._df[self._df[self.is_annotated_column_name] == True][
                self.text_column_name
            ]
            .map(lambda text: self.extract_entities_from_nerded_text(text))
            .tolist()
        )
        # do the training
        n_iter = 25
        optimizer = self.ner_model.begin_training()
        other_pipes = [pipe for pipe in self.ner_model.pipe_names if pipe != "ner"]
        with self.ner_model.disable_pipes(*other_pipes):
            for itn in range(n_iter):
                random.shuffle(trainset)
                losses = {}
                batches = minibatch(trainset, size=compounding(4.0, 32.0, 1.001))
                for batch in batches:
                    texts, annotations = zip(*batch)
                    self.ner_model.update(
                        texts, annotations, sgd=optimizer, drop=0.35, losses=losses
                    )
                print("Losses", losses)

        # test the trained model
        # TODO: complete, precision/recall statistics
        test_text = "Guten Morgen, bei uns gibt es heute Bifteki mit Schafkäsesoße, dazu Reis und Salat. Schönen Freitag,"
        doc = self.ner_model(test_text)
        print("Entities in '%s'" % test_text)
        for ent in doc.ents:
            print(ent.label_, ent.text)

        # save model to output directory
        if self.ner_model_target is not None:
            output_dir = pathlib.Path(self.ner_model_target)
            if not output_dir.exists():
                output_dir.mkdir()
            self.ner_model.meta['name'] = self.ner_model_target
            self.ner_model.to_disk(output_dir)
            print("Retraining completed. Saved model to folder '{}'".format(output_dir))
        else:
            print("Retraining completed.")

    def data(self, index, role=Qt.DisplayRole):
        # ensure index is valid
        if not index.isValid():
            return QVariant()
        # get is_annotated
        is_annotated = self._df.ix[index.row(), self.is_annotated_column_index]
        is_annotated = str(is_annotated if is_annotated is not None else False)

        # column 0: text
        if index.column() == 0:
            result = str(self._df.ix[index.row(), self.text_column_index])
            # add predicted entities if we have a model and no confirmed annotation yet
            if self.ner_model is not None and is_annotated == "False":
                doc = self.ner_model(result)
                shift = 0
                for ent in doc.ents:
                    oldResultLength = len(result)
                    result = "{}{}{}".format(
                        result[: ent.start_char + shift],
                        "({}| {})".format(ent.text, ent.label_),
                        result[ent.end_char + shift :],
                    )
                    shift += len(result) - oldResultLength
            return result
        # column 1: is_annotated
        if index.column() == 1:
            return is_annotated

    def setData(self, index, value, role):
        row = index.row()
        col = index.column()
        # skip writing is_annotated
        if col == 1:
            return True
        # update _df and save if needed
        if (
            self.data(index) != value
            or self._df.ix[row, self.is_annotated_column_index] == False
        ):
            self._df.iat[row, self.text_column_index] = value
            self._df.iat[row, self.is_annotated_column_index] = True
            self.save()
            self.dataChanged.emit(index, index)
        return True

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if section == 0:
            return self.text_column_name
        if section == 1:
            return self.is_annotated_column_name
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(self._df.index)

    def columnCount(self, parent=QModelIndex()):
        return 2

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsEditable

    def save(self):
        if not self.save_callback is None:
            self.saveStarted.emit()
            self.save_callback(self._df)
            self.saveCompleted.emit()

    def annotatedTextsCount(self):
        return (self._df[self.is_annotated_column_name] == True).sum()

    def nextBestRowIndex(self, currentIndex):
        if self.isTextToAnnotateLeft():
            # return the next text which is not annotated yet
            return self._df[self.is_annotated_column_name].idxmin()
        else:
            # there is no text that is not annotated yet
            # return the next text (might start at the beginning if end of available texts is reads)
            return (currentIndex + 1) % self.rowCount()

    def isTextToAnnotateLeft(self):
        return (False in self._df[self.is_annotated_column_name].values)

    def hasDatasetMetadata(self):
        return (
            self.dataset_source_friendly is not None
            or self.dataset_target_friendly is not None
        )

    def hasNerModel(self):
        return self.ner_model_source is not None or self.ner_model_target is not None
