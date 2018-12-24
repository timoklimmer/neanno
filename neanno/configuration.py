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
    AutoSuggestKeyTermRegex,
    AutoSuggestEntityRegex,
    CategoryDefinition,
    NamedEntityDefinition,
)
from neanno.dictutils import QueryDict


class ConfigInit:
    """Collects all configuration settings and provides configuration-related objects to neanno (through config.*)."""

    def __init__(self):
        # specify neanno's args and load/validate the required config file
        ConfigInit.define_args_and_load_config_yaml()
        # derive further configuration objects from specified arguments
        # dataset source-related
        ConfigInit.dataset_source()
        # dataset target-related
        ConfigInit.dataset_target()
        # categories-related
        ConfigInit.categories()
        # key terms-related
        ConfigInit.key_terms()
        # named entities-related
        ConfigInit.named_entities()
        # spacy-related
        ConfigInit.spacy()
        # instructions
        ConfigInit.instructions()

    def define_args_and_load_config_yaml():
        # define arguments
        config.parser = argparse.ArgumentParser(
            description="A tool to label and annotate texts and train models.",
            add_help=False,
        )
        required = config.parser.add_argument_group("required arguments")
        required.add_argument(
            "--config-file",
            help="Points to a config file for neanno. See the example config files (config.yaml) to learn how to write them.",
            required=True,
        )
        help = config.parser.add_argument_group("help arguments")
        help.add_argument(
            "-h", "--help", action="help", help="show this help message and exit"
        )

        # load and validate config file
        args = config.parser.parse_args()
        with open(args.config_file, "r") as config_file:
            with open(
                os.path.join(
                    os.path.abspath(os.path.dirname(__file__)),
                    "resources",
                    "config.schema.yaml",
                )
            ) as config_schema_file:
                config.yaml = yaml.load(config_file)
                config_yaml_schema = yaml.load(config_schema_file)
                config_yaml_validator = Validator(config_yaml_schema)
                config_yaml_validator.validate(config.yaml)
                errors = config_yaml_validator.errors
                if errors:
                    config.parser.error(
                        yaml.dump(errors)
                        + os.linesep
                        + os.linesep
                        + "The given config file does not follow the required schema. See error message(s) above for more details."
                    )

    def dataset_source():
        print("Loading dataframe with texts to annotate...")
        config.text_column = ConfigInit.get_config_value("dataset/text_column")
        config.is_annotated_column = ConfigInit.get_config_value(
            "dataset/is_annotated_column"
        )
        config.dataset_to_edit, config.dataset_source_friendly = ConfigInit.load_dataset(
            ConfigInit.get_config_value("dataset/source"),
            [config.text_column],
            "dataset/source",
        )
        config.dataset_to_edit[config.text_column] = config.dataset_to_edit[
            config.text_column
        ].astype(str)

    def dataset_target():
        config.dataset_target_friendly = None
        if ConfigInit.has_config_value("dataset/target"):
            datasource_spec = ConfigInit.get_config_value("dataset/target")
            datasource_type = datasource_spec.split(":")[0]
            supported_datasource_types = ["csv"]
            if datasource_type not in supported_datasource_types:
                config.parser.error(
                    "Parameter 'dataset/target' uses a datasource type '{}' which is not supported.  Ensure that a valid datasource type is specified. Valid datasource types are: {}.".format(
                        datasource_type, ", ".join(supported_datasource_types)
                    )
                )
            getattr(ConfigInit, "dataset_target_" + datasource_type)()

    def dataset_target_csv():
        dataset_target_csv = ConfigInit.get_config_value("dataset/target").replace(
            "csv:", "", 1
        )
        config.dataset_target_friendly = os.path.basename(dataset_target_csv)
        config.save_callback = lambda df: df.to_csv(
            dataset_target_csv, index=False, header=True
        )

    def key_terms():
        config.is_key_terms_enabled = "key_terms" in config.yaml
        config.key_terms_shortcut_mark_anonymous = ConfigInit.get_config_value(
            "key_terms/shortcuts/anonymous", "Alt+1"
        )
        config.key_terms_shortcut_mark_child = ConfigInit.get_config_value(
            "key_terms/shortcuts/child", "Alt+2"
        )
        config.key_terms_backcolor = ConfigInit.get_config_value(
            "key_terms/backcolor", "#333333"
        )
        config.key_terms_forecolor = ConfigInit.get_config_value(
            "key_terms/forecolor", "#50e6ff"
        )
        ConfigInit.key_terms_autosuggest()

    def key_terms_autosuggest():
        # sources
        config.is_autosuggest_key_terms_by_sources = ConfigInit.has_config_value(
            "key_terms/auto_suggest/sources"
        )
        if config.is_autosuggest_key_terms_by_sources:
            print("Loading autosuggest key terms dataset(s)...")
            # combine data from multiple datasets
            autosuggest_key_terms_dataset = pd.DataFrame(
                columns=["term", "parent_terms"]
            )
            for spec in ConfigInit.get_config_value("key_terms/auto_suggest/sources"):
                new_data, friendly_dataset_name_never_used = ConfigInit.load_dataset(
                    spec, ["term", "parent_terms"], "key_terms/auto_suggest/sources"
                )
                new_data = new_data.fillna("")
                new_data = new_data.astype({"term": str, "parent_terms": str})
                autosuggest_key_terms_dataset = autosuggest_key_terms_dataset.append(
                    new_data
                )
            # setup flashtext for later string replacements
            autosuggest_key_terms_dataset["replace"] = autosuggest_key_terms_dataset[
                "term"
            ]
            autosuggest_key_terms_dataset["against"] = autosuggest_key_terms_dataset[
                "replace"
            ]
            autosuggest_key_terms_dataset.loc[
                autosuggest_key_terms_dataset["parent_terms"] != "", "against"
            ] = (
                "("
                + autosuggest_key_terms_dataset["term"]
                + "|PK "
                + autosuggest_key_terms_dataset["parent_terms"]
                + ")"
            )
            autosuggest_key_terms_dataset.loc[
                autosuggest_key_terms_dataset["parent_terms"] == "", "against"
            ] = ("(" + autosuggest_key_terms_dataset["term"] + "|SK)")
            autosuggest_key_terms_dataset = autosuggest_key_terms_dataset[
                ["replace", "against"]
            ]
            autosuggest_key_terms_dataset = autosuggest_key_terms_dataset.set_index(
                "against"
            ).T.to_dict("list")
            config.key_terms_autosuggest_flashtext = KeywordProcessor()
            config.key_terms_autosuggest_flashtext.add_keywords_from_dict(
                autosuggest_key_terms_dataset
            )

        # regexes
        config.key_terms_autosuggest_regexes = []
        config.is_autosuggest_key_terms_by_regexes = ConfigInit.has_config_value(
            "key_terms/auto_suggest/regexes"
        )
        if config.is_autosuggest_key_terms_by_regexes:
            for autosuggest_regex in ConfigInit.get_config_value(
                "key_terms/auto_suggest/regexes"
            ):
                config.key_terms_autosuggest_regexes.append(
                    AutoSuggestKeyTermRegex(
                        autosuggest_regex["pattern"],
                        autosuggest_regex["parent_terms"]
                        if "parent_terms" in autosuggest_regex
                        else None,
                    )
                )

    def named_entities():
        config.named_entity_definitions = []
        config.is_named_entities_enabled = "named_entities" in config.yaml
        if config.is_named_entities_enabled:
            ConfigInit.named_entities_definitions()
            ConfigInit.named_entities_autosuggest()

    def named_entities_definitions():
        index = 0
        for definition in ConfigInit.get_config_value("named_entities/definitions"):
            code = definition["code"]
            shortcut = definition["shortcut"]
            maincolor = (
                definition["maincolor"]
                if "maincolor" in definition
                else DEFAULT_ENTITY_COLORS_PALETTE[
                    index % len(DEFAULT_ENTITY_COLORS_PALETTE)
                ][0]
            )
            backcolor = (
                definition["backcolor"]
                if "backcolor" in definition
                else DEFAULT_ENTITY_COLORS_PALETTE[
                    index % len(DEFAULT_ENTITY_COLORS_PALETTE)
                ][1]
            )
            forecolor = (
                definition["forecolor"]
                if "forecolor" in definition
                else DEFAULT_ENTITY_COLORS_PALETTE[
                    index % len(DEFAULT_ENTITY_COLORS_PALETTE)
                ][2]
            )
            config.named_entity_definitions.append(
                NamedEntityDefinition(code, shortcut, maincolor, backcolor, forecolor)
            )
            index += 1

    def named_entities_autosuggest():
        # sources
        config.is_autosuggest_entities_by_sources = ConfigInit.has_config_value(
            "named_entities/auto_suggest/sources"
        )
        if config.is_autosuggest_entities_by_sources:
            print("Loading autosuggest entities dataset(s)...")
            # combine data from multiple datasets
            autosuggest_entities_dataset = pd.DataFrame(columns=["term", "entity_code"])
            for spec in ConfigInit.get_config_value(
                "named_entities/auto_suggest/sources"
            ):
                new_data, friendly_dataset_name_never_used = ConfigInit.load_dataset(
                    spec, ["term", "entity_code"], "named_entities/auto_suggest/sources"
                )
                new_data = new_data.astype({"term": str, "entity_code": str})
                autosuggest_entities_dataset = autosuggest_entities_dataset.append(
                    new_data
                )
            # setup flashtext for later string replacements
            config.named_entities_autosuggest_flashtext = KeywordProcessor()
            data_for_flashtext = pd.DataFrame(
                "("
                + autosuggest_entities_dataset["term"]
                + "|NE "
                + autosuggest_entities_dataset["entity_code"]
                + ")"
            )
            data_for_flashtext["replace"] = autosuggest_entities_dataset["term"]
            data_for_flashtext.columns = ["against", "replace"]
            dict_for_flashtext = data_for_flashtext.set_index("against").T.to_dict(
                "list"
            )
            config.named_entities_autosuggest_flashtext.add_keywords_from_dict(
                dict_for_flashtext
            )

        # regexes
        config.named_entities_autosuggest_regexes = []
        config.is_autosuggest_entities_by_regexes = ConfigInit.has_config_value(
            "named_entities/auto_suggest/regexes"
        )
        if config.is_autosuggest_entities_by_regexes:
            for autosuggest_regex in ConfigInit.get_config_value(
                "named_entities/auto_suggest/regexes"
            ):
                config.named_entities_autosuggest_regexes.append(
                    AutoSuggestEntityRegex(
                        autosuggest_regex["entity"], autosuggest_regex["pattern"]
                    )
                )

    def categories():
        config.category_definitions = []
        config.is_categories_enabled = "categories" in config.yaml
        if config.is_categories_enabled:
            config.categories_column = ConfigInit.get_config_value("categories/column")
            for definition in ConfigInit.get_config_value("categories/definitions"):
                name = definition["name"]
                config.category_definitions.append(CategoryDefinition(name))
            config.categories_names_list = [
                definition.name for definition in config.category_definitions
            ]
            config.categories_count = len(config.category_definitions)

    def spacy():
        config.is_spacy_enabled = "spacy" in config.yaml
        config.spacy_model_source = ConfigInit.get_config_value("spacy/source")
        config.spacy_model_target = ConfigInit.get_config_value("spacy/target")

    def instructions():
        config.has_instructions = "instructions" in config.yaml
        config.instructions = ConfigInit.get_config_value("instructions")

    def load_dataset(spec, required_columns, parameter=None):
        supported_datasource_types = ["csv"]
        datasource_type = spec.split(":")[0]
        if datasource_type not in supported_datasource_types:
            config.parser.error(
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
            spec, required_columns, parameter_hint
        )

    def load_dataset_csv(spec, required_columns, parameter_hint):
        file_to_load = spec.replace("csv:", "", 1)
        if not os.path.isfile(file_to_load):
            config.parser.error(
                "The file '{}'{} does not exist. Ensure that you specify a file which exists.".format(
                    file_to_load, parameter_hint
                )
            )
        result = pd.read_csv(file_to_load)
        if not pd.Series(required_columns).isin(result.columns).all():
            config.parser.error(
                "A dataset{} does not return a dataset with the expected columns. Ensure that the dataset includes the following columns (case-sensitive): {}.".format(
                    parameter_hint, ", ".join(required_columns)
                )
            )
        friendly_dataset_name = os.path.basename(file_to_load)
        return (result, friendly_dataset_name)

    def get_config_value(path, default=None):
        candidate = QueryDict(config.yaml).get(path)
        return candidate if candidate is not None else default

    def has_config_value(path):
        return ConfigInit.get_config_value(path) is not None
