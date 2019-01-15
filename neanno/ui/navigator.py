import config
from PyQt5.QtWidgets import QDataWidgetMapper

from neanno.configuration.configmanager import ConfigManager


class TextNavigator(QDataWidgetMapper):
    """ A QDataWidgetMapper which additionally lets users navigate backwards and forwards."""

    backward_stack = []
    forward_stack = []
    is_forward_or_backward = False

    def __init__(self, parent=None):
        super().__init__(parent)

    def getCurrentIndex(self):
        return self.currentIndex()

    def setCurrentIndex(self, index):
        if self.currentIndex() != index:
            if not self.is_forward_or_backward:
                self.forward_stack = []
                self.backward_stack.append(self.currentIndex())
            config.autosuggester.reset_key_terms_marked_for_removal()
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
