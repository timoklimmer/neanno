import re

import pandas as pd
from flashtext import KeywordProcessor

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

    key_terms_location_string = None
    key_terms_dataset = pd.DataFrame(columns=["term", "parent_terms"], dtype=str)
    key_terms_flashtext = None
    key_terms_marked_for_removal = []

    def load_key_terms_dataset(self, location_string):
        # update key_terms_location_string
        self.key_terms_location_string = location_string
        # load data
        self.key_terms_dataset = DatasetManager.load_dataset_from_location_string(
            location_string, {"term": str, "parent_terms": str}
        )[0]
        # setup flashtext for later string replacements
        temp_replace_against_dataset = self.key_terms_dataset.copy()
        temp_replace_against_dataset["replace"] = temp_replace_against_dataset["term"]
        temp_replace_against_dataset["against"] = temp_replace_against_dataset[
            "replace"
        ]
        temp_replace_against_dataset.loc[
            temp_replace_against_dataset["parent_terms"] != "", "against"
        ] = (
            "`"
            + temp_replace_against_dataset["term"]
            + "``PK``"
            + temp_replace_against_dataset["parent_terms"]
            + "`´"
        )
        temp_replace_against_dataset.loc[
            temp_replace_against_dataset["parent_terms"] == "", "against"
        ] = ("`" + temp_replace_against_dataset["term"] + "``SK`´")
        temp_replace_against_dataset = temp_replace_against_dataset[
            ["replace", "against"]
        ]
        temp_replace_against_dataset_as_dict = {
            row["against"]: [row["replace"]]
            for index, row in temp_replace_against_dataset.iterrows()
        }
        self.key_terms_flashtext = KeywordProcessor()
        self.key_terms_flashtext.add_keywords_from_dict(
            temp_replace_against_dataset_as_dict
        )

    def add_key_term_to_dataset(self, key_term, parent_terms):
        new_row = pd.DataFrame({"term": [key_term], "parent_terms": [parent_terms]})
        self.key_terms_dataset = self.key_terms_dataset.append(new_row)
        if parent_terms != "":
            self.key_terms_flashtext.add_keywords_from_dict(
                {"`{}``PK``{}`´".format(key_term, parent_terms): [key_term]}
            )
        else:
            self.key_terms_flashtext.add_keywords_from_dict(
                {"`{}``SK`´".format(key_term): [key_term]}
            )

    def remove_key_term_from_dataset(self, key_term):
        self.key_terms_dataset = self.key_terms_dataset[
            self.key_terms_dataset.term != key_term
        ]
        self.key_terms_flashtext.remove_keyword(key_term)

    def suggest_key_terms_by_dataset(self, text, skip_annotations_unmask=False):
        if self.key_terms_flashtext is not None:
            result = mask_annotations(text)
            result = self.key_terms_flashtext.replace_keywords(result)
            return result if skip_annotations_unmask else unmask_annotations(result)
        else:
            return text

    def update_key_terms_dataset(self, annotated_text):
        # get terms to add/update
        key_terms_to_add = {}
        parented_terms_to_update = []
        existing_terms_list = list(self.key_terms_dataset["term"])
        for annotation in extract_annotations_as_generator(
            annotated_text,
            types_to_extract=["standalone_key_term", "parented_key_term"],
        ):
            if annotation["term"] not in existing_terms_list:
                # term does not exist yet
                key_terms_to_add = merge_dict(
                    key_terms_to_add,
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
                        self.key_terms_dataset[
                            self.key_terms_dataset["term"] == annotation["term"]
                        ]["parent_terms"]
                    )[0]
                    if currently_stored_parent_terms != annotation["parent_terms"]:
                        # needs update
                        key_terms_to_add = merge_dict(
                            key_terms_to_add,
                            {
                                annotation["term"]: annotation["parent_terms"]
                                if "parent_terms" in annotation
                                else ""
                            },
                        )
                        parented_terms_to_update.append(annotation["term"])

        # get total terms to remove
        key_terms_to_remove = [
            term
            for term in self.key_terms_marked_for_removal
            if term not in key_terms_to_add
        ]
        key_terms_to_update = [term for term in parented_terms_to_update]
        key_terms_to_remove.extend(key_terms_to_update)

        # update key terms dataset (incl. flashtext)
        # remove
        if key_terms_to_remove:
            for key_term in key_terms_to_remove:
                self.remove_key_term_from_dataset(key_term)

        # add
        if key_terms_to_add:
            for key_term in key_terms_to_add:
                self.add_key_term_to_dataset(key_term, key_terms_to_add[key_term])
        # save
        self.save_key_terms_dataset(self.key_terms_location_string)

    def save_key_terms_dataset(self, location_string):
        # sort the key terms dataset for convenience
        self.key_terms_dataset["sort"] = self.key_terms_dataset["term"].str.lower()
        self.key_terms_dataset = self.key_terms_dataset.sort_values(by=["sort"])
        del self.key_terms_dataset["sort"]
        # save the dataset
        DatasetManager.save_dataset_to_location_string(
            self.key_terms_dataset, location_string
        )

    def mark_key_term_for_removal(self, term):
        if term not in self.key_terms_marked_for_removal:
            self.key_terms_marked_for_removal.append(term)

    def reset_key_terms_marked_for_removal(self):
        self.key_terms_marked_for_removal = []

    # key terms - regex

    key_term_regexes = {}

    def add_key_term_regex(self, name, pattern, parent_terms):
        self.key_term_regexes[name] = KeyTermRegex(name, pattern, parent_terms)

    def remove_key_term_regex(self, name):
        del self.key_term_regexes[name]

    def suggest_key_terms_by_regex(self, text, skip_annotations_unmask=False):
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
        return result if skip_annotations_unmask else unmask_annotations(result)

    # named entities

    # named entities - dataset

    named_entities_flashtext = None
    named_entities_dataset = pd.DataFrame(
        columns=["term", "entity_code", "parent_terms"], dtype=str
    )

    def load_named_entity_datasets(self, location_strings):
        # load entities into dataset
        for location_string in location_strings:
            new_data = DatasetManager.load_dataset_from_location_string(
                location_string,
                {"term": str, "entity_code": str, "parent_terms": str},
                "named_entities/auto_suggest/datasets",
            )[0]
            self.named_entities_dataset = self.named_entities_dataset.append(new_data)
        # update flashtext
        self.named_entities_flashtext = KeywordProcessor()
        data_for_flashtext = pd.DataFrame(
            {
                "against": [
                    "`{}``SN``{}`´".format(row["term"], row["entity_code"])
                    if not row["parent_terms"]
                    else "`{}``PN``{}``{}`´".format(
                        row["term"], row["entity_code"], row["parent_terms"]
                    )
                    for index, row in self.named_entities_dataset.iterrows()
                ],
                "replace": self.named_entities_dataset["term"],
            }
        )
        dict_for_flashtext = data_for_flashtext.set_index("against").T.to_dict("list")
        self.named_entities_flashtext.add_keywords_from_dict(dict_for_flashtext)

    def suggest_named_entities_by_dataset(self, text, skip_annotations_unmask=False):
        result = mask_annotations(text)
        result = self.named_entities_flashtext.replace_keywords(result)
        return result if skip_annotations_unmask else unmask_annotations(result)

    # named entities - regex

    named_entity_regexes = {}

    def add_named_entity_regex(self, entity_code, pattern, parent_terms):
        self.named_entity_regexes[entity_code] = NamedEntityRegex(
            entity_code, pattern, parent_terms
        )

    def remove_named_entity_regex(self, entity_code):
        del self.named_entity_regexes[entity_code]

    def suggest_named_entities_by_regex(self, text, skip_annotations_unmask=False):
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
        return result if skip_annotations_unmask else unmask_annotations(result)

    # named entities - general
    def get_parent_terms_for_named_entity(self, entity_code, term):
        # TODO: add parent_terms from autosuggest by regex
        dataset_query_result = list(
            self.named_entities_dataset[
                (self.named_entities_dataset["entity_code"] == entity_code)
                & (self.named_entities_dataset["term"] == term)
            ]["parent_terms"]
        )
        if len(dataset_query_result) > 0:
            dataset_query_result = dataset_query_result[0]
            dataset_query_result = (
                None
                if dataset_query_result is None or pd.isnull(dataset_query_result)
                else dataset_query_result
            )
        else:
            dataset_query_result = None
        return dataset_query_result

    # general

    def suggest(self, text):
        result = text
        result = self.suggest_key_terms_by_dataset(result, True)
        result = mask_annotations(result)
        result = self.suggest_key_terms_by_regex(result, True)
        result = mask_annotations(result)
        result = self.suggest_named_entities_by_dataset(result, True)
        result = mask_annotations(result)
        result = self.suggest_named_entities_by_regex(result, True)
        result = unmask_annotations(result)
        return result
