import uuid
from abc import ABC, abstractmethod

import pandas as pd
import yaml

from neanno.utils.metrics import (
    compute_category_metrics,
    compute_ner_metrics,
    get_confusion_matrix,
    get_confusion_matrix_png_bytes,
)
from neanno.utils.signals import *
from neanno.utils.text import normalize_labels_values, remove_all_annotations_from_text
from neanno.utils.yaml import validate_yaml


class Predictor(ABC):
    """Base class for a predictor which can predict different things such as text categories, named entities or key terms."""

    _name = None
    _is_online_training_enabled = None
    _is_batch_training_enabled = None
    _is_prediction_enabled = None
    _is_testing_enabled = None
    _predictor_config = None

    def __init__(self, predictor_config):
        self._predictor_config = predictor_config
        self._name = (
            self._predictor_config["name"]
            if "name" in self._predictor_config
            else str(uuid.uuid4())
        )
        try:
            validate_yaml(self._predictor_config, self.project_config_validation_schema)
        except:
            print(
                "Failed to create predictor '{}' because it was given a wrong configuration. To create the predictor you must follow it's required configuration schema.".format(
                    self._name
                )
            )
            raise
        self._is_online_training_enabled = self.supports_online_training and (
            self._predictor_config["is_online_training_enabled"]
            if "is_online_training_enabled" in self._predictor_config
            else True
        )
        self._is_batch_training_enabled = self.supports_batch_training and (
            self._predictor_config["is_batch_training_enabled"]
            if "is_batch_training_enabled" in self._predictor_config
            else True
        )
        self._is_prediction_enabled = (
            self._predictor_config["is_prediction_enabled"]
            if "is_prediction_enabled" in self._predictor_config
            else True
        )
        # TODO: make public in config
        self._is_testing_enabled = True

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
    def project_config_validation_schema(self):
        if self.project_config_validation_schema_custom_part:
            return {
                **self.project_config_validation_schema_base,
                **self.project_config_validation_schema_custom_part,
            }
        else:
            return {**self.project_config_validation_schema_base}

    @property
    def project_config_validation_schema_base(self):
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
            is_online_training_enabled:
                type: boolean
                required: False           
            is_batch_training_enabled:
                type: boolean
                required: False
            is_prediction_enabled:
                type: boolean
                required: False
        """,
            Loader=yaml.FullLoader,
        )

    @property
    @abstractmethod
    def project_config_validation_schema_custom_part(self):
        pass

    @property
    @abstractmethod
    def supports_online_training(self):
        pass

    @property
    @abstractmethod
    def supports_batch_training(self):
        pass

    @property
    def is_online_training_enabled(self):
        return self._is_online_training_enabled

    @is_online_training_enabled.setter
    def is_online_training_enabled(self, value):
        self._is_online_training_enabled = value

    @property
    def is_batch_training_enabled(self):
        return self._is_batch_training_enabled

    @is_batch_training_enabled.setter
    def is_batch_training_enabled(self, value):
        self._is_batch_training_enabled = value

    @property
    def is_prediction_enabled(self):
        return self._is_prediction_enabled

    @is_prediction_enabled.setter
    def is_prediction_enabled(self, value):
        self._is_prediction_enabled = value

    @property
    def is_testing_enabled(self):
        return self._is_testing_enabled

    @is_testing_enabled.setter
    def is_testing_enabled(self, value):
        self._is_testing_enabled = value

    def train_from_annotated_text(self, annotated_text, language="en-us"):
        pass

    def train_from_trainset(
        self,
        trainset,
        text_column,
        is_annotated_column,
        language_column,
        categories_column,
        categories_to_train,
        entity_codes_to_train,
        signals,
    ):
        pass

    def predict_inline_annotations(self, text, language="en-US"):
        return text

    def predict_text_categories(self, text, language="en-US"):
        return []

    def test_model(
        self,
        testset,
        text_column,
        is_annotated_column,
        language_column,
        categories_column,
        categories_to_train,
        entity_codes_to_train,
        signals,
    ):
        pass


class CategoriesPredictor(Predictor):
    """A predictor which predicts the categories of a text."""

    def test_model(
        self,
        testset,
        text_column,
        is_annotated_column,
        language_column,
        categories_column,
        categories_to_train,
        entity_codes_to_train,
        signals,
    ):
        """Tests how well the predictor predicts categories."""

        # inform about this predictor
        emit_sub_header(self.name, signals)

        # compute metrics
        actual_categories_series = testset[categories_column]
        predicted_categories_series = testset.apply(
            lambda row: (
                "|".join(
                    self.predict_text_categories(
                        row[text_column],
                        row[language_column] if language_column else "en-US",
                    )
                )
            ),
            axis=1,
        )
        category_metrics = pd.DataFrame(
            compute_category_metrics(
                actual_categories_series,
                predicted_categories_series,
                categories_to_train,
            )
        ).T
        category_metrics = category_metrics[
            [
                "actual",
                "predictions",
                "correct",
                "incorrect",
                "precision",
                "recall",
                "f1_score",
            ]
        ].astype(
            {
                "actual": int,
                "predictions": int,
                "correct": int,
                "incorrect": int,
                "precision": float,
                "recall": float,
                "f1_score": float,
            }
        )

        # emit metrics
        emit_message(category_metrics.to_string(), signals)

        # emit blank line for better readability
        emit_message("", signals)

        # emit confusion matrix
        actual_categories_series_normalized = normalize_labels_values(
            actual_categories_series
        )
        predicted_categories_series_normalized = normalize_labels_values(
            predicted_categories_series
        )
        # png_bytes = get_confusion_matrix_png_bytes(
        #     actual_categories_series_normalized,
        #     predicted_categories_series,
        #     categories_to_train,
        # )
        # emit_image(png_bytes, "png", signals)
        emit_message(
            get_confusion_matrix(
                actual_categories_series_normalized,
                predicted_categories_series_normalized,
                categories_to_train
            ).to_string(),
            signals
        )

        # emit two new lines to improve readability of output
        emit_new_line(signals)
        emit_new_line(signals)


class NamedEntitiesPredictor(Predictor):
    """A predictor which predicts named entities of a text."""

    def test_model(
        self,
        testset,
        text_column,
        is_annotated_column,
        language_column,
        categories_column,
        categories_to_train,
        entity_codes_to_train,
        signals,
    ):
        """Tests how well the predictor predicts named entities."""

        # inform about this predictor
        emit_sub_header(self.name, signals)

        # compute metrics
        actual_annotations = testset[text_column]
        predicted_annotations = testset.apply(
            lambda row: (
                self.predict_inline_annotations(
                    remove_all_annotations_from_text(row[text_column]),
                    row[language_column] if language_column else "en-US",
                )
            ),
            axis=1,
        )
        ner_metrics = pd.DataFrame(
            compute_ner_metrics(
                actual_annotations, predicted_annotations, entity_codes_to_train
            )
        ).T
        ner_metrics = ner_metrics[
            [
                "actual",
                "predictions",
                "correct",
                "incorrect",
                "precision",
                "recall",
                "f1_score",
            ]
        ].astype(
            {
                "actual": int,
                "predictions": int,
                "correct": int,
                "incorrect": int,
                "precision": float,
                "recall": float,
                "f1_score": float,
            }
        )

        # emit result
        emit_message(pd.DataFrame(ner_metrics).to_string(), signals)

        # emit two new lines to improve readability of output
        emit_new_line(signals)
        emit_new_line(signals)


class KeyTermsPredictor(Predictor):
    pass
