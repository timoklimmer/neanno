import statistics


def append_if_not_none(list, new_item_candidate):
    if new_item_candidate:
        list.append(new_item_candidate)


def not_none(list):
    return [item for item in list if item is not None]


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


def get_set_of_list_and_keep_sequence(list):
    """ Returns the set of the specified list but keeps the sequence of the items."""
    seen = set()
    return [x for x in list if not (x in seen or seen.add(x))]


def is_majority_of_last_n_items_decreasing(list, n):
    """ Checks if the majority of the last n items in the given list are decreasing."""
    if len(list) <= n + 1:
        raise ValueError(
            "Cannot check if last items are decreasing. According to the given parameters, the list has to have at least n + 1 = {} items.".format(
                str(n + 1)
            )
        )
    last_relevant_items = list[-(n + 1) :]
    decreasing = [
        last_relevant_items[index - 1] > last_relevant_items[index]
        if index > 0
        else None
        for (index, value) in enumerate(last_relevant_items)
    ][1:]
    try:
        return statistics.mode(decreasing)
    except statistics.StatisticsError:
        return False
