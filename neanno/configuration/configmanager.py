import argparse
import os
import re
import importlib

import config
import yaml
from cerberus import Validator

from neanno.configuration.colors import DEFAULT_ENTITY_COLORS_PALETTE
from neanno.configuration.definitions import CategoryDefinition, NamedEntityDefinition
from neanno.prediction.key_terms.from_dataset import FromDatasetKeyTermsPredictor
from neanno.prediction.key_terms.from_regexes import FromRegexesKeyTermsPredictor
from neanno.prediction.named_entities.from_datasets import (
    FromDatasetsNamedEntitiesPredictor,
)
from neanno.prediction.named_entities.from_regexes import (
    FromRegexesNamedEntitiesPredictor,
)
from neanno.prediction.named_entities.from_spacy import FromSpacyNamedEntitiesPredictor
from neanno.prediction.pipeline import PredictionPipeline
from neanno.utils.dataset import DatasetLocation, DatasetManager
from neanno.utils.dict import QueryDict


class ConfigManager:
    """Collects all configuration settings and provides configuration-related objects to neanno (through config.*)."""

    def __init__(self):
        # specify neanno's args and load/validate the required config file
        ConfigManager.define_args_and_load_config_yaml()
        # instantiate prediction pipeline (setup/population will be done below)
        config.prediction_pipeline = PredictionPipeline()
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
        # instructions
        ConfigManager.instructions()

    @staticmethod
    def define_args_and_load_config_yaml():
        # define arguments
        config.parser = argparse.ArgumentParser(
            description="A tool to label and annotate texts and train models.",
            add_help=False,
        )
        required = config.parser.add_argument_group("required arguments")
        required.add_argument(
            "--config-file",
            help="""Points to a config file for neanno. See the airline_tickets.config.yaml file in samples/airline_tickets to learn how to write neanno config files.""",
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

    @staticmethod
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

    @staticmethod
    def dataset_target():
        config.dataset_target_friendly = None
        if ConfigManager.has_config_value("dataset/target"):
            dataset_location = DatasetLocation(
                ConfigManager.get_config_value("dataset/target")
            )
            getattr(ConfigManager, "dataset_target_{}".format(dataset_location.type))(
                dataset_location
            )

    @staticmethod
    def dataset_target_csv(dataset_location):
        config.dataset_target_friendly = os.path.basename(dataset_location.path)
        config.save_callback = lambda df: DatasetManager.save_dataset_to_csv(
            df, dataset_location.path
        )

    @staticmethod
    def key_terms():
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
        config.is_key_terms_enabled = "key_terms" in config.yaml
        if config.is_key_terms_enabled:
            ConfigManager.key_terms_predictors()

    @staticmethod
    def get_prefix_for_predictor_class_name(predictor_config_key):
        result = predictor_config_key
        result = result[:1].upper() + result[1:]
        result = re.sub(
            "_.", lambda match: match.group().replace("_", "").upper(), result
        )
        return result

    @staticmethod
    def key_terms_predictors():
        # iterate through all predictor configs, dynamically instantiate a predictor instance for
        # each config and add it to the prediction pipeline
        predictor_configs_dict = ConfigManager.get_config_value("key_terms/predictors")
        for predictor_config_key in predictor_configs_dict:
            predictor_config = predictor_configs_dict[predictor_config_key]
            predictor_module = importlib.import_module(
                "neanno.prediction.key_terms.{}".format(predictor_config_key)
            )
            predictor_class_name = "{}KeyTermsPredictor".format(
                ConfigManager.get_prefix_for_predictor_class_name(predictor_config_key)
            )
            print("Adding {} to prediction pipeline...".format(predictor_class_name))
            predictor = getattr(predictor_module, predictor_class_name)(
                predictor_config
            )
            config.prediction_pipeline.add_predictor(predictor)

    @staticmethod
    def named_entities():
        config.named_entity_definitions = []
        config.named_entity_codes = []
        config.is_named_entities_enabled = "named_entities" in config.yaml
        if config.is_named_entities_enabled:
            ConfigManager.named_entities_definitions()
            ConfigManager.named_entities_predictors()

    @staticmethod
    def named_entities_definitions():
        index = 0
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

    @staticmethod
    def named_entities_predictors():
        # iterate through all predictor configs, dynamically instantiate a predictor instance for
        # each config and add it to the prediction pipeline
        predictor_configs_dict = ConfigManager.get_config_value("named_entities/predictors")
        for predictor_config_key in predictor_configs_dict:
            predictor_config = predictor_configs_dict[predictor_config_key]
            predictor_module = importlib.import_module(
                "neanno.prediction.named_entities.{}".format(predictor_config_key)
            )
            predictor_class_name = "{}NamedEntitiesPredictor".format(
                ConfigManager.get_prefix_for_predictor_class_name(predictor_config_key)
            )
            print("Adding {} to prediction pipeline...".format(predictor_class_name))
            predictor = getattr(predictor_module, predictor_class_name)(
                predictor_config
            )
            config.prediction_pipeline.add_predictor(predictor)

    @staticmethod
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

    @staticmethod
    def categories_predictors():
        # TODO: complete
        pass

    @staticmethod
    def instructions():
        config.has_instructions = "instructions" in config.yaml
        config.instructions = ConfigManager.get_config_value("instructions")

    @staticmethod
    def get_config_value(path, default=None):
        candidate = QueryDict(config.yaml).get(path)
        return candidate if candidate is not None else default

    @staticmethod
    def has_config_value(path):
        return ConfigManager.get_config_value(path) is not None

    @staticmethod
    def get_named_entity_definition_by_key_sequence(key_sequence):
        for named_entity_definition in config.named_entity_definitions:
            if named_entity_definition.key_sequence == re.sub(
                "(Shift\+|\+Shift)", "", key_sequence
            ):
                return named_entity_definition
                break
