import argparse
import os
import re

import config
import pandas as pd
from neanno.definitions import CategoryDefinition, NamedEntityDefinition


class ConfigInit:
    """Collects all configuration settings and provides configuration-related objects to neanno."""

    def __init__(self):
        # specify and parse arguments
        parser = ConfigInit.specify_and_parse_arguments()

        # derive further configuration objects from specified arguments
        # dataset source-related
        ConfigInit.dataset_source(parser)
        # dataset target-related
        ConfigInit.dataset_target(parser)
        # named entities-related
        ConfigInit.named_entities(parser)
        # categories-related
        ConfigInit.categories(parser)
        # spacy-related
        ConfigInit.spacy(parser)

    def specify_and_parse_arguments():
        parser = argparse.ArgumentParser(
            description="A tool to label and annotate texts and train models.",
            add_help=False,
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
        return parser

    def dataset_source(parser):
        # note: depending on the specified prefix = data source type, this will run the respective functions below, eg. dataset_source_csv(...)
        print("Loading data frame with texts to annotate...")
        datasource_type = config.dataset_source.split(":")[0]
        supported_datasource_types = ["csv"]
        if datasource_type not in supported_datasource_types:
            parser.error(
                "Parameter '--dataset-source' uses a datasource type '{}' which is not supported.".format(
                    datasource_type
                )
            )
        getattr(ConfigInit, "dataset_source_" + datasource_type)(parser)

    def dataset_source_csv(parser):
        file_to_load = config.dataset_source.replace("csv:", "", 1)
        if not os.path.isfile(file_to_load):
            parser.error(
                "The file '{}' specified in parameter '--dataset-source' does not exist.".format(
                    file_to_load
                )
            )
        config.dataset_source_friendly = os.path.basename(file_to_load)
        config.dataframe_to_edit = pd.read_csv(file_to_load)

    def dataset_target(parser):
        # note: depending on the specified prefix = data source type, this will run the respective functions below, eg. dataset_target_csv(...)
        datasource_type = config.dataset_source.split(":")[0]
        supported_datasource_types = ["csv"]
        if datasource_type not in supported_datasource_types:
            parser.error(
                "Parameter '--dataset-target' uses a datasource type '{}' which is not supported.".format(
                    datasource_type
                )
            )
        getattr(ConfigInit, "dataset_target_" + datasource_type)(parser)

    def dataset_target_csv(parser):
        dataset_target_csv = config.dataset_target.replace("csv:", "", 1)
        config.dataset_target_friendly = os.path.basename(dataset_target_csv)
        config.save_callback = lambda df: df.to_csv(
            dataset_target_csv, index=False, header=True
        )

    def named_entities(parser):
        config.named_entity_definitions = []
        config.is_named_entities_enabled = bool(config.named_entity_defs)
        if config.is_named_entities_enabled:
            # validation
            # ensure named_entity_defs has the expected format
            if not re.match(
                "(?i)^[A-Z0-9_]+ Alt\+[A-Z0-9]+( #[A-F0-9]{6}\b| [A-Z]+)?(/[A-Z0-9_]+ Alt\+[A-Z0-9]+( #[A-F0-9]{6}\b| [A-Z]+)?)*$",
                config.named_entity_defs,
            ):
                parser.error(
                    "The value of parameter '--named-entity-defs' = '{}' does not follow the expected format.".format(
                        config.named_entity_defs
                    )
                )
            # assemble named entity definitions
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
                if (
                    len(
                        [
                            named_entity_definition.code
                            for named_entity_definition in config.named_entity_definitions
                            if named_entity_definition.code == code
                        ]
                    )
                    > 0
                ):
                    parser.error(
                        "Entity code '{}' is specified multiple times in parameter '--named-entity-defs'.".format(
                            code
                        )
                    )
                if (
                    len(
                        [
                            named_entity_definition.key_sequence
                            for named_entity_definition in config.named_entity_definitions
                            if named_entity_definition.key_sequence == shortcut
                        ]
                    )
                    > 0
                ):
                    parser.error(
                        "Shortcut '{}' is specified multiple times in parameter '--named-entity-defs'.".format(
                            shortcut
                        )
                    )
                config.named_entity_definitions.append(
                    NamedEntityDefinition(code, shortcut, color)
                )
                index += 1

    def categories(parser):
        config.category_definitions = []
        config.is_categories_enabled = bool(config.category_defs)
        if config.is_categories_enabled:
            # validation
            # ensure --categories-column is set if --category-defs is used
            if not config.categories_column:
                parser.error(
                    "Parameter '--categories-column' is required if parameter '--category-defs' is used."
                )
            # assemble category definitions
            for definition in config.category_defs.split("/"):
                name = definition
                config.category_definitions.append(CategoryDefinition(name))

    def spacy(parser):
        # ensure that --spacy-model-target is not specified without --spacy-model-source
        if config.spacy_model_target and not config.spacy_model_source:
            parser.error(
                "Parameter '--spacy-model-target' must not be used without parameter '--spacy_model_source'."
            )
        # enable spacy
        config.is_spacy_enabled = bool(config.spacy_model_source)
