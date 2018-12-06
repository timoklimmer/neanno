import argparse
import os
import sys

import pandas as pd

from neanno import ask_for_annotations


def main():
    try:
        print("Starting neanno...")

        parser = argparse.ArgumentParser(
            description="A tool to annotate texts and train models."
        )
        parser.add_argument(
            "--dataset-source-csv",
            help="Path to a CSV file containing the data to annotate.",
            required=True,
        )
        parser.add_argument(
            "--text-column",
            help="Name of the column which contains the texts to annotate.",
            required=True,
        )
        parser.add_argument(
            "--is-annotated-column",
            help="Name of the column which contains a flag showing if the text has been annotated. Will be created if needed and does not exist.",
            required=True,
        )
        parser.add_argument(
            "--dataset-target-csv",
            help="Path to the CSV output file which will contain the annotations. Can be the same as dataset_source_csv.",
            required=True,
        )
        parser.add_argument(
            "--category-defs",
            help='Defines the categories the texts can have. Eg. "Inquiry/Issue/Information"',
        )
        parser.add_argument(
            "--categories-column",
            help='Name of the column which contains the categories of the text. Will be created if needed and does not exist."',
        )
        parser.add_argument(
            "--named-entity-defs",
            help='Defines the entities to annotate incl. shortcuts and colors. Eg. "PER Alt+P #ff0000/ORG Alt+O #00ff00/LOC Alt+L". If no color is specified, a default color will be assigned.',
        )
        parser.add_argument(
            "--spacy-model-source",
            help="Name of the source NER/Spacy model, used as starting point and to recommend labels. If the argument is not specified, no recommendations will be made.",
        )
        parser.add_argument(
            "--spacy-model-target",
            help="Directory where the modified, newly trained NER/spacy model is saved. Can only be used if --spacy-model-source is used.",
        )
        args = parser.parse_args()

        # get configuration
        print("Getting configuration...")
        dataset_source_csv = args.dataset_source_csv
        text_column = args.text_column
        is_annotated_column = args.is_annotated_column
        dataset_target_csv = args.dataset_target_csv
        named_entity_defs = args.named_entity_defs
        category_defs = args.category_defs
        categories_column = args.categories_column
        spacy_model_source = args.spacy_model_source
        spacy_model_target = args.spacy_model_target

        # compute friendly data source names
        dataset_source_friendly = os.path.basename(dataset_source_csv)
        dataset_target_friendly = (
            os.path.basename(dataset_target_csv)
            if dataset_target_csv is not None
            else None
        )

        # define a method to save the edited dataset
        save_callback = (
            lambda df: df.to_csv(dataset_target_csv, index=False, header=True)
            if dataset_target_csv is not None
            else None
        )

        # load pandas data frame
        print("Loading data frame with texts to annotate...")
        dataframe_to_edit = pd.read_csv(dataset_source_csv)

        # run the annotation UI
        print("Showing annotation dialog...")
        ask_for_annotations(
            dataframe_to_edit=dataframe_to_edit,
            dataset_source_friendly=dataset_source_friendly,
            text_column=text_column,
            is_annotated_column=is_annotated_column,
            named_entity_defs=named_entity_defs,
            category_defs=category_defs,
            categories_column=categories_column,
            save_callback=save_callback,
            dataset_target_friendly=dataset_target_friendly,
            spacy_model_source=spacy_model_source,
            spacy_model_target=spacy_model_target,
        )
    except:
        print("An unhandled error occured: ", sys.exc_info()[0])
        raise
