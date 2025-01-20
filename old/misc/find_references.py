# guess which fields might be references

from karp.foundation import json
from collections import defaultdict, Counter
import pickle

# a field is a possible key if it has >= 95% unique values and its
# name ends with id or nr
# a field is a possible reference if >= 95% of its values are keys
# (these thresholds can be adjusted below)


def guess_keys(resource_config, entries, key_threshold=0.95):
    fields = resource_config.nested_fields()
    fields = [
        field
        for field in fields
        if resource_config.field_config(field).type != "object"
        and (field.lower().endswith("id") or field.lower().endswith("nr"))
    ]

    duplicates = Counter()
    field_values = defaultdict(set)
    result = set()

    for entry in entries:
        for field in fields:
            paths = json.expand_path(field, entry.entry)
            for path in paths:
                value = json.get_path(path, entry.entry)
                if value in field_values[field]:
                    duplicates[field] += 1
                field_values[field].add(value)

    for field, values in field_values.items():
        dups = duplicates[field]
        non_dups = len(values)
        total = dups + non_dups
        if dups <= (1 - key_threshold) * total:
            result.add(field)

    return {field: field_values[field] for field in result}


def guess_references(resource_config, entries, keys, ref_threshold=0.95):
    fields = resource_config.nested_fields()

    for field in fields:
        for key, values in keys.items():

resource_config = resource_queries.by_resource_id("salex").config
entries = list(entry_queries.all_entries("salex", expand_plugins=False))
#with open("entries.pickle", "rb") as file:
#    entries = pickle.load(file)

for key, values in guess_keys(resource_config, entries).items():
   print(key, len(values))

exit()
