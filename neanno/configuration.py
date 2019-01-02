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
    AutoSuggestEntityRegex,
    AutoSuggestKeyTermRegex,
    CategoryDefinition,
    NamedEntityDefinition,
)
from neanno.dictutils import QueryDict, merge_dict
from neanno.textutils import extract_annotations_as_list


class ConfigManager:
    """Collects all configuration settings and provides configuration-related objects to neanno (through config.*)."""

    key_terms_marked_for_removal_from_autosuggest_collection = []

    def __init__(self):
        # specify neanno's args and load/validate the required config file
        ConfigManager.define_args_and_load_config_yaml()
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
                        + "The given config file does not follow the required schema (from file config.schema.yaml). See error message(s) above for more details."
                    )

    def dataset_source():
        print("Loading dataframe with texts to annotate...")
        config.text_column = ConfigManager.get_config_value("dataset/text_column")
        config.is_annotated_column = ConfigManager.get_config_value(
            "dataset/is_annotated_column"
        )
        config.dataset_to_edit, config.dataset_source_friendly = ConfigManager.load_dataset(
            ConfigManager.get_config_value("dataset/source"),
            {config.text_column: str},
            "dataset/source",
        )
        config.dataset_to_edit[config.text_column] = config.dataset_to_edit[
            config.text_column
        ].astype(str)

    def dataset_target():
        config.dataset_target_friendly = None
        if ConfigManager.has_config_value("dataset/target"):
            datasource_spec = ConfigManager.get_config_value("dataset/target")
            datasource_type = datasource_spec.split(":")[0]
            supported_datasource_types = ["csv"]
            if datasource_type not in supported_datasource_types:
                config.parser.error(
                    "Parameter 'dataset/target' uses a datasource type '{}' which is not supported.  Ensure that a valid datasource type is specified. Valid datasource types are: {}.".format(
                        datasource_type, ", ".join(supported_datasource_types)
                    )
                )
            getattr(ConfigManager, "dataset_target_" + datasource_type)()

    def dataset_target_csv():
        dataset_target_csv = ConfigManager.get_config_value("dataset/target").replace(
            "csv:", "", 1
        )
        config.dataset_target_friendly = os.path.basename(dataset_target_csv)
        config.save_callback = lambda df: df.to_csv(
            dataset_target_csv, index=False, header=True
        )

    def key_terms():
        config.key_terms_marked_for_removal_from_autosuggest_collection = []
        config.is_key_terms_enabled = "key_terms" in config.yaml
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
        # source
        config.is_autosuggest_key_terms_by_source = ConfigManager.has_config_value(
            "key_terms/auto_suggest/source/spec"
        )
        if config.is_autosuggest_key_terms_by_source:
            print("Loading autosuggest key terms dataset...")
            # load data
            config.autosuggest_key_terms_dataset, friendly_dataset_name_never_used = ConfigManager.load_dataset(
                ConfigManager.get_config_value("key_terms/auto_suggest/source/spec"),
                {"term": str, "parent_terms": str},
                "key_terms/auto_suggest/source/spec",
            )
            # setup flashtext for later string replacements
            autosuggest_key_terms_dataset = config.autosuggest_key_terms_dataset.copy()
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
                + "|P "
                + autosuggest_key_terms_dataset["parent_terms"]
                + ")"
            )
            autosuggest_key_terms_dataset.loc[
                autosuggest_key_terms_dataset["parent_terms"] == "", "against"
            ] = ("(" + autosuggest_key_terms_dataset["term"] + "|S)")
            autosuggest_key_terms_dataset = autosuggest_key_terms_dataset[
                ["replace", "against"]
            ]
            autosuggest_key_terms_dataset_as_dict = {
                row["against"]: [row["replace"]]
                for index, row in autosuggest_key_terms_dataset.iterrows()
            }
            config.key_terms_autosuggest_flashtext = KeywordProcessor()
            config.key_terms_autosuggest_flashtext.add_keywords_from_dict(
                autosuggest_key_terms_dataset_as_dict
            )

        # regexes
        config.key_terms_autosuggest_regexes = []
        config.is_autosuggest_key_terms_by_regexes = ConfigManager.has_config_value(
            "key_terms/auto_suggest/regexes"
        )
        if config.is_autosuggest_key_terms_by_regexes:
            for autosuggest_regex in ConfigManager.get_config_value(
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
            ConfigManager.named_entities_definitions()
            ConfigManager.named_entities_autosuggest()

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
            index += 1

    def named_entities_autosuggest():
        # sources
        config.is_autosuggest_entities_by_sources = ConfigManager.has_config_value(
            "named_entities/auto_suggest/sources"
        )
        if config.is_autosuggest_entities_by_sources:
            print("Loading autosuggest entities dataset(s)...")
            # combine data from multiple datasets
            autosuggest_entities_dataset = pd.DataFrame(columns=["term", "entity_code"])
            for spec in ConfigManager.get_config_value(
                "named_entities/auto_suggest/sources"
            ):
                new_data, friendly_dataset_name_never_used = ConfigManager.load_dataset(
                    spec,
                    {"term": str, "entity_code": str},
                    "named_entities/auto_suggest/sources",
                )
                autosuggest_entities_dataset = autosuggest_entities_dataset.append(
                    new_data
                )
            # setup flashtext for later string replacements
            config.named_entities_autosuggest_flashtext = KeywordProcessor()
            data_for_flashtext = pd.DataFrame(
                "("
                + autosuggest_entities_dataset["term"]
                + "|N "
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
        config.is_autosuggest_entities_by_regexes = ConfigManager.has_config_value(
            "named_entities/auto_suggest/regexes"
        )
        if config.is_autosuggest_entities_by_regexes:
            for autosuggest_regex in ConfigManager.get_config_value(
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

    def load_dataset(spec, schema, fillna=True, parameter=None):
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
        required_columns = list(schema.keys())
        result = getattr(ConfigManager, "load_dataset_" + datasource_type)(
            spec, required_columns, parameter_hint, True
        )
        for column_name in schema.keys():
            result[0][column_name] = result[0][column_name].astype(schema[column_name])
        return result

    def load_dataset_csv(spec, required_columns, parameter_hint, fill_na=True):
        file_to_load = spec.replace("csv:", "", 1)
        if not os.path.isfile(file_to_load):
            config.parser.error(
                "The file '{}'{} does not exist. Ensure that you specify a file which exists.".format(
                    file_to_load, parameter_hint
                )
            )
        result = pd.read_csv(file_to_load)
        if fill_na:
            result = result.fillna("")
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
        return ConfigManager.get_config_value(path) is not None

    def update_autosuggest_key_terms_collection(annotated_text):
        if config.is_autosuggest_key_terms_by_source:
            # get terms to add/update
            terms_to_add = {}
            parented_terms_to_update = []
            existing_terms_list = list(config.autosuggest_key_terms_dataset["term"])
            for annotation in extract_annotations_as_list(
                annotated_text,
                term_types_to_extract=["standalone_keyterm", "parented_keyterm"],
            ):
                if annotation["term"] not in existing_terms_list:
                    # term does not exist yet
                    terms_to_add = merge_dict(
                        terms_to_add,
                        {
                            annotation["term"]: annotation["parent_terms"]
                            if "parent_terms" in annotation
                            else ""
                        },
                    )
                else:
                    # term exists but may need update due to different parent terms
                    if "parent_terms" in annotation:
                        currently_stored_parent_terms = list(
                            config.autosuggest_key_terms_dataset[
                                config.autosuggest_key_terms_dataset["term"]
                                == annotation["term"]
                            ]["parent_terms"]
                        )[0]
                        if currently_stored_parent_terms != annotation["parent_terms"]:
                            # needs update
                            terms_to_add = merge_dict(
                                terms_to_add,
                                {
                                    annotation["term"]: annotation["parent_terms"]
                                    if "parent_terms" in annotation
                                    else ""
                                },
                            )
                            parented_terms_to_update.append(annotation["term"])

            # get total terms to remove
            terms_to_remove = [
                term
                for term in config.key_terms_marked_for_removal_from_autosuggest_collection
                if term not in terms_to_add
            ]
            terms_to_update = [term for term in parented_terms_to_update]
            terms_to_remove.extend(terms_to_update)

            # update autosuggest dataset
            # remove
            if terms_to_remove:
                for term in terms_to_remove:
                    config.autosuggest_key_terms_dataset = config.autosuggest_key_terms_dataset[
                        config.autosuggest_key_terms_dataset.term != term
                    ]
            # add
            if terms_to_add:
                for term in terms_to_add:
                    new_row = pd.DataFrame(
                        {"term": [term], "parent_terms": [terms_to_add[term]]}
                    )
                    config.autosuggest_key_terms_dataset = config.autosuggest_key_terms_dataset.append(
                        new_row
                    )
            # save
            ConfigManager.writeback_autosuggest_key_terms_collection()

            # update flashtext
            # remove obsolete terms
            if terms_to_remove:
                for term in terms_to_remove:
                    config.key_terms_autosuggest_flashtext.remove_keyword(term)
            # add new terms
            if terms_to_add:
                for term in terms_to_add:
                    if terms_to_add[term] != "":
                        config.key_terms_autosuggest_flashtext.add_keywords_from_dict(
                            {"({}|P {})".format(term, terms_to_add[term]): [term]}
                        )
                    else:
                        config.key_terms_autosuggest_flashtext.add_keywords_from_dict(
                            {"({}|S)".format(term): [term]}
                        )

    def writeback_autosuggest_key_terms_collection():
        # sort the key terms dataset for convenience
        config.autosuggest_key_terms_dataset[
            "sort"
        ] = config.autosuggest_key_terms_dataset["term"].str.lower()
        config.autosuggest_key_terms_dataset = config.autosuggest_key_terms_dataset.sort_values(
            by=["sort"]
        )
        del config.autosuggest_key_terms_dataset["sort"]
        # save the dataset
        ConfigManager.save_dataset(
            config.autosuggest_key_terms_dataset,
            ConfigManager.get_config_value("key_terms/auto_suggest/source/spec"),
        )

    def mark_key_term_for_removal_from_autosuggest_collection(term):
        if term not in config.key_terms_marked_for_removal_from_autosuggest_collection:
            config.key_terms_marked_for_removal_from_autosuggest_collection.append(term)

    def reset_key_terms_marked_for_removal_from_autosuggest_collection():
        config.key_terms_marked_for_removal_from_autosuggest_collection = []

    def save_dataset(dataframe, spec):
        supported_datasource_types = ["csv"]
        datasource_type = spec.split(":")[0]
        if datasource_type not in supported_datasource_types:
            config.parser.error(
                "Spec '{}' uses a datasource type '{}' which is not supported for saving. Ensure that a valid datasource type is specified. Valid datasource types are: {}.".format(
                    spec, datasource_type, ", ".join(supported_datasource_types)
                )
            )
        getattr(ConfigManager, "save_dataset_" + datasource_type)(dataframe, spec)

    def save_dataset_csv(dataframe, spec):
        file_path = spec.replace("csv:", "", 1)
        dataframe.to_csv(file_path, header=True, index=False)
