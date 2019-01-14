import re

from neanno.autosuggest.definitions import *
from neanno.utils.text import mask_annotations, unmask_annotations


class AutoSuggester:
    """ Autosuggests annotations.

        Note: Primary purpose of this class is to suggest annotations such that it is easier to annotate text.
               
              You might use this class to predict key terms but for named entities you should use a real NER
              model (trained with the data annotated by neanno).
    """

    # constructor

    def __init__(self):
        pass

    # key terms

    # key terms - dataset

    def load_key_terms_dataset(self, location):
        pass

    def add_key_term_to_dataset(self, key_term):
        pass

    def remove_key_term_from_dataset(self, key_term):
        pass

    def suggest_key_terms_by_dataset(self, text):
        # TODO: complete
        return text

    def save_key_terms_dataset(text):
        pass

    # key terms - regex

    key_term_regexes = {}

    def add_key_term_regex(self, name, pattern, parent_terms):
        self.key_term_regexes[name] = KeyTermRegex(name, pattern, parent_terms)

    def remove_key_term_regex(self, name):
        del self.key_term_regexes[name]

    def suggest_key_terms_by_regex(self, text):
        result = mask_annotations(text)
        for key_term_regex_name in self.key_term_regexes:
            key_term_regex = self.key_term_regexes[key_term_regex_name]
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
        return unmask_annotations(result)

    # named entities

    # named entities - dataset

    def load_named_entity_dataset(self, location, entity_code):
        pass

    def add_named_entity_to_dataset(self, term, entity_code):
        pass

    def remove_named_entity_from_dataset(self, term, entity_code):
        pass

    def suggest_named_entities_by_dataset(self, text):
        # TODO: complete
        return text

    def save_named_entity_dataset(self, entity_code):
        pass

    # named entities - regex

    def add_named_entity_regex(self, entity_code, regex):
        pass

    def remove_named_entity_regex(self, entity_code):
        pass

    def suggest_named_entities_by_regex(self, text):
        # TODO: complete
        return text

    # general

    def suggest(self, text):
        result = text
        result = self.suggest_key_terms_by_dataset(result)
        result = self.suggest_key_terms_by_regex(result)
        result = self.suggest_named_entities_by_dataset(result)
        result = self.suggest_named_entities_by_regex(result)
        return result
