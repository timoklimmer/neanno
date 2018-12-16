import config
from PyQt5.QtCore import Qt, pyqtProperty
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDataWidgetMapper,
    QFrame,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)


class QDataWidgetMapperWithHistory(QDataWidgetMapper):
    """ A QDataWidgetMapper which additionally lets users navigate backwards and forwards."""

    backward_stack = []
    forward_stack = []
    is_forward_or_backward = False

    def __init__(self, parent=None):
        super().__init__(parent)

    def setCurrentIndex(self, index):
        if self.currentIndex() != index:
            if not self.is_forward_or_backward:
                self.forward_stack = []
                self.backward_stack.append(self.currentIndex())
            super().setCurrentIndex(index)

    def backward(self):
        if len(self.backward_stack) > 0:
            self.forward_stack.append(self.currentIndex())
            self.is_forward_or_backward = True
            self.setCurrentIndex(self.backward_stack.pop())
            self.is_forward_or_backward = False

    def forward(self):
        if len(self.forward_stack) > 0:
            self.backward_stack.append(self.currentIndex())
            self.is_forward_or_backward = True
            self.setCurrentIndex(self.forward_stack.pop())
            self.is_forward_or_backward = False


class CategoriesTableWidget(QTableWidget):
    """
    A custom QTableWidget used for showing/selecting the categories of a text.
    """

    config = None
    textmodel = None

    def __init__(self, config, textmodel):
        super().__init__()
        self.config = config
        self.textmodel = textmodel
        self.setColumnCount(2)
        self.setRowCount(config.categories_count)
        self.horizontalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(
            self.verticalHeader().minimumSectionSize()
        )
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.MultiSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setFocusPolicy(Qt.NoFocus)
        self.populate_categories()

    def populate_categories(self):
        row = 0
        for category in config.category_definitions:
            name_item = QTableWidgetItem()
            name_item.setText(category.name)
            name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.setItem(row, 0, name_item)
            frequency_item = QTableWidgetItem()
            frequency_item.setText("0")
            frequency_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 1, frequency_item)
            row += 1

    def get_selected_categories(self):
        selected_categories = []
        for selected_row in self.selectionModel().selectedRows():
            selected_category = self.item(selected_row.row(), 0).text()
            selected_categories.append(selected_category)
        selected_categories_sorted = sorted(
            selected_categories, key=lambda x: config.categories_names_list.index(x)
        )
        return "|".join(selected_categories_sorted)

    def set_selected_categories(self, value):
        self.clearSelection()
        for selected_category in value.split("|"):
            row_indexes_to_select = [
                found_item.row()
                for found_item in self.findItems(selected_category, Qt.MatchExactly)
            ]
            for row_index_to_select in row_indexes_to_select:
                for column_index in range(0, self.columnCount()):
                    self.item(row_index_to_select, column_index).setSelected(True)

    selected_categories = pyqtProperty(
        str, fget=get_selected_categories, fset=set_selected_categories
    )

    def update_categories_distribution(self):
        for category in self.textmodel.category_distribution:
            row_indexes_to_update = [
                found_item.row()
                for found_item in self.findItems(category, Qt.MatchExactly)
            ]
            for row_index_to_update in row_indexes_to_update:
                self.item(row_index_to_update, 1).setText(
                    str(self.textmodel.category_distribution[category])
                )
                