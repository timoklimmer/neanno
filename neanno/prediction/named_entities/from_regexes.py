import re

import yaml

from neanno.prediction.predictor import Predictor


class FromRegexesNamedEntitiesPredictor(Predictor):
    """ Predicts named entities of a text by using regular expressions."""

    pattern_definitions = {}

    def __init__(self, predictor_config):
        super().__init__(predictor_config)
        for pattern_definition in predictor_config["patterns"]:
            self.add_pattern_definition(
                pattern_definition["entity"],
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
                        entity:
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

    def add_pattern_definition(self, entity_code, pattern, parent_terms):
        self.pattern_definitions[entity_code] = PatternDefinition(
            entity_code, pattern, parent_terms
        )

    def remove_pattern_definition(self, entity_code):
        del self.pattern_definitions[entity_code]

    def predict_inline_annotations(self, text, language="en-US"):
        result = text
        for named_entity_code in self.pattern_definitions:
            pattern_definition = self.pattern_definitions[named_entity_code]
            if pattern_definition.parent_terms:
                result = re.sub(
                    r"(?P<term>{})".format(pattern_definition.pattern),
                    "`{}``PN``{}``{}`´".format(
                        "\g<term>",
                        pattern_definition.entity,
                        pattern_definition.parent_terms,
                    ),
                    result,
                )
            else:
                result = re.sub(
                    r"(?P<term>{})".format(pattern_definition.pattern),
                    "`{}``SN``{}`´".format("\g<term>", pattern_definition.entity),
                    result,
                )
        return result

    def get_parent_terms_for_named_entity(self, term, entity_code):
        if entity_code in self.pattern_definitions:
            named_entity_regex_definition = self.pattern_definitions[entity_code]
            # check if term matches regex from the definition
            if re.match(named_entity_regex_definition.pattern, term):
                # yes, matches
                return named_entity_regex_definition.parent_terms
            else:
                # does not match
                # note: depending on the regex pattern we might end up here even if
                #       the pattern would usually match. however, since we only have
                #       the term but not its surroundings to match against, we cannot
                #       consider lookbehinds/lookaheads from the regex. to avoid efforts,
                #       we accept this behavior as long as it seems that this is
                #       acceptable.
                return None
        else:
            # no, no regex for the entity code
            return None


class PatternDefinition:
    """ Defines a regex for predicting named entities."""

    def __init__(self, entity, pattern, parent_terms=[]):
        self.entity = entity
        self.pattern = pattern
        self.parent_terms = parent_terms
