import os

import config
from PyQt5.QtCore import Qt, pyqtProperty
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)


class CategoriesSelectorWidget(QTableWidget):
    """
    A custom QTableWidget used for showing/selecting the categories of a text.
    """

    config = None
    textmodel = None

    def __init__(self, config, textmodel):
        super().__init__()
        self.adjust_highlight_color_on_windows()
        self.config = config
        self.textmodel = textmodel
        self.setColumnCount(2)
        self.setRowCount(config.categories_count)
        self.setShowGrid(False)
        self.horizontalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(
            self.verticalHeader().minimumSectionSize()
        )
        self.setMaximumHeight(
            self.verticalHeader().minimumSectionSize() * self.rowCount()
        )
        self.setFrameStyle(QFrame.NoFrame)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.MultiSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setFocusPolicy(Qt.NoFocus)
        self.populate_categories()

    def adjust_highlight_color_on_windows(self):
        # adjust the colors for highlighted entries if we are on Windows
        # note: this is required because the highlighted color in Windows
        #       may be very light, hence make neanno inconvenient to use
        if os.name == "nt":
            new_palette = self.palette()
            new_palette.setColor(QPalette.Highlight, QColor("#243a5e"))
            new_palette.setColor(QPalette.HighlightedText, QColor("white"))
            self.setPalette(new_palette)

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
        return selected_categories_sorted

    def get_selected_categories_as_text(self):
        return "|".join(self.get_selected_categories())

    def set_selected_categories(self, value):
        self.clearSelection()
        for selected_category in value:
            row_indexes_to_select = [
                found_item.row()
                for found_item in self.findItems(selected_category, Qt.MatchExactly)
            ]
            for row_index_to_select in row_indexes_to_select:
                for column_index in range(0, self.columnCount()):
                    self.item(row_index_to_select, column_index).setSelected(True)

    def set_selected_categories_by_text(self, value):
        self.clearSelection()
        if value != "":
            self.set_selected_categories(value.split("|"))

    selected_categories_text = pyqtProperty(
        str, fget=get_selected_categories_as_text, fset=set_selected_categories_by_text
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
