import argparse
import os
import re

import config
import pandas as pd
import yaml
from cerberus import Validator
from flashtext import KeywordProcessor

from neanno.autosuggest.autosuggester import AnnotationSuggester
from neanno.autosuggest.definitions import KeyTermRegex, NamedEntityRegex
from neanno.configuration.colors import DEFAULT_ENTITY_COLORS_PALETTE
from neanno.configuration.definitions import CategoryDefinition, NamedEntityDefinition
from neanno.utils.dataset import DatasetLocation, DatasetManager
from neanno.utils.dict import QueryDict, merge_dict
from neanno.utils.text import extract_annotations_as_generator


class ConfigManager:
    """Collects all configuration settings and provides configuration-related objects to neanno (through config.*)."""

    key_terms_marked_for_removal = []

    def __init__(self):
        # specify neanno's args and load/validate the required config file
        ConfigManager.define_args_and_load_config_yaml()
        # instantiate annotation suggester (setup/population will be done below)
        config.annotationsuggester = AnnotationSuggester()
        # derive further configuration objects from specified arguments
        # dataset source-related
        ConfigManager.dataset_source()
        # dataset target-related
        ConfigManager.dataset_target()
        # categories-related
        ConfigManager.categories()
        # key terms-related
        ConfigManager.key_terms()
        # named entities-related
        ConfigManager.named_entities()
        # spacy-related
        ConfigManager.spacy()
        # instructions
        ConfigManager.instructions()

    def define_args_and_load_config_yaml():
        # define arguments
        config.parser = argparse.ArgumentParser(
            description="A tool to label and annotate texts and train models.",
            add_help=False,
        )
        required = config.parser.add_argument_group("required arguments")
        required.add_argument(
            "--config-file",
            help="Points to a config file for neanno. See the airline_tickets.config.yaml file in samples/airline_tickets to learn how to write neanno config files.",
            required=True,
        )
        help = config.parser.add_argument_group("help arguments")
        help.add_argument(
            "-h", "--help", action="help", help="show this help message and exit"
        )

        # load and validate config file
        args = config.parser.parse_args()
        print("Using config file '{}'...".format(args.config_file))
        print("")
        with open(args.config_file, "r") as config_file:
            with open(
                os.path.join(
                    os.path.abspath(os.path.dirname(__file__)),
                    "../resources",
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
                        + "The given config file does not follow the required schema (from file config.schema.yaml). See error message(s) above for more details."
                    )

    def dataset_source():
        print("Loading dataframe with texts to annotate...")
        config.text_column = ConfigManager.get_config_value("dataset/text_column")
        config.is_annotated_column = ConfigManager.get_config_value(
            "dataset/is_annotated_column"
        )
        config.dataset_to_edit, config.dataset_source_friendly = DatasetManager.load_dataset_from_location_string(
            ConfigManager.get_config_value("dataset/source"),
            {config.text_column: str},
            "dataset/source",
        )

    def dataset_target():
        config.dataset_target_friendly = None
        if ConfigManager.has_config_value("dataset/target"):
            dataset_location = DatasetLocation(
                ConfigManager.get_config_value("dataset/target")
            )
            getattr(ConfigManager, "dataset_target_{}".format(dataset_location.type))(
                dataset_location
            )

    def dataset_target_csv(dataset_location):
        config.dataset_target_friendly = os.path.basename(dataset_location.path)
        config.save_callback = lambda df: DatasetManager.save_dataset_to_csv(
            df, dataset_location.path
        )

    def key_terms():
        config.is_key_terms_enabled = "key_terms" in config.yaml
        if config.is_key_terms_enabled:
            config.key_terms_shortcut_mark_standalone = ConfigManager.get_config_value(
                "key_terms/shortcuts/standalone", "Alt+1"
            )
            config.key_terms_shortcut_mark_parented = ConfigManager.get_config_value(
                "key_terms/shortcuts/parented", "Alt+2"
            )
            config.key_terms_backcolor = ConfigManager.get_config_value(
                "key_terms/backcolor", "#333333"
            )
            config.key_terms_forecolor = ConfigManager.get_config_value(
                "key_terms/forecolor", "#50e6ff"
            )
            ConfigManager.key_terms_autosuggest()

    def key_terms_autosuggest():
        # dataset
        key_terms_dataset_location_path = "key_terms/auto_suggest/dataset/location"
        if ConfigManager.has_config_value(key_terms_dataset_location_path):
            print("Loading autosuggest key terms dataset...")
            config.annotationsuggester.load_key_terms_dataset(
                ConfigManager.get_config_value(key_terms_dataset_location_path)
            )

        # regexes
        key_terms_regexes_path = "key_terms/auto_suggest/regexes"
        if ConfigManager.has_config_value(key_terms_regexes_path):
            print("Loading autosuggest key terms regex patterns...")
            for key_term_regex in ConfigManager.get_config_value(
                key_terms_regexes_path
            ):
                config.annotationsuggester.add_key_term_regex(
                    key_term_regex["name"],
                    key_term_regex["pattern"],
                    key_term_regex["parent_terms"]
                    if "parent_terms" in key_term_regex
                    else None,
                )

    def named_entities():
        config.named_entity_definitions = []
        config.is_named_entities_enabled = "named_entities" in config.yaml
        if config.is_named_entities_enabled:
            ConfigManager.named_entities_definitions()
            ConfigManager.named_entities_autosuggest()

    def named_entities_definitions():
        index = 0
        config.named_entity_codes = []
        for definition in ConfigManager.get_config_value("named_entities/definitions"):
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
            config.named_entity_codes.append(code)
            index += 1

    def named_entities_autosuggest():
        # dataset
        named_entities_datasets_path = "named_entities/auto_suggest/datasets"
        if ConfigManager.has_config_value(named_entities_datasets_path):
            print("Loading autosuggest named entities dataset(s)...")
            config.annotationsuggester.load_named_entity_datasets(
                ConfigManager.get_config_value(named_entities_datasets_path)
            )

        # regexes
        named_entities_regexes_path = "named_entities/auto_suggest/regexes"
        if ConfigManager.has_config_value(named_entities_regexes_path):
            print("Loading autosuggest named entities regex patterns...")
            for named_entity_regex in ConfigManager.get_config_value(
                named_entities_regexes_path
            ):
                config.annotationsuggester.add_named_entity_regex(
                    named_entity_regex["entity"],
                    named_entity_regex["pattern"],
                    named_entity_regex["parent_terms"]
                    if "parent_terms" in named_entity_regex
                    else None,
                )

    def categories():
        config.category_definitions = []
        config.is_categories_enabled = "categories" in config.yaml
        if config.is_categories_enabled:
            config.categories_column = ConfigManager.get_config_value(
                "categories/column"
            )
            for definition in ConfigManager.get_config_value("categories/definitions"):
                name = definition["name"]
                config.category_definitions.append(CategoryDefinition(name))
            config.categories_names_list = [
                definition.name for definition in config.category_definitions
            ]
            config.categories_count = len(config.category_definitions)

    def spacy():
        config.is_spacy_enabled = "spacy" in config.yaml
        config.spacy_model_source = ConfigManager.get_config_value("spacy/source")
        config.spacy_model_target = ConfigManager.get_config_value("spacy/target")

    def instructions():
        config.has_instructions = "instructions" in config.yaml
        config.instructions = ConfigManager.get_config_value("instructions")

    def get_config_value(path, default=None):
        candidate = QueryDict(config.yaml).get(path)
        return candidate if candidate is not None else default

    def has_config_value(path):
        return ConfigManager.get_config_value(path) is not None

    def get_named_entity_definition_by_key_sequence(key_sequence):
        for named_entity_definition in config.named_entity_definitions:
            if named_entity_definition.key_sequence == re.sub(
                "(Shift\+|\+Shift)", "", key_sequence
            ):
                return named_entity_definition
                break
