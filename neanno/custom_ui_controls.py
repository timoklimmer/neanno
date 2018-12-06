from PyQt5.QtCore import Qt, pyqtProperty
from PyQt5.QtWidgets import (QDataWidgetMapper, QListWidget)


class QDataWidgetMapperWithHistory(QDataWidgetMapper):
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


class MappableQListWidget(QListWidget):
    def get_selected_items_as_string(self):
        return "|".join([item.text() for item in self.selectedItems()])

    def set_selected_items_as_string(self, value):
        self.clearSelection()
        for selectedItem in value.split("|"):
            for itemToSelect in self.findItems(selectedItem, Qt.MatchExactly):
                itemToSelect.setSelected(True)

    selectedItemsAsString = pyqtProperty(
        str, fget=get_selected_items_as_string, fset=set_selected_items_as_string
    )
