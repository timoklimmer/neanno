import pandas as pd
import yaml
from flashtext import KeywordProcessor

from neanno.prediction.predictor import Predictor
from neanno.utils.dataset import DatasetManager
from neanno.utils.dict import merge_dict
from neanno.utils.text import (
    extract_annotations_as_generator
)


class FromDatasetsNamedEntitiesPredictor(Predictor):
    """ Predicts named entities of a text by looking up terms in a dataset."""

    location_strings = {}
    dataset = pd.DataFrame(columns=["term", "entity_code", "parent_terms"], dtype=str)
    flashtext = None
    marked_for_removal = []

    def __init__(self, predictor_config):
        super().__init__(predictor_config)
        self.load_datasets(predictor_config["datasets"])

    @property
    def config_validation_schema_custom_part(self):
        return yaml.load(
            """
            datasets:
                type: list
                schema:
                    type: dict
                    schema:
                        code:
                            type: string
                            required: True
                        location:
                            type: string
                            regex: "^.+?:.+"
                            required: True
            """
        )

    def load_datasets(self, entity_code_location_string_dict):
        for entity_code_location_string in entity_code_location_string_dict:
            entity_code = entity_code_location_string["code"]
            location_string = entity_code_location_string["location"]
            # remember location string
            self.location_strings[entity_code] = location_string
            # load entities into dataset
            new_data = DatasetManager.load_dataset_from_location_string(
                location_string, {"term": str, "entity_code": str, "parent_terms": str}
            )[0]
            self.dataset = self.dataset.append(new_data)
            # update flashtext
            self.flashtext = KeywordProcessor()
            data_for_flashtext = pd.DataFrame(
                {
                    "against": [
                        "`{}``SN``{}`´".format(row["term"], row["entity_code"])
                        if not row["parent_terms"]
                        else "`{}``PN``{}``{}`´".format(
                            row["term"], row["entity_code"], row["parent_terms"]
                        )
                        for index, row in self.dataset.iterrows()
                    ],
                    "replace": self.dataset["term"],
                }
            )
            dict_for_flashtext = data_for_flashtext.set_index("against").T.to_dict(
                "list"
            )
            self.flashtext.add_keywords_from_dict(dict_for_flashtext)

    def add_named_entity_term_to_dataset(self, term, entity_code, parent_terms):
        new_row = pd.DataFrame(
            {
                "term": [term],
                "entity_code": [entity_code],
                "parent_terms": [parent_terms],
            }
        )
        self.dataset = self.dataset.append(new_row)
        if parent_terms != "":
            self.flashtext.add_keywords_from_dict(
                {"`{}``PN``{}``{}`´".format(term, entity_code, parent_terms): [term]}
            )
        else:
            self.flashtext.add_keywords_from_dict(
                {"`{}``SN``{}`´".format(term, entity_code): [term]}
            )

    def remove_named_entity_term_from_dataset(self, term, entity_code):
        self.dataset = self.dataset[
            ~(
                (self.dataset["term"] == term)
                & (self.dataset["entity_code"] == entity_code)
            )
        ]
        self.flashtext.remove_keyword(term)

    def save_dataset(self, location_string, entity_code):
        # get the named entities with the specified entity code
        filtered_named_entities = self.dataset[
            self.dataset["entity_code"] == entity_code
        ].copy()
        # sort the filtered named entities for convenience
        filtered_named_entities["sort"] = filtered_named_entities["term"].str.lower()
        filtered_named_entities = filtered_named_entities.sort_values(by=["sort"])
        del filtered_named_entities["sort"]
        # save the dataset
        DatasetManager.save_dataset_to_location_string(
            filtered_named_entities, location_string
        )

    def mark_named_entity_term_for_removal(self, term, entity_code):
        if (term, entity_code) not in self.marked_for_removal:
            self.marked_for_removal.append((term, entity_code))

    def reset_marked_for_removal(self):
        self.marked_for_removal = []

    def get_parent_terms_for_named_entity(self, term, entity_code):
        # check if we have corresponding parent terms in the named entities dataset
        dataset_query_result = list(
            self.dataset[
                (self.dataset["entity_code"] == entity_code)
                & (self.dataset["term"] == term)
            ]["parent_terms"]
        )
        if len(dataset_query_result) > 0:
            # we got a row back
            # return either the parent terms or None depending on parent_terms value in dataset
            dataset_query_result = dataset_query_result[0]
            return (
                None
                if dataset_query_result is None or pd.isnull(dataset_query_result)
                else dataset_query_result
            )
        else:
            # no, no parent terms found in dataset
            return None

    def learn_from_annotated_text(self, annotated_text, language):
        # note: the definition of a "term" within this function is a tuple of term and entity code
        # get terms to add/update
        terms_to_add = {}
        parented_terms_to_update = []
        affected_entity_codes = []
        for annotation in extract_annotations_as_generator(
            annotated_text,
            types_to_extract=["standalone_named_entity", "parented_named_entity"],
        ):
            if (
                len(
                    self.dataset[
                        (self.dataset["term"] == annotation["term"])
                        & (self.dataset["entity_code"] == annotation["entity_code"])
                    ]
                )
                == 0
            ):
                # term does not exist yet
                terms_to_add = merge_dict(
                    terms_to_add,
                    {
                        (annotation["term"], annotation["entity_code"]): annotation[
                            "parent_terms"
                        ]
                        if "parent_terms" in annotation
                        else ""
                    },
                )
                affected_entity_codes.append(annotation["entity_code"])
            else:
                # term exists but may need update due to different parent terms
                if "parent_terms" in annotation:
                    currently_stored_parent_terms = list(
                        self.dataset[
                            (self.dataset["term"] == annotation["term"])
                            & (self.dataset["entity_code"] == annotation["entity_code"])
                        ]["parent_terms"]
                    )[0]
                    if currently_stored_parent_terms != annotation["parent_terms"]:
                        # needs update
                        terms_to_add = merge_dict(
                            terms_to_add,
                            {
                                (
                                    annotation["term"],
                                    annotation["entity_code"],
                                ): annotation["parent_terms"]
                                if "parent_terms" in annotation
                                else ""
                            },
                        )
                        parented_terms_to_update.append(
                            (annotation["term"], annotation["entity_code"])
                        )
                        affected_entity_codes.append(annotation["entity_code"])

        # get total terms to remove
        terms_to_remove = []
        for term in self.marked_for_removal:
            if term in terms_to_add:
                continue
            terms_to_remove.append(term)
            affected_entity_codes.append(term[1])
        terms_to_remove.extend(parented_terms_to_update)

        # update key terms dataset (incl. flashtext)
        # remove
        if terms_to_remove:
            for term in terms_to_remove:
                self.remove_named_entity_term_from_dataset(term[0], term[1])
        # add
        if terms_to_add:
            for term in terms_to_add:
                self.add_named_entity_term_to_dataset(
                    term[0], term[1], terms_to_add[term]
                )
        # save
        for affected_entity_code in affected_entity_codes:
            if affected_entity_code in self.location_strings:
                self.save_dataset(
                    self.location_strings[affected_entity_code], affected_entity_code
                )

    def predict_inline_annotations(self, text, language="en-US"):
        return (
            self.flashtext.replace_keywords(text)
            if self.flashtext is not None
            else text
        )
