class QueryDict(dict):
    """Helper class to query a dict more conveniently."""

    def get(self, path, default=None):
        # return default value if path is None
        if not path:
            return default
        # walk down the hierarchy and return either the found value or the default value
        keys_from_path = path.split("/")
        path_length = len(keys_from_path)
        for i, key_from_path in enumerate(keys_from_path):
            if i == 0:
                parent_element = dict.get(self, key_from_path, default)
                continue
            if i > 0 and i < path_length:
                try:
                    parent_element = parent_element[key_from_path]
                    continue
                except:
                    return default
        return parent_element


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
