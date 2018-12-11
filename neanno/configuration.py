import argparse
import os
import re

import config
import pandas as pd
from flashtext import KeywordProcessor

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
            help="Points to a dataset which will contain the annotations/labels. Uses the same datasource type scheme as --dataset-source (supported datasources may differ, however).",
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
            "--autosuggest-entities-sources",
            help="Points to a dataset which contains a term and entity_code column. The data provided will then be used to autosuggest entities if strings equal. Uses the same datasource type scheme as --dataset-source (supported datasources may differ, however).",
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
        config.autosuggest_entities_sources = args.autosuggest_entities_sources
        config.category_defs = args.category_defs
        config.categories_column = args.categories_column
        config.spacy_model_source = args.spacy_model_source
        config.spacy_model_target = args.spacy_model_target
        return parser

    def dataset_source(parser):
        # note: depending on the specified prefix = data source type, this will run the respective functions below, eg. dataset_source_csv(...)
        print("Loading dataframe with texts to annotate...")
        config.dataframe_to_edit, config.dataset_source_friendly = ConfigInit.load_dataset(
            config.dataset_source, parser, [config.text_column], "--dataset-source"
        )

    def dataset_target(parser):
        # note: depending on the specified prefix = data source type, this will run the respective functions below, eg. dataset_target_csv(...)
        datasource_type = config.dataset_source.split(":")[0]
        supported_datasource_types = ["csv"]
        if datasource_type not in supported_datasource_types:
            parser.error(
                "Parameter '--dataset-target' uses a datasource type '{}' which is not supported.  Ensure that a valid datasource type is specified. Valid datasource types are: {}.".format(
                    datasource_type, ", ".join(supported_datasource_types)
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
        if config.spacy_model_target and not config.spacy_model_source:
            parser.error(
                "Parameter '--autosuggest-entities-entities' must not be used without parameter '--named-entity-defs'."
            )
        config.named_entity_definitions = []
        config.is_named_entities_enabled = bool(config.named_entity_defs)
        config.is_autosuggest_entities_enabled = bool(
            config.autosuggest_entities_sources
        )
        if config.is_named_entities_enabled:
            # ensure named_entity_defs has the expected format
            if not re.match(
                "(?i)^[A-Z0-9_]+ [A-Z0-9+]+( #[A-F0-9]{6}| [A-Z]+)?(/[A-Z0-9_]+ [A-Z0-9+]+( #[A-F0-9]{6}| [A-Z]+)?)*$",
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
            # load autosuggest dataset
            if config.is_autosuggest_entities_enabled:
                print("Loading autosuggest dataset...")
                # combine data from multiple datasets
                autosuggest_entities_dataset = pd.DataFrame(
                    columns=["term", "entity_code"]
                )
                for spec in config.autosuggest_entities_sources.split("//"):
                    new_data, friendly_dataset_name_never_used = ConfigInit.load_dataset(
                        spec,
                        parser,
                        ["term", "entity_code"],
                        "--autosuggest-entities-sources",
                    )
                    autosuggest_entities_dataset = autosuggest_entities_dataset.append(
                        new_data
                    )
                # setup flashtext for later string replacements
                config.flashtext = KeywordProcessor()
                data_for_flashtext = pd.DataFrame(
                    "("
                    + autosuggest_entities_dataset["term"]
                    + "| "
                    + autosuggest_entities_dataset["entity_code"]
                    + ")"
                )
                data_for_flashtext["replace"] = autosuggest_entities_dataset["term"]
                data_for_flashtext.columns = ["against", "replace"]
                dict_for_flashtext = data_for_flashtext.set_index("against").T.to_dict(
                    "list"
                )
                config.flashtext.add_keywords_from_dict(dict_for_flashtext)

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

    def load_dataset(spec, parser, required_columns, parameter=None):
        supported_datasource_types = ["csv"]
        datasource_type = config.dataset_source.split(":")[0]
        if datasource_type not in supported_datasource_types:
            parser.error(
                "Parameter '{}' uses a datasource type '{}' which is not supported. Ensure that a valid datasource type is specified. Valid datasource types are: {}.".format(
                    parameter, datasource_type, ", ".join(supported_datasource_types)
                )
            )
        parameter_hint = (
            " specified in parameter '{}'".format(parameter)
            if parameter is not None
            else ""
        )
        return getattr(ConfigInit, "load_dataset_" + datasource_type)(
            spec, parser, required_columns, parameter_hint
        )

    def load_dataset_csv(spec, parser, required_columns, parameter_hint):
        file_to_load = spec.replace("csv:", "", 1)
        if not os.path.isfile(file_to_load):
            parser.error(
                "The file '{}'{} does not exist. Ensure that you specify a file which exists.".format(
                    file_to_load, parameter_hint
                )
            )
        result = pd.read_csv(file_to_load)
        if not pd.Series(required_columns).isin(result.columns).all():
            parser.error(
                "A dataset{} does not return a dataset with the expected columns. Ensure that the dataset includes the following columns (case-sensitive): {}.".format(
                    parameter_hint, ", ".join(required_columns)
                )
            )
        friendly_dataset_name = os.path.basename(file_to_load)
        return (result, friendly_dataset_name)

