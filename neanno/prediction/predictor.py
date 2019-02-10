from abc import ABC


class Predictor(ABC):
    _name = None
    _is_prediction_enabled = None
    _predictor_config = None

    def __init__(self, _predictor_config):
        self._predictor_config = _predictor_config
        self._name = self._predictor_config["name"]
        self._is_prediction_enabled = self._predictor_config["is_prediction_enabled"]

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def predictor_config(self):
        return self._predictor_config

    @predictor_config.setter
    def predictor_config(self, value):
        self._predictor_config = value

    @property
    def is_prediction_enabled(self):
        return self._is_prediction_enabled

    @is_prediction_enabled.setter
    def is_prediction_enabled(self, value):
        self._is_prediction_enabled = value

