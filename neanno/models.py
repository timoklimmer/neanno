import pandas as pd
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant, pyqtSignal


class _TextModel(QAbstractTableModel):
    saveStarted = pyqtSignal()
    saveCompleted = pyqtSignal()

    def __init__(
        self,
        pandas_data_frame,
        text_column_name,
        is_annotated_column_name,
        save_callback=None,
    ):
        super().__init__(parent=None)
        self._df = pandas_data_frame
        self.text_column_name = text_column_name
        self.is_annotated_column_name = is_annotated_column_name
        self.save_callback = save_callback

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
        # return text if index is on first column, otherwise is_annotated
        if index.column() == 0:
            return str(self._df.ix[index.row(), self.text_column_index])
        else:
            resultCandidate = self._df.ix[index.row(), self.is_annotated_column_index]
            return str(resultCandidate if resultCandidate is not None else False)

    def setData(self, index, value, role):
        row = index.row()
        col = index.column()
        # skip writing is_annotated
        if col != 0:
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

    def nextBestRowIndex(self):
        return self._df[self.is_annotated_column_name].idxmin()
