import argparse
import os

import pandas as pd
from neanno.definitions import CategoryDefinition, NamedEntityDefinition

import config


class ConfigurationInitializer:
    """Collects all configuration settings and provides configuration-related objects to neanno."""

    def __init__(self):
        print("Getting configuration...")

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

        config.dataset_source_csv = args.dataset_source_csv
        config.text_column = args.text_column
        config.is_annotated_column = args.is_annotated_column
        config.dataset_target_csv = args.dataset_target_csv
        config.named_entity_defs = args.named_entity_defs
        config.category_defs = args.category_defs
        config.categories_column = args.categories_column
        config.spacy_model_source = args.spacy_model_source
        config.spacy_model_target = args.spacy_model_target

        # TODO: add validation
        # TODO: print config values

        # compute friendly data source names
        config.dataset_source_friendly = os.path.basename(config.dataset_source_csv)
        config.dataset_target_friendly = (
            os.path.basename(config.dataset_target_csv)
            if config.dataset_target_csv is not None
            else None
        )

        # define a method to save the edited dataset
        config.save_callback = (
            lambda df: df.to_csv(config.dataset_target_csv, index=False, header=True)
            if config.dataset_target_csv is not None
            else None
        )

        # load pandas data frame
        print("Loading data frame with texts to annotate...")
        config.dataframe_to_edit = pd.read_csv(config.dataset_source_csv)

        # determine is_named_entities_enabled
        config.is_named_entities_enabled = bool(config.named_entity_defs)

        # compute the named entity definition collection
        config.named_entity_definitions = []
        if config.named_entity_defs:
            default_colors = [
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
            for definition in config.named_entity_defs.split("/"):
                items = definition.split(" ")
                code = items[0]
                shortcut = items[1]
                color = (
                    items[2]
                    if len(items) >= 3
                    else default_colors[index % len(default_colors)]
                )
                config.named_entity_definitions.append(
                    NamedEntityDefinition(code, shortcut, color)
                )
                index += 1

        # determine is_named_entities_enabled
        config.is_categories_enabled = bool(config.category_defs)

        # assemble the category definition collection
        config.category_definitions = []
        if config.category_defs:
            for definition in config.category_defs.split("/"):
                name = definition
                config.category_definitions.append(CategoryDefinition(name))

        # determine is_spacy_enabled
        config.is_spacy_enabled = bool(config.spacy_model_source)
