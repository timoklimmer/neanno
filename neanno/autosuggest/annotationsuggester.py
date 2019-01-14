class AnnotationSuggester:
    """ Autosuggests annotations.

        Note: Primary purpose of this class is to suggest annotations such that it is easier to annotate text.
               
              You might use this class to predict key terms but for named entities you should use a real NER
              model (trained with the data annotated by neanno).
    """

    # constructor

    def __init__(self):
        pass

    # general functions

    @staticmethod
    def load():
        pass

    @staticmethod
    def save():
        pass

    # key terms

    # key terms - dataset

    def load_key_terms_dataset(self, location):
        pass

    def add_key_term_to_dataset(self, key_term):
        pass

    def remove_key_term_from_dataset(self, key_term):
        pass

    def suggest_key_terms_by_dataset(self):
        pass

    def save_key_terms_dataset(text):
        pass

    # key terms - regex

    def add_key_term_regex(self, name, regex):
        pass

    def remove_key_term_regex(self, name):
        pass

    def suggest_key_terms_by_regex(self, text):
        pass

    # named entities

    # named entities - dataset

    def load_named_entity_dataset(self, location, entity_code):
        pass

    def add_named_entity_to_dataset(self, term, entity_code):
        pass

    def remove_named_entity_from_dataset(self, term, entity_code):
        pass

    def suggest_named_entities_by_dataset(self, entity_code):
        pass

    def save_named_entity_dataset(self, entity_code):
        pass

    # named entities - regex

    def add_named_entity_regex(self, entity_code, regex):
        pass

    def remove_named_entity_regex(self, entity_code):
        pass

    def suggest_annotations(self, text):
        pass

