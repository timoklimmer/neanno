import re

import yaml

from neanno.prediction.predictor import Predictor
from neanno.utils.text import mask_annotations, unmask_annotations


class FromRegexesNamedEntitiesPredictor(Predictor):
    """ Predicts named entities of a text by using regular expressions."""

    named_entity_regexes = {}

    def __init__(self, predictor_config):
        super().__init__(predictor_config)
        for named_entity_regex in predictor_config["patterns"]:
            self.add_named_entity_regex(
                named_entity_regex["entity"],
                named_entity_regex["pattern"],
                named_entity_regex["parent_terms"]
                if "parent_terms" in named_entity_regex
                else None,
            )

    @property
    def config_validation_schema_custom_part(self):
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
            """
        )

    def add_named_entity_regex(self, entity_code, pattern, parent_terms):
        self.named_entity_regexes[entity_code] = NamedEntityRegex(
            entity_code, pattern, parent_terms
        )

    def remove_named_entity_regex(self, entity_code):
        del self.named_entity_regexes[entity_code]

    def predict_inline_annotations(self, text, mask_annotations_before_return=False):
        result = mask_annotations(text)
        for named_entity_code in self.named_entity_regexes:
            named_entity_regex = self.named_entity_regexes[named_entity_code]
            if named_entity_regex.parent_terms:
                result = re.sub(
                    r"(?P<term>{})".format(named_entity_regex.pattern),
                    "`{}``PN``{}``{}`´".format(
                        "\g<term>",
                        named_entity_regex.entity,
                        named_entity_regex.parent_terms,
                    ),
                    result,
                )
            else:
                result = re.sub(
                    r"(?P<term>{})".format(named_entity_regex.pattern),
                    "`{}``SN``{}`´".format("\g<term>", named_entity_regex.entity),
                    result,
                )
        return (
            mask_annotations(result)
            if mask_annotations_before_return
            else unmask_annotations(result)
        )

    def get_parent_terms_for_named_entity(self, term, entity_code):
        if entity_code in self.named_entity_regexes:
            named_entity_regex_definition = self.named_entity_regexes[entity_code]
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


class NamedEntityRegex:
    """ Defines a regex for predicting named entities."""

    def __init__(self, entity, pattern, parent_terms=[]):
        self.entity = entity
        self.pattern = pattern
        self.parent_terms = parent_terms
