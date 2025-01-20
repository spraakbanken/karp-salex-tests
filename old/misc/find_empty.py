from karp.foundation import json
from copy import deepcopy


def shown(value, printed=False):
    if not isinstance(value, dict):
        return True
    if "visas" in value and not value["visas"]:
        return False
    if printed and "endastDigitalt" in value and value["endastDigitalt"]:
        return False
    return True


def check_entry(entry, printed=False):
    orig_entry = deepcopy(entry.entry)
    ortografi = entry.entry.get("ortografi")

    for path in reversed(list(json.all_paths(entry.entry))):
        value = json.get_path(path, entry.entry)

        if not shown(value):
            json.del_path(path, entry.entry)

    for path in reversed(list(json.all_paths(entry.entry))):
        value = json.get_path(path, entry.entry)

        if value == [] or value == {}:
            json.del_path(path, entry.entry)

    # if orig_entry != entry.entry:
    #    print("before:")
    #    print(orig_entry)
    #    print("after:")
    #    print(entry.entry)
    #    print()

    if not entry.entry.get("so", {}) and not entry.entry.get("saol", {}):
        print(entry.id, ortografi)


for entry in entry_queries.all_entries("salex", expand_plugins=False):
    check_entry(entry)
