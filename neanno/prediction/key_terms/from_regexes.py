import re

import yaml

from neanno.prediction.predictor import Predictor


class FromRegexesKeyTermsPredictor(Predictor):
    """ Predicts key terms of a text by using regular expressions."""

    pattern_definitions = {}

    def __init__(self, predictor_config):
        super().__init__(predictor_config)
        for pattern_definition in predictor_config["patterns"]:
            self.add_pattern_definition(
                pattern_definition["name"],
                pattern_definition["pattern"],
                pattern_definition["parent_terms"]
                if "parent_terms" in pattern_definition
                else None,
            )

    @property
    def project_config_validation_schema_custom_part(self):
        return yaml.load(
            """
            patterns:
                type: list
                schema:
                    type: dict
                    schema:
                        name:
                            type: string
                            required: True
                        pattern:
                            type: string
                            required: True
                        parent_terms:
                            type: string
                            required: False
            """,
            Loader=yaml.FullLoader,
        )

    def add_pattern_definition(self, name, pattern, parent_terms):
        self.pattern_definitions[name] = PatternDefinition(name, pattern, parent_terms)

    def remove_pattern_definition(self, name):
        del self.pattern_definitions[name]

    def predict_inline_annotations(self, text, language="en-US"):
        result = text
        for name in self.pattern_definitions:
            pattern_definition = self.pattern_definitions[name]
            if pattern_definition.parent_terms:
                result = re.sub(
                    r"(?P<term>{})".format(pattern_definition.pattern),
                    "`{}``PK``{}`´".format("\g<term>", pattern_definition.parent_terms),
                    result,
                )
            else:
                result = re.sub(
                    r"(?P<term>{})".format(pattern_definition.pattern),
                    "`{}``SK`´".format("\g<term>"),
                    result,
                )
        return result


class PatternDefinition:
    """ Defines a regex pattern for predicting key terms."""

    def __init__(self, name, pattern, parent_terms=[]):
        self.name = name
        self.pattern = pattern
        self.parent_terms = parent_terms
