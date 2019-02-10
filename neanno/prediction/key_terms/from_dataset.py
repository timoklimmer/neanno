import pandas as pd
import yaml
from flashtext import KeywordProcessor

from neanno.prediction.predictor import Predictor
from neanno.utils.dataset import DatasetManager
from neanno.utils.dict import merge_dict
from neanno.utils.text import (
    extract_annotations_as_generator,
    mask_annotations,
    unmask_annotations,
)


class FromDatasetKeyTermsPredictor(Predictor):
    """ Predicts key terms of a text by looking up terms in a dataset."""

    location_string = None
    dataset = pd.DataFrame(columns=["term", "parent_terms"], dtype=str)
    flashtext = None
    key_terms_marked_for_removal = []

    def __init__(self, predictor_config):
        super().__init__(predictor_config)
        self.load_dataset(predictor_config["location"])

    @property
    def config_validation_schema_custom_part(self):
        return yaml.load(
            """
            location:
                type: string
                regex: "^.+?:.+"
                required: True
            """
        )

    def load_dataset(self, location_string):
        # update location_string
        self.location_string = location_string
        # load data
        self.dataset = DatasetManager.load_dataset_from_location_string(
            location_string, {"term": str, "parent_terms": str}
        )[0]
        # setup flashtext for later string replacements
        temp_replace_against_dataset = self.dataset.copy()
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
        self.flashtext = KeywordProcessor()
        self.flashtext.add_keywords_from_dict(temp_replace_against_dataset_as_dict)

    def add_key_term_to_dataset(self, key_term, parent_terms):
        new_row = pd.DataFrame({"term": [key_term], "parent_terms": [parent_terms]})
        self.dataset = self.dataset.append(new_row)
        if parent_terms != "":
            self.flashtext.add_keywords_from_dict(
                {"`{}``PK``{}`´".format(key_term, parent_terms): [key_term]}
            )
        else:
            self.flashtext.add_keywords_from_dict(
                {"`{}``SK`´".format(key_term): [key_term]}
            )

    def remove_key_term_from_dataset(self, key_term):
        self.dataset = self.dataset[self.dataset.term != key_term]
        self.flashtext.remove_keyword(key_term)

    def save_dataset(self, location_string):
        # sort the key terms dataset for convenience
        self.dataset["sort"] = self.dataset["term"].str.lower()
        self.dataset = self.dataset.sort_values(by=["sort"])
        del self.dataset["sort"]
        # save the dataset
        DatasetManager.save_dataset_to_location_string(self.dataset, location_string)

    def mark_key_term_for_removal(self, key_term):
        if key_term not in self.key_terms_marked_for_removal:
            self.key_terms_marked_for_removal.append(key_term)

    def reset_key_terms_marked_for_removal(self):
        self.key_terms_marked_for_removal = []

    def learn_from_annotated_text(self, annotated_text):
        # get terms to add/update
        key_terms_to_add = {}
        parented_terms_to_update = []
        existing_terms_list = list(self.dataset["term"])
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
                        self.dataset[self.dataset["term"] == annotation["term"]][
                            "parent_terms"
                        ]
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
            key_term
            for key_term in self.key_terms_marked_for_removal
            if key_term not in key_terms_to_add
        ]
        key_terms_to_remove.extend(parented_terms_to_update)

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
        self.save_dataset(self.location_string)

    def predict_inline_annotations(self, text, mask_annotations_before_return=False):
        if self.flashtext is not None:
            result = mask_annotations(text)
            result = self.flashtext.replace_keywords(result)
        else:
            result = text
        return (
            mask_annotations(result)
            if mask_annotations_before_return
            else unmask_annotations(result)
        )
