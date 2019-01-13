def ensure_items_within_set(list, set, list_none_means_pass=False, error_message=None):
    """ Ensures that all items in the specified list are within the specified set."""
    if list is None:
        return
    for item in list:
        if item not in set:
            if error_message is None:
                error_message = (
                    "At least one entry in the specified list is invalid. Valid items are: {}.".format(
                        ", ".join(["'" + set_item + "'" for set_item in set])
                    ),
                )
            raise ValueError(error_message)


def get_set_of_list_keep_sequence(list):
    """ Returns the set of the specified list but keeps the sequence of the items."""
    seen = set()
    return [x for x in list if not (x in seen or seen.add(x))]
