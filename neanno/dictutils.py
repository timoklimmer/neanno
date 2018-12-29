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


def mergesum_dict(dict1, dict2):
    """ Assumes two dictionaries with schema key:numeric value and merges them into a single dictionary while summing the numeric values per key."""
    result = {}
    for key in dict1:
        if key not in result:
            result[key] = 0
        value = dict1[key]
        result[key] += value
    for key in dict2:
        if key not in result:
            result[key] = 0
        value = dict2[key]
        result[key] += value
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
