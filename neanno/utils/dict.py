class QueryDict(dict):
    """Helper class to query a dict more conveniently."""

    def get(self, path, default=None):
        keys = path.split("/")
        value = None
        for key in keys:
            if value:
                if isinstance(value, list):
                    value = [
                        child_value.get(key, default) if child_value else None
                        for child_value in value
                    ]
                else:
                    value = value.get(key, default)
            else:
                value = dict.get(self, key, default)
            if not value:
                break
        return value


def merge_dict_sum_numbers(dict1, dict2):
    """ Assumes two dictionaries with schema key:numeric value and merges them into a single dictionary whereby the numeric values are summed per key."""
    result = {}
    if dict1 is None:
        dict1 = {}
    if dict2 is None:
        dict2 = {}
    for key in dict1:
        if key not in result:
            result[key] = 0
        result[key] += dict1[key]
    for key in dict2:
        if key not in result:
            result[key] = 0
        result[key] += dict2[key]
    return result


def merge_dict_sum_child_dicts(dict1, dict2):
    """ Assumes two dictionaries with schema key:{child keys: numeric value} and merges the two into a single dictionary whereby the numeric values in the child dictionaries are summed."""
    result = {}
    if dict1 is None:
        dict1 = {}
    if dict2 is None:
        dict2 = {}
    for key in dict1:
        if key not in result:
            result[key] = {}
        result[key] = merge_dict_sum_numbers(result[key], dict1[key])
    for key in dict2:
        if key not in result:
            result[key] = {}
        result[key] = merge_dict_sum_numbers(result[key], dict2[key])
    return result


def merge_dict(dict1, dict2):
    """ Merges dict2 into dict1."""
    if dict1 is None:
        dict1 = {}
    if dict2 is None:
        dict2 = {}
    result = dict1.copy()
    for key in dict2:
        result[key] = dict2[key]
    return result
