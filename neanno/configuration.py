import argparse
import os
import re

import config
import pandas as pd
import yaml
from cerberus import Validator
from flashtext import KeywordProcessor
from neanno.colors import DEFAULT_ENTITY_COLORS_PALETTE
from neanno.definitions import (
    AutoSuggestRegex,
    CategoryDefinition,
    NamedEntityDefinition,
)
from neanno.dictutils import QueryDict


class ConfigInit:
    """Collects all configuration settings and provides configuration-related objects to neanno (through config.*)."""

    def __init__(self):
        # specify neanno's args and load/validate the required config file
        config_yaml, parser = ConfigInit.define_args_and_load_config_yaml()
        # derive further configuration objects from specified arguments
        # dataset source-related
        ConfigInit.dataset_source(config_yaml, parser)
        # dataset target-related
        ConfigInit.dataset_target(config_yaml, parser)
        # named entities-related
        ConfigInit.named_entities(config_yaml, parser)
        # categories-related
        ConfigInit.categories(config_yaml, parser)
        # spacy-related
        ConfigInit.spacy(config_yaml, parser)

    def define_args_and_load_config_yaml():
        # define arguments
        parser = argparse.ArgumentParser(
            description="A tool to label and annotate texts and train models.",
            add_help=False,
        )
        required = parser.add_argument_group("required arguments")
        required.add_argument(
            "--config-file",
            help="Points to a config file for neanno. See the example config files (config.yaml) to learn how to write them.",
            required=True,
        )
        help = parser.add_argument_group("help arguments")
        help.add_argument(
            "-h", "--help", action="help", help="show this help message and exit"
        )

        # load and validate config file
        args = parser.parse_args()
        with open(args.config_file, "r") as config_file:
            with open(
                os.path.join(
                    os.path.abspath(os.path.dirname(__file__)),
                    "resources",
                    "config.schema.yaml",
                )
            ) as config_schema_file:
                config_yaml = yaml.load(config_file)
                config_yaml_schema = yaml.load(config_schema_file)
                config_yaml_validator = Validator(config_yaml_schema)
                config_yaml_validator.validate(config_yaml)
                errors = config_yaml_validator.errors
                if errors:
                    parser.error(
                        yaml.dump(errors)
                        + os.linesep
                        + os.linesep
                        + "The given config file does not follow the required schema. See error message(s) above for more details."
                    )

        # return config_yaml and parser (so subsequent methods can issue errors too)
        return (config_yaml, parser)

    def dataset_source(config_yaml, parser):
        print("Loading dataframe with texts to annotate...")
        config.dataset_node = config_yaml["dataset"]
        config.text_column = config.dataset_node["text_column"]
        config.is_annotated_column = config.dataset_node["is_annotated_column"]
        config.dataset_to_edit, config.dataset_source_friendly = ConfigInit.load_dataset(
            config.dataset_node["source"],
            parser,
            [config.text_column],
            "dataset.source",
        )
        config.dataset_to_edit[config.text_column] = config.dataset_to_edit[
            config.text_column
        ].astype(str)

    def dataset_target(config_yaml, parser):
        config.dataset_target_friendly = None
        if "target" in config.dataset_node:
            datasource_spec = config.dataset_node["target"]
            datasource_type = datasource_spec.split(":")[0]
            supported_datasource_types = ["csv"]
            if datasource_type not in supported_datasource_types:
                parser.error(
                    "Parameter 'dataset.target' uses a datasource type '{}' which is not supported.  Ensure that a valid datasource type is specified. Valid datasource types are: {}.".format(
                        datasource_type, ", ".join(supported_datasource_types)
                    )
                )
            getattr(ConfigInit, "dataset_target_" + datasource_type)(
                config_yaml, parser
            )

    def dataset_target_csv(config_yaml, parser):
        dataset_target_csv = config.dataset_node["target"].replace("csv:", "", 1)
        config.dataset_target_friendly = os.path.basename(dataset_target_csv)
        config.save_callback = lambda df: df.to_csv(
            dataset_target_csv, index=False, header=True
        )

    def named_entities(config_yaml, parser):
        config.named_entity_definitions = []
        config.is_named_entities_enabled = "named_entities" in config_yaml
        if config.is_named_entities_enabled:
            config.named_entities_node = config_yaml["named_entities"]
            index = 0
            for definition in config.named_entities_node["definitions"]:
                code = definition["code"]
                shortcut = definition["shortcut"]
                color = (
                    definition["color"]
                    if "color" in definition.keys()
                    else DEFAULT_ENTITY_COLORS_PALETTE[
                        index % len(DEFAULT_ENTITY_COLORS_PALETTE)
                    ]
                )
                config.named_entity_definitions.append(
                    NamedEntityDefinition(code, shortcut, color)
                )
                index += 1
            # load autosuggest dataset
            config.is_autosuggest_entities_enabled = (
                config.is_named_entities_enabled
                and "auto_suggest" in config.named_entities_node
            )
            config.is_autosuggest_entities_by_sources_enabled = False
            config.is_autosuggest_entities_by_regexes_enabled = False
            if config.is_autosuggest_entities_enabled:
                if "sources" in config.named_entities_node["auto_suggest"].keys():
                    config.is_autosuggest_entities_by_sources_enabled = True
                    print("Loading autosuggest dataset(s)...")
                    # combine data from multiple datasets
                    autosuggest_entities_dataset = pd.DataFrame(
                        columns=["term", "entity_code"]
                    )
                    for spec in config.named_entities_node["auto_suggest"]["sources"]:
                        new_data, friendly_dataset_name_never_used = ConfigInit.load_dataset(
                            spec,
                            parser,
                            ["term", "entity_code"],
                            "named_entities.auto_suggest.sources",
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
                    dict_for_flashtext = data_for_flashtext.set_index(
                        "against"
                    ).T.to_dict("list")
                    config.flashtext.add_keywords_from_dict(dict_for_flashtext)

                # provide regexes to config
                config.autosuggest_regexes = []
                if "regexes" in config.named_entities_node["auto_suggest"].keys():
                    config.is_autosuggest_entities_by_regexes_enabled = True
                    for autosuggest_regex in config.named_entities_node["auto_suggest"][
                        "regexes"
                    ]:
                        config.autosuggest_regexes.append(
                            AutoSuggestRegex(
                                autosuggest_regex["entity"],
                                autosuggest_regex["pattern"],
                            )
                        )

    def categories(config_yaml, parser):
        config.category_definitions = []
        config.is_categories_enabled = "categories" in config_yaml.keys()
        if config.is_categories_enabled:
            config.categories_node = config_yaml["categories"]
            config.categories_column = config.categories_node["column"]
            for definition in config.categories_node["definitions"]:
                name = definition["name"]
                config.category_definitions.append(CategoryDefinition(name))
            config.categories_names_list = [
                definition.name for definition in config.category_definitions
            ]
            config.categories_count = len(config.category_definitions)

    def spacy(config_yaml, parser):
        config.is_spacy_enabled = "spacy" in config_yaml.keys()
        if config.is_spacy_enabled:
            config.spacy_model_source = config_yaml["spacy"]["source"]
            if "target" in config_yaml["spacy"].keys():
                config.spacy_model_target = config_yaml["spacy"]["target"]

    def load_dataset(spec, parser, required_columns, parameter=None):
        supported_datasource_types = ["csv"]
        datasource_type = spec.split(":")[0]
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
