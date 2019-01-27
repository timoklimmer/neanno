from abc import ABC

class Predictor(ABC):
    _name = None
    _enabled = None

    def __init__(self, name, enabled):
        self._name = name
        self._enabled = enabled

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        