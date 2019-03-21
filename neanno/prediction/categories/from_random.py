import random
import re

import yaml

from neanno.prediction.predictor import Predictor

class FromRandomCategoryPredictor(Predictor):
    """ Randomly predicts some text categories."""

    categories = []

    def __init__(self, predictor_config):
        super().__init__(predictor_config)

    @property
    def config_validation_schema_custom_part(self):
        return yaml.load(
            """
            """
        )

    def learn_from_annotated_dataset(
        self,
        dataset,
        text_column,
        is_annotated_column,
        language_column,
        categories_column,
        categories_to_train,
        entity_codes_to_train,
        signals,
    ):
        self.categories = categories_to_train

    def predict_text_categories(self, text, language="en-US"):
        if self.categories:
            return random.sample(
                self.categories, random.sample(range(1, len(self.categories)), 1)[0]
            )
        else:
            return []
