import re

from neanno.prediction.predictor import Predictor
from neanno.utils.text import mask_annotations, unmask_annotations


class KeyTermsFromRegexPredictor(Predictor):
    """ Predicts key terms of a text by using regular expressions."""

    key_term_regexes = {}

    def __init__(self, name, enabled):
        super().__init__(name, enabled)

    def add_key_term_regex(self, entity_code, pattern, parent_terms):
        self.key_term_regexes[entity_code] = KeyTermRegex(
            entity_code, pattern, parent_terms
        )

    def remove_key_term_regex(self, entity_code):
        del self.key_term_regexes[entity_code]

    def predict_inline_annotations(self, text, mask_annotations_before_return=False):
        result = mask_annotations(text)
        for entity_code in self.key_term_regexes:
            key_term_regex = self.key_term_regexes[entity_code]
            if key_term_regex.parent_terms:
                result = re.sub(
                    r"(?P<term>{})".format(key_term_regex.pattern),
                    "`{}``PK``{}`´".format("\g<term>", key_term_regex.parent_terms),
                    result,
                )
            else:
                result = re.sub(
                    r"(?P<term>{})".format(key_term_regex.pattern),
                    "`{}``SK`´".format("\g<term>"),
                    result,
                )
        return (
            mask_annotations(result)
            if mask_annotations_before_return
            else unmask_annotations(result)
        )


class KeyTermRegex:
    """ Defines a regex for predicting key terms."""

    def __init__(self, entity_code, pattern, parent_terms=[]):
        self.entity_code = entity_code
        self.pattern = pattern
        self.parent_terms = parent_terms