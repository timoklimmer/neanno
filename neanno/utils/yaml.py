import yaml
import os
from cerberus import Validator


def validate_yaml(yaml_to_validate, yaml_schema_to_use):
    """ Validates the given YAML against the given schema (cerberus) and throws an exception if the validation fails."""

    # note: input parameters can be either streams, strings or dicts

    # ensure that none of the input parameters is not None or empty
    if not yaml_to_validate:
        raise ValueError(
            "Parameter 'yaml_to_validate' is None or empty which is not valid."
        )
    if not yaml_schema_to_use:
        raise ValueError(
            "Parameter 'yaml_schema_to_use' is None or empty which is not valid."
        )

    # get yaml_dom and yaml_schema_dom
    yaml_dom = yaml.load(
        str(yaml_to_validate)
        if isinstance(yaml_to_validate, (dict,))
        else yaml_to_validate
    )
    yaml_schema_dom = yaml.load(
        str(yaml_schema_to_use)
        if isinstance(yaml_schema_to_use, (dict,))
        else yaml_schema_to_use
    )

    # ensure that yaml_dom and yaml_schema_dom are not None
    if not yaml_dom:
        raise ValueError(
            "Could not resolve parameter 'yaml_to_validate' to a valid YAML object. Ensure that the specified parameter is correct."
        )
    if not yaml_schema_dom:
        raise ValueError(
            "Could not resolve parameter 'yaml_schema_dom' to a valid YAML object. Ensure that the specified parameter is correct."
        )

    # do validation and throw exception if validation fails
    validator = Validator(yaml_schema_dom)
    validator.validate(yaml_dom)
    errors = validator.errors
    if errors:
        error_message = (
            yaml.dump(errors)
            + os.linesep
            + os.linesep
            + "The given yaml does not follow the required schema. See error message(s) above for more details."
        )
        raise ValueError(error_message)
