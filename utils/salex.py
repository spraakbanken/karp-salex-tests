"""Utility functions specific to Salex."""

import karp.foundation.json as json
from copy import deepcopy


def entry_is_visible(entry):
    return entry.get("visas", True)


def entry_is_visible_in_printed_book(entry):
    return entry_is_visible(entry) and not entry.get("endastDigitalt", False)


def is_visible(path, entry, test=entry_is_visible):
    return True
    for i in range(len(path)):
        if not test(json.get_path(path[:-1], entry)):
            return False

    return True


def trim_invisible(data, test=entry_is_visible):
    paths = list(json.all_paths(data))  # compute up front since we will be modifying data
    for path in paths:
        if not json.has_path(path, data):
            continue  # already deleted

        if not test(json.get_path(path, data)):
            json.del_path(path, data)


def visible_part(data, test=entry_is_visible):
    data = deepcopy(data)
    trim_invisible(data, test)
    return data
