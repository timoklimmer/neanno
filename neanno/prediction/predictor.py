import uuid
from abc import ABC, abstractmethod, abstractproperty

import yaml

from neanno.utils.yaml import validate_yaml


class Predictor(ABC):
    _name = None
    _is_prediction_enabled = None
    _predictor_config = None

    def __init__(self, predictor_config):
        self._predictor_config = predictor_config
        self._name = (
            self._predictor_config["name"]
            if "name" in self._predictor_config
            else str(uuid.uuid4())
        )
        self._is_prediction_enabled = (
            self._predictor_config["is_prediction_enabled"]
            if "is_prediction_enabled" in self._predictor_config
            else True
        )
        try:
            validate_yaml(self._predictor_config, self.config_validation_schema)
        except:
            print(
                "Failed to create predictor '{}' because it was given a wrong configuration. To create the predictor you must follow it's required configuration schema.".format(
                    self._name
                )
            )
            raise

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def config(self):
        return self._predictor_config

    @config.setter
    def config(self, value):
        self._predictor_config = value

    @property
    def config_validation_schema(self):
        return {
            **self.config_validation_schema_base,
            **self.config_validation_schema_custom_part,
        }

    @property
    def config_validation_schema_base(self):
        # notes: - these are the minimum requirements to instantiate a predictor.
        #          when a predictor is instantiated from the neanno UI, more
        #          fields may be required, and the neanno UI will validate for them.
        #          see the neanno UI's config schema for more details.
        return yaml.load(
            """
            name:
                type: string
                required: False
            module:
                type: string
                required: False
            class:
                type: string
                required: False
            is_prediction_enabled:
                type: boolean
                required: False
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

    def learn_from_annotated_text(self, annotated_text):
        pass

    def learn_from_annotated_dataset(
        self,
        dataset,
        text_column,
        is_annotated_column,
        categories_column,
        categories_to_train,
        entity_codes_to_train,
    ):
        pass

    def predict_inline_annotations(self, text):
        return text

    def predict_categories(self, text):
        return []
