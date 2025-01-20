from karp.foundation import json
from collections import Counter, defaultdict


def flatten_list(x):
    if isinstance(x, list):
        for y in x:
            yield from flatten_list(y)
    else:
        yield x


def get_values_of(path, data):
    if json.has_path(path, data):
        yield from flatten_list(json.get_path(path, data))


def get_tags(path, entry):
    for lemma in get_values_of("SAOLLemman", entry.entry):
        if lemma.get("visas"):
            yield from get_values_of("_inflectiontable.rows.row.preform.tag", lemma)


counts = defaultdict(Counter)

for entry in entry_queries.all_entries("salex"):
    ordklass = entry.entry.get("ordklass")
    if not ordklass:
        continue
    for tag in get_tags("SAOLLemman._inflectiontable.rows.row.preform.tag", entry):
        counts[tag][ordklass] += 1

for tag, classes in counts.items():
    print(tag, list(classes.items()))

exit()
