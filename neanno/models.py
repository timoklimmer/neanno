import pandas as pd
import spacy
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant, pyqtSignal


class _TextModel(QAbstractTableModel):
    saveStarted = pyqtSignal()
    saveCompleted = pyqtSignal()
    ner_model_spacy = None

    def __init__(
        self,
        pandas_data_frame,
        text_column_name,
        is_annotated_column_name,
        named_entity_definitions,
        save_callback=None,
        ner_model_source_spacy=None,
        ner_model_target_spacy=None,
        dataset_source_friendly=None,
        dataset_target_friendly=None,
    ):
        super().__init__(parent=None)
        self._df = pandas_data_frame
        self.text_column_name = text_column_name
        self.is_annotated_column_name = is_annotated_column_name
        self.named_entity_definitions = named_entity_definitions
        self.save_callback = save_callback
        self.ner_model_source_spacy = ner_model_source_spacy
        self.ner_model_target_spacy = ner_model_target_spacy
        self.dataset_source_friendly = dataset_source_friendly
        self.dataset_target_friendly = dataset_target_friendly

        # load and prepare spacy model
        if self.ner_model_source_spacy is not None:
            # we have an existing model
            # load model
            self.ner_model_spacy = spacy.load(self.ner_model_source_spacy)
            # ensure we have a ner pipe
            if "ner" not in self.ner_model_spacy.pipe_names:
                ner = self.ner_model_spacy.create_pipe("ner")
                self.ner_model_spacy.add_pipe(ner, last=True)
            else:
                ner = self.ner_model_spacy.get_pipe("ner")
            # ensure we have all configured labels also configured in the model
            for named_entity_definition in self.named_entity_definitions:
                ner.add_label(named_entity_definition.code)
            # TODO: remove all other labels

        # get column indexes and ensure that the data frame has an is annotated column
        self.text_column_index = self._df.columns.get_loc(text_column_name)
        if self.is_annotated_column_name not in self._df:
            self._df[self.is_annotated_column_name] = False
        self.is_annotated_column_index = self._df.columns.get_loc(
            self.is_annotated_column_name
        )

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
            if self.ner_model_spacy is not None and is_annotated == "False":
                doc = self.ner_model_spacy(result)
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
        if False in self._df[self.is_annotated_column_name].values:
            # return the next text which is not annotated
            return self._df[self.is_annotated_column_name].idxmin()
        else:
            # there is no text that is not annotated yet
            return -1
            #return (currentIndex + 1) % self.rowCount()

    def hasDatasetMetadata(self):
        return (
            self.dataset_source_friendly is not None
            or self.dataset_target_friendly is not None
        )

    def hasNerModelMetadata(self):
        return (
            self.ner_model_source_spacy is not None
            or self.ner_model_target_spacy is not None
        )
