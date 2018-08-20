# from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex

# import pandas as pd


class _MyModel(QAbstractTableModel):
    def __init__(self, data, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.lst = data

    def columnCount(self, parent=QModelIndex()):
        return len(self.lst[0])

    def rowCount(self, parent=QModelIndex()):
        return len(self.lst)

    def data(self, index, role=Qt.DisplayRole):
        row = index.row()
        col = index.column()

        if role == Qt.EditRole:
            return self.lst[row][col]
        elif role == Qt.DisplayRole:
            return self.lst[row][col]

    def flags(self, index):
        flags = super(_MyModel, self).flags(index)

        if index.isValid():
            flags |= Qt.ItemIsEditable
            flags |= Qt.ItemIsDragEnabled
        else:
            flags = Qt.ItemIsDropEnabled

        return flags

    def setData(self, index, value, role=Qt.EditRole):

        if not index.isValid() or role != Qt.EditRole:
            return False

        self.lst[index.row()][index.column()] = value
        self.dataChanged.emit(index, index)
        return True


# class PandasModel(QtCore.QAbstractTableModel):
#     def __init__(self, df=pd.DataFrame(), parent=None):
#         QtCore.QAbstractTableModel.__init__(self, parent=parent)
#         self._df = df

#     def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
#         if role != QtCore.Qt.DisplayRole:
#             return QtCore.QVariant()

#         if orientation == QtCore.Qt.Horizontal:
#             try:
#                 return self._df.columns.tolist()[section]
#             except (IndexError,):
#                 return QtCore.QVariant()
#         elif orientation == QtCore.Qt.Vertical:
#             try:
#                 # return self.df.index.tolist()
#                 return self._df.index.tolist()[section]
#             except (IndexError,):
#                 return QtCore.QVariant()

#     def data(self, index, role=QtCore.Qt.DisplayRole):
#         if role != QtCore.Qt.DisplayRole:
#             return QtCore.QVariant()

#         if not index.isValid():
#             return QtCore.QVariant()

#         return QtCore.QVariant(str(self._df.ix[index.row(), index.column()]))

#     def setData(self, index, value, role):
#         row = self._df.index[index.row()]
#         col = self._df.columns[index.column()]
#         if hasattr(value, "toPyObject"):
#             # PyQt4 gets a QVariant
#             value = value.toPyObject()
#         else:
#             # PySide gets an unicode
#             dtype = self._df[col].dtype
#             if dtype != object:
#                 value = None if value == "" else dtype.type(value)
#         self._df.set_value(row, col, value)
#         self.dataChanged.emit(index, index)
#         return True

#     def rowCount(self, parent=QtCore.QModelIndex()):
#         return len(self._df.index)

#     def columnCount(self, parent=QtCore.QModelIndex()):
#         return len(self._df.columns)

#     def sort(self, column, order):
#         colname = self._df.columns.tolist()[column]
#         self.layoutAboutToBeChanged.emit()
#         self._df.sort_values(
#             colname, ascending=order == QtCore.Qt.AscendingOrder, inplace=True
#         )
#         self._df.reset_index(inplace=True, drop=True)
#         self.layoutChanged.emit()
