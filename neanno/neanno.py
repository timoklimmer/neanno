import argparse
import os

import pandas as pd
from neanno import NamedEntityDefinition, annotate_entities


def main():
    parser = argparse.ArgumentParser(
        description="A tool to annotate named entities and train models to recognize them."
    )
    parser.add_argument(
        "--named-entity-defs",
        help='Defines the entities to annotate incl. shortcuts and colors. Eg. "PER Alt+P #ff0000/ORG Alt+O #00ff00/LOC Alt+L". If no color is specified, a default color will be assigned.',
        required=True,
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
        help="Name of the column which contains a flag showing if the text has been annotated. Will be created if it does not exist.",
        required=True,
    )
    parser.add_argument(
        "--dataset-target-csv",
        help="Path to the CSV output file which will contain the annotations. Can be the same as dataset_source_csv.",
        required=True,
    )
    parser.add_argument(
        "--ner-model-source",
        help="Name of the source NER/Spacy model, used as starting point and to recommend labels. If the argument is not specified, no recommendations will be made.",
    )
    parser.add_argument(
        "--ner-model-target",
        help="Directory where the modified, newly trained NER/spacy model is saved. Can only be used if --ner-model-source is used.",
    )
    args = parser.parse_args()

    named_entity_defs = args.named_entity_defs
    dataset_source_csv = args.dataset_source_csv
    text_column = args.text_column
    is_annotated_column = args.is_annotated_column
    dataset_target_csv = args.dataset_target_csv
    ner_model_source = args.ner_model_source
    ner_model_target = args.ner_model_target

    # load pandas data frame
    dataframe_to_edit = pd.read_csv(dataset_source_csv)

    # compute friendly data source names
    dataset_source_friendly = (
        os.path.basename(dataset_source_csv) if dataset_source_csv is not None else None
    )
    dataset_target_friendly = (
        os.path.basename(dataset_target_csv) if dataset_target_csv is not None else None
    )

    # run the annotation UI
    annotate_entities(
        dataframe_to_edit=dataframe_to_edit,
        text_column_name=text_column,
        is_annotated_column_name=is_annotated_column,
        named_entity_defs=named_entity_defs,
        save_callback=lambda df: df.to_csv(dataset_target_csv, index=False, header=True)
        if dataset_target_csv is not None
        else None,
        dataset_source_friendly=dataset_source_friendly,
        dataset_target_friendly=dataset_target_friendly,
        ner_model_source=ner_model_source,
        ner_model_target=ner_model_target
    )
