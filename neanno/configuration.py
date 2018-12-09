import argparse
import os

import pandas as pd
from neanno.definitions import CategoryDefinition, NamedEntityDefinition

import config


class ConfigurationInitializer:
    """Collects all configuration settings and provides configuration-related objects to neanno."""

    def __init__(self):
        # specify and parse arguments
        parser = argparse.ArgumentParser(
            description="A tool to annotate texts and train models.", add_help=False
        )
        required = parser.add_argument_group("required arguments")
        required.add_argument(
            "--dataset-source",
            help='Points to a dataset with the data to annotate. Needs different prefixes depending on data source type. Eg. "csv:sample_data/sample_data.csv" uses the data from the sample_data/sample_data.csv file.',
            required=True,
        )
        required.add_argument(
            "--text-column",
            help="Name of the column which contains the texts to annotate.",
            required=True,
        )
        required.add_argument(
            "--is-annotated-column",
            help="Name of the column which contains a flag showing if the text has been annotated. Will be created if needed and does not exist.",
            required=True,
        )
        required.add_argument(
            "--dataset-target",
            help='Points to a dataset which will contain the annotations/labels. Needs different prefixes depending on data source type. Eg. "csv:sample_data/sample_data.annotated.csv" will write to the sample_data/sample_data.annotated.csv file.',
            required=True,
        )
        optional = parser.add_argument_group("optional arguments")
        optional.add_argument(
            "--category-defs",
            help='Defines the categories the texts can have. Eg. "Inquiry/Issue/Information"',
        )
        optional.add_argument(
            "--categories-column",
            help="Name of the column which contains the categories of the text. Will be created if needed and does not exist.",
        )
        optional.add_argument(
            "--named-entity-defs",
            help='Defines the entities to annotate incl. shortcuts and colors. Eg. "PER Alt+P #ff0000/ORG Alt+O #00ff00/LOC Alt+L". If no color is specified, a default color will be assigned.',
        )
        optional.add_argument(
            "--spacy-model-source",
            help="Name of the source NER/Spacy model, used as starting point and to recommend labels. If the argument is not specified, no recommendations will be made.",
        )
        optional.add_argument(
            "--spacy-model-target",
            help="Directory where the modified, newly trained NER/spacy model is saved. Can only be used if --spacy-model-source is used.",
        )
        help = parser.add_argument_group("help arguments")
        help.add_argument(
            "-h", "--help", action="help", help="show this help message and exit"
        )
        args = parser.parse_args()
        config.dataset_source = args.dataset_source
        config.text_column = args.text_column
        config.is_annotated_column = args.is_annotated_column
        config.dataset_target = args.dataset_target
        config.named_entity_defs = args.named_entity_defs
        config.category_defs = args.category_defs
        config.categories_column = args.categories_column
        config.spacy_model_source = args.spacy_model_source
        config.spacy_model_target = args.spacy_model_target

        # TODO: add validation

        # derive further configuration objects from specified arguments
        # dataset source-related
        print("Loading data frame with texts to annotate...")
        getattr(ConfigurationInitializer, "dataset_source_" + config.dataset_source.split(":")[0])()
        # dataset target-related
        getattr(ConfigurationInitializer, "dataset_target_" + config.dataset_target.split(":")[0])()
        # named entities-related
        ConfigurationInitializer.named_entities()
        # categories-related
        ConfigurationInitializer.categories()
        # spacy-related
        ConfigurationInitializer.spacy()

    def dataset_source_csv():
        file_to_load = config.dataset_source.replace("csv:", "", 1)
        config.dataset_source_friendly = os.path.basename(file_to_load)
        config.dataframe_to_edit = pd.read_csv(file_to_load)
    
    def dataset_target_csv():
        config.dataset_target_csv = config.dataset_target.replace("csv:", "", 1)
        config.dataset_target_friendly = os.path.basename(config.dataset_target_csv)
        config.save_callback = lambda df: df.to_csv(
            config.dataset_target_csv, index=False, header=True
        )

    def named_entities():
        config.is_named_entities_enabled = bool(config.named_entity_defs)
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

    def categories():
        config.is_categories_enabled = bool(config.category_defs)
        config.category_definitions = []
        if config.category_defs:
            for definition in config.category_defs.split("/"):
                name = definition
                config.category_definitions.append(CategoryDefinition(name))

    def spacy():
        config.is_spacy_enabled = bool(config.spacy_model_source)
