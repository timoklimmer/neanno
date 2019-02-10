from abc import ABC, abstractmethod, abstractproperty
from neanno.utils.yaml import validate_yaml


class Predictor(ABC):
    _name = None
    _is_prediction_enabled = None
    _config = None

    def __init__(self, config):
        try:
            validate_yaml(config, self.config_validation_schema)
        except:
            print(
                "Failed to create predictor{} because it was given a wrong configuration. To create the predictor you must follow it's required configuration schema.".format(
                    " '" + config["name"] + "'" if "name" in config else ""
                )
            )
            raise
        self._config = config
        self._name = self._config["name"]
        self._is_prediction_enabled = self._config["is_prediction_enabled"]

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, value):
        self._config = value

    @property
    @abstractmethod
    def config_validation_schema(self):
        pass

    @property
    def is_prediction_enabled(self):
        return self._is_prediction_enabled

    @is_prediction_enabled.setter
    def is_prediction_enabled(self, value):
        self._is_prediction_enabled = value
