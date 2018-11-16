import argparse
import os

import pandas as pd
from neanno import NamedEntityDefinition, annotate_entities


def main():
    parser = argparse.ArgumentParser(
        description="Yet another named entity annotation tool."
    )
    parser.add_argument(
        "--dataset_source_csv",
        "-s",
        help="Path to a CSV file containing the data to annotate.",
    )
    parser.add_argument(
        "--dataset_target_csv",
        "-t",
        help="Path to the CSV output file which will contain the annotations. Can be the same as dataset_source_csv.",
    )
    parser.add_argument(
        "--text_column_name",
        "-c",
        help="Name of the column containing the texts to annotate.",
    )
    parser.add_argument(
        "--is_annotated_column_name",
        "-i",
        help="Name of the column containing a flag if the text has been annotated.",
    )
    parser.add_argument(
        "--named_entity_defs",
        "-n",
        help='Defines the entities available for annotation incl. shortcuts. Eg. "BLUE Alt+B/RED Alt+R/GREEN Alt+G"',
    )
    parser.add_argument(
        "--ner_model_source", "-m", help="Name of the source NER/Spacy model."
    )
    parser.add_argument(
        "--ner_model_target",
        "-o",
        help="Name under which the modified NER/spacy model is to be trained.",
    )
    args = parser.parse_args()

    dataset_source_csv = args.dataset_source_csv  # "sample_texts.csv"
    dataset_target_csv = args.dataset_target_csv  # "sample_texts.annotated.csv"
    text_column_name = args.text_column_name  # "text"
    is_annotated_column_name = args.is_annotated_column_name  # "is_annotated"
    named_entity_defs_string = (
        args.named_entity_defs
    )  # "BLUE Alt+B/RED Alt+R/GREEN Alt+G"
    ner_model_source_spacy = args.ner_model_source  # en_core_web_sm
    ner_model_target_spacy = args.ner_model_target  # en_my_own

    # load pandas data frame
    dataframe_to_edit = pd.read_csv(dataset_source_csv)

    # declare the named entities to annotate
    named_entity_definitions = []
    colors = [
        "#153465",
        "#67160e",
        "#135714",
        "#341b4d",
        "#b45c18",
        "#b0984f",
        "#838b83",
        "#2f4f4f",
    ]
    index = 0
    for definition in named_entity_defs_string.split("/"):
        items = definition.split(" ")
        code = items[0]
        shortcut = items[1]
        color = colors[index % len(colors)]
        named_entity_definitions.append(NamedEntityDefinition(code, shortcut, color))
        index += 1

    # run the annotation UI
    dataset_source_friendly = os.path.basename(dataset_source_csv)
    dataset_target_friendly = os.path.basename(dataset_target_csv)
    annotate_entities(
        dataframe_to_edit=dataframe_to_edit,
        text_column_name=text_column_name,
        is_annotated_column_name=is_annotated_column_name,
        named_entity_definitions=named_entity_definitions,
        save_callback=lambda df: df.to_csv(dataset_target_csv, index=False, header=True)
        if dataset_target_csv is not None
        else None,
        ner_model_source=ner_model_source_spacy,
        ner_model_target=ner_model_target_spacy,
        dataset_source_friendly=dataset_source_friendly,
        dataset_target_friendly=dataset_target_friendly,
    )
