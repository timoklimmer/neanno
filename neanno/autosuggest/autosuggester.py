import re

import pandas as pd
from flashtext import KeywordProcessor

from neanno.autosuggest.named_entities_by_config import NamedEntitiesSuggesterByConfig
from neanno.prediction.keyterms import KeyTermPredictor
from neanno.utils.dataset import DatasetManager
from neanno.utils.dict import merge_dict
from neanno.utils.text import (
    extract_annotations_as_generator,
    mask_annotations,
    unmask_annotations,
)


class AnnotationSuggester(KeyTermPredictor, NamedEntitiesSuggesterByConfig):
    """ Autosuggests annotations.

        Note: This class is not intended for use as final predictor as because
              the suggestions made are primarily meant to facilitate annotation.
    """

    def suggest(self, text, suggest_key_terms=True, suggest_named_entities=True):
        result = text
        if suggest_key_terms:
            result = self.predict_key_terms_by_dataset(result, True)
            result = mask_annotations(result)
            result = self.predict_key_terms_by_regex(result, True)
            result = mask_annotations(result)
        if suggest_named_entities:
            result = self.suggest_named_entities_by_dataset(result, True)
            result = mask_annotations(result)
            result = self.suggest_named_entities_by_regex(result, True)
        result = unmask_annotations(result)
        return result
