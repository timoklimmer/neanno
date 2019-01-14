import pandas as pd


class AnnotationSuggester:
    """ Autosuggests annotations.

        Note: Primary purpose of this class is to suggest annotations such that it is easier to annotate text.
               
              You might use this class to predict key terms but for named entities you should use a real NER
              model (trained with the data annotated by neanno).
    """

    def __init__(self):
        pass

    def add_key_terms_dataset(self, spec):
        pass

    def add_named_entity_dataset(self, spec, entity_code):
        pass

    def add_key_term_regex(self, regex):
        pass

    def add_named_entity_regex(self, regex, entity_code):
        pass

    def add_key_term_to_dataset(self, key_term):
        pass

    def add_named_entity_to_dataset(self, term, entity_code):
        pass

    def remove_key_term_from_dataset(self, key_term):
        pass

    def remove_named_entity_from_dataset(self, term, entity_code):
        pass

    def suggest_annotations(self, text):
        pass

    def save_datasets(self):
        pass

