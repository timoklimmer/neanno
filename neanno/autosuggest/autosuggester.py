import re

# TODO: remove all config dependencies
import config
import pandas as pd

from neanno.autosuggest.definitions import *
from neanno.utils.dataset import DatasetManager
from neanno.utils.dict import merge_dict
from neanno.utils.text import (
    extract_annotations_as_generator,
    mask_annotations,
    unmask_annotations,
)


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

    def update_key_terms_dataset(self, annotated_text, location_string):
        if config.is_autosuggest_key_terms_by_dataset:
            # get terms to add/update
            terms_to_add = {}
            parented_terms_to_update = []
            existing_terms_list = list(config.autosuggest_key_terms_dataset["term"])
            for annotation in extract_annotations_as_generator(
                annotated_text,
                types_to_extract=["standalone_key_term", "parented_key_term"],
            ):
                if annotation["term"] not in existing_terms_list:
                    # term does not exist yet
                    terms_to_add = merge_dict(
                        terms_to_add,
                        {
                            annotation["term"]: annotation["parent_terms"]
                            if "parent_terms" in annotation
                            else ""
                        },
                    )
                else:
                    # term exists but may need update due to different parent terms
                    if "parent_terms" in annotation:
                        currently_stored_parent_terms = list(
                            config.autosuggest_key_terms_dataset[
                                config.autosuggest_key_terms_dataset["term"]
                                == annotation["term"]
                            ]["parent_terms"]
                        )[0]
                        if currently_stored_parent_terms != annotation["parent_terms"]:
                            # needs update
                            terms_to_add = merge_dict(
                                terms_to_add,
                                {
                                    annotation["term"]: annotation["parent_terms"]
                                    if "parent_terms" in annotation
                                    else ""
                                },
                            )
                            parented_terms_to_update.append(annotation["term"])

            # get total terms to remove
            terms_to_remove = [
                term
                for term in config.key_terms_marked_for_removal
                if term not in terms_to_add
            ]
            terms_to_update = [term for term in parented_terms_to_update]
            terms_to_remove.extend(terms_to_update)

            # update autosuggest dataset
            # remove
            if terms_to_remove:
                for term in terms_to_remove:
                    config.autosuggest_key_terms_dataset = config.autosuggest_key_terms_dataset[
                        config.autosuggest_key_terms_dataset.term != term
                    ]
            # add
            if terms_to_add:
                for term in terms_to_add:
                    new_row = pd.DataFrame(
                        {"term": [term], "parent_terms": [terms_to_add[term]]}
                    )
                    config.autosuggest_key_terms_dataset = config.autosuggest_key_terms_dataset.append(
                        new_row
                    )
            # save
            self.save_key_terms_dataset(location_string)

            # update flashtext
            # remove obsolete terms
            if terms_to_remove:
                for term in terms_to_remove:
                    config.key_terms_autosuggest_flashtext.remove_keyword(term)
            # add new terms
            if terms_to_add:
                for term in terms_to_add:
                    if terms_to_add[term] != "":
                        config.key_terms_autosuggest_flashtext.add_keywords_from_dict(
                            {"`{}``PK``{}`´".format(term, terms_to_add[term]): [term]}
                        )
                    else:
                        config.key_terms_autosuggest_flashtext.add_keywords_from_dict(
                            {"`{}``SK`´".format(term): [term]}
                        )

    def save_key_terms_dataset(self, location_string):
        # sort the key terms dataset for convenience
        config.autosuggest_key_terms_dataset[
            "sort"
        ] = config.autosuggest_key_terms_dataset["term"].str.lower()
        config.autosuggest_key_terms_dataset = config.autosuggest_key_terms_dataset.sort_values(
            by=["sort"]
        )
        del config.autosuggest_key_terms_dataset["sort"]
        # save the dataset
        DatasetManager.save_dataset_to_location_string(
            config.autosuggest_key_terms_dataset, location_string
        )

    def mark_key_term_for_removal(self, term):
        if term not in config.key_terms_marked_for_removal:
            config.key_terms_marked_for_removal.append(term)

    def reset_key_terms_marked_for_removal(self):
        config.key_terms_marked_for_removal = []

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

    named_entity_regexes = {}

    def add_named_entity_regex(self, entity_code, pattern, parent_terms):
        self.named_entity_regexes[entity_code] = NamedEntityRegex(
            entity_code, pattern, parent_terms
        )

    def remove_named_entity_regex(self, entity_code):
        del self.named_entity_regexes[entity_code]

    def suggest_named_entities_by_regex(self, text):
        result = mask_annotations(text)
        for named_entity_code in self.named_entity_regexes:
            named_entity_regex = self.named_entity_regexes[named_entity_code]
            if named_entity_regex.parent_terms:
                result = re.sub(
                    r"(?P<term>{})".format(named_entity_regex.pattern),
                    "`{}``PN``{}``{}`´".format(
                        "\g<term>",
                        named_entity_regex.entity,
                        named_entity_regex.parent_terms,
                    ),
                    result,
                )
            else:
                result = re.sub(
                    r"(?P<term>{})".format(named_entity_regex.pattern),
                    "`{}``SN``{}`´".format("\g<term>", named_entity_regex.entity),
                    result,
                )
        return unmask_annotations(result)

    # general

    def suggest(self, text):
        result = text
        result = self.suggest_key_terms_by_dataset(result)
        result = self.suggest_key_terms_by_regex(result)
        result = self.suggest_named_entities_by_dataset(result)
        result = self.suggest_named_entities_by_regex(result)
        return result
