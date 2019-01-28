from abc import ABC


class Predictor(ABC):
    _name = None
    _enabled_for_prediction = None

    def __init__(self, name, enabled_for_prediction):
        self._name = name
        self._enabled_for_prediction = enabled_for_prediction

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def enabled_for_prediction(self):
        return self._enabled_for_prediction

    @enabled_for_prediction.setter
    def enabled_for_prediction(self, value):
        self._enabled_for_prediction = value

