"""Utility functions specific to Salex."""

import karp.foundation.json as json
from copy import deepcopy


def is_visible(path, entry):
    # TODO: support endastDigitalt
    return True
    for i in range(len(path)):
        visas_path = path[:i] + ["visas"]
        if json.has_path(visas_path, entry.entry) and not json.get_path(visas_path, entry.entry):
            return False

    return True


def trim_invisible(data):
    paths = list(json.all_paths(data))  # compute up front since we will be modifying data
    for path in paths:
        if path and path[-1] == "visas":
            if not json.has_path(path, data):
                continue  # already deleted

            if not json.get_path(path, data):
                json.del_path(path[:-1], data)


def visible_part(data):
    data = deepcopy(data)
    trim_invisible(data)
    return data
