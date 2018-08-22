import pandas as pd
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant


class _TextModel(QAbstractTableModel):
    def __init__(
        self,
        pandas_data_frame,
        input_text_column_name,
        annotated_text_column_name,
        save_callback=None,
    ):
        super().__init__(parent=None)
        self._df = pandas_data_frame
        self.input_text_column_name = input_text_column_name
        self.annotated_text_column_name = annotated_text_column_name
        self.save_callback = save_callback

        # get column indexes and ensure that the data frame has an annotated text column
        self.text_column_index = self._df.columns.get_loc(input_text_column_name)
        if self.annotated_text_column_name not in self._df:
            self._df[self.annotated_text_column_name] = None
        self.annotated_text_column_index = self._df.columns.get_loc(
            self.annotated_text_column_name
        )

    def data(self, index, role=Qt.DisplayRole):
        # ensure index is valid
        if not index.isValid():
            return QVariant()
        # return annotated text if set, otherwise the original text
        resultCandidate = self._df.ix[index.row(), self.annotated_text_column_index]
        return (
            resultCandidate
            if resultCandidate is not None
            else self._df.ix[index.row(), self.text_column_index]
        )

    def setData(self, index, value, role):
        row = self._df.index[index.row()]
        col = self.annotated_text_column_index
        if self.data(index) != value or self._df.ix[index.row(), self.annotated_text_column_index] is None:      
            self._df.iat[row, col] = value
            self.save()
            self.dataChanged.emit(index, index)
        return True

    def rowCount(self, parent=QModelIndex()):
        return len(self._df.index)

    def columnCount(self, parent=QModelIndex()):
        return 1

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsEditable

    def save(self):
        if not self.save_callback is None:
            self.save_callback(self._df)

    def annotatedTextsCount(self):
        return self._df[self.annotated_text_column_name].notnull().sum()
