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

# TODO: add dict navigator
#https://www.haykranen.nl/2016/02/13/handling-complex-nested-dicts-in-python/