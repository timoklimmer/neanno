import pandas as pd
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, QVariant


class _TextModel(QAbstractTableModel):
    def __init__(self, df=pd.DataFrame(), save_callback=None):
        super().__init__(parent=None)
        self._df = df
        self.save_callback = save_callback

    def data(self, index, role=Qt.DisplayRole):
        return (
            self._df.ix[index.row(), index.column()] if index.isValid() else QVariant()
        )

    def setData(self, index, value, role):
        row = self._df.index[index.row()]
        col = self._df.columns[index.column()]
        self._df.set_value(row, col, value)
        self.dataChanged.emit(index, index)
        return True

    def rowCount(self, parent=QModelIndex()):
        return len(self._df.index)

    def columnCount(self, parent=QModelIndex()):
        return len(self._df.columns)

    def flags(self, index):
        return super().flags(index) | Qt.ItemIsEditable

    def save(self):
        if not self.save_callback is None:
            self.save_callback(self._df)
