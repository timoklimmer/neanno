from abc import ABC, abstractmethod, abstractproperty

import yaml

from neanno.utils.yaml import validate_yaml


class Predictor(ABC):
    _name = None
    _is_prediction_enabled = None
    _config = None

    def __init__(self, predictor_config):
        try:
            validate_yaml(predictor_config, self.config_validation_schema)
        except:
            print(
                "Failed to create predictor{} because it was given a wrong configuration. To create the predictor you must follow it's required configuration schema.".format(
                    " '" + predictor_config["name"] + "'"
                    if "name" in predictor_config
                    else ""
                )
            )
            raise
        self._config = predictor_config
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
    def config_validation_schema(self):
        return {
            **self.config_validation_schema_base,
            **self.config_validation_schema_custom_part,
        }

    @property
    def config_validation_schema_base(self):
        return yaml.load(
            """
            name:
                type: string
                required: True
            module:
                type: string
                required: True
            class:
                type: string
                required: True
            is_prediction_enabled:
                type: boolean
                required: True
        """
        )

    @property
    @abstractmethod
    def config_validation_schema_custom_part(self):
        pass

    @property
    def is_prediction_enabled(self):
        return self._is_prediction_enabled

    @is_prediction_enabled.setter
    def is_prediction_enabled(self, value):
        self._is_prediction_enabled = value
